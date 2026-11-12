# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

"""One REST operation per call. Writers compare before they write."""

import base64
import hashlib
import re
from urllib.parse import quote, urlsplit

from ansible_collections.gr.idg.plugins.module_utils.client import (
    DEFAULT_DOMAIN,
    IDGError,
    PROTECTED_STORES,
    action_id_from_body,
    as_list,
    clean_for_compare,
    clean_payload,
    error_text,
    order_name_first,
    quote_path,
    same_config,
    snake_record,
    status_message,
)
from ansible_collections.gr.idg.plugins.module_utils import records


READ_ONLY_CLI = frozenset((
    "show", "help", "echo", "top", "switch", "exit", "test", "traceroute", "ping",
))
RESERVED_ACTIONS = frozenset(("Export", "Import", "LoadConfiguration"))
SENSITIVE_STORES = frozenset(("cert", "sharedcert", "isamcert", "pubcert"))


def _with_raw(result, raw_flag, document):
    if raw_flag:
        result["raw"] = document
    return result


def _changed(before, after, wrote):
    return {
        "changed": wrote,
        "diff": {"before": before, "after": after},
    }


def read_provider(client, domain, class_name, area="status"):
    path = quote_path("mgmt", area, domain, class_name)
    payload, document = client.read_class(path, class_name)
    return payload, document


def attach_raw(result, raw_flag, document):
    return _with_raw(result, raw_flag, document)


def windows_status(client, class_name, mapper, result_key, raw_flag):
    payload, document = read_provider(client, DEFAULT_DOMAIN, class_name)
    record = payload if isinstance(payload, dict) else {}
    result = {
        "changed": False,
        "domain": DEFAULT_DOMAIN,
        result_key: mapper(record),
    }
    return _with_raw(result, raw_flag, document)


def list_status(client, domain, class_name, mapper, result_key, raw_flag, area="status"):
    payload, document = read_provider(client, domain, class_name, area=area)
    result = {
        "changed": False,
        "domain": domain,
        result_key: mapper(payload),
    }
    return _with_raw(result, raw_flag, document)


def snake_status(client, domain, class_name, result_key, raw_flag, area="status"):
    payload, document = read_provider(client, domain, class_name, area=area)
    result = {
        "changed": False,
        "domain": domain,
        result_key: snake_record(payload),
    }
    return _with_raw(result, raw_flag, document)


def read_datetime(client, raw_flag):
    current, document = read_provider(client, DEFAULT_DOMAIN, "DateTimeStatus")
    extended = None
    extended_doc = None
    try:
        extended, extended_doc = read_provider(client, DEFAULT_DOMAIN, "DateTimeStatus2")
    except IDGError as exc:
        if exc.status not in (404, None) and "not available" not in str(exc):
            raise
    result = {
        "changed": False,
        "domain": DEFAULT_DOMAIN,
        "clock": records.datetime_status(current, extended),
    }
    if raw_flag:
        result["raw"] = {"DateTimeStatus": document, "DateTimeStatus2": extended_doc}
    return result


def gather_facts(client, raw_flag):
    firmware, firmware_doc = read_provider(client, DEFAULT_DOMAIN, "FirmwareVersion3")
    license_rows, license_doc = read_provider(client, DEFAULT_DOMAIN, "LicenseStatus")
    crypto, crypto_doc = read_provider(client, DEFAULT_DOMAIN, "CryptoEngineStatus2")
    settings_path = quote_path(
        "mgmt", "config", DEFAULT_DOMAIN, "SystemSettings", "System-Settings"
    )
    settings, settings_doc = client.read_class(settings_path, "SystemSettings")

    firmware = firmware if isinstance(firmware, dict) else {}
    hidden = {
        "CustomUIFile",
        "EntitlementNumber",
        "SerialNumber",
        "mAdminState",
        "name",
        "_links",
        "href",
    }
    public_settings = {
        key: value
        for key, value in (settings or {}).items()
        if key not in hidden
    }
    features = {}
    for feat in as_list(license_rows):
        if not isinstance(feat, dict) or not feat.get("Feature"):
            continue
        features[feat.get("Feature")] = {
            "available": records.is_yes(feat.get("Available")),
            "enabled": records.is_yes(feat.get("Enabled")),
        }
    crypto_public = {}
    for key, value in (crypto or {}).items():
        if value not in ("notApplicable", "none"):
            crypto_public[key] = value

    info = {
        "firmware": snake_record(firmware),
        "license": features,
        "crypto_engine": snake_record(crypto_public),
        "system_settings": snake_record(public_settings),
    }
    result = {
        "changed": False,
        "domain": DEFAULT_DOMAIN,
        "info": info,
        "ansible_facts": {
            "datapower": {
                "firmware": firmware.get("Version"),
                "model": firmware.get("ModelType"),
                "serial": firmware.get("Serial"),
            }
        },
    }
    if raw_flag:
        result["raw"] = {
            "FirmwareVersion3": firmware_doc,
            "CryptoEngineStatus2": crypto_doc,
            "SystemSettings": settings_doc,
        }
    return result


def _on_off(value):
    return "on" if value else "off"


def _managed_match(current, desired):
    """True when every key we send already has that value on the appliance."""
    current = clean_for_compare(current or {})
    desired = clean_for_compare(desired or {})
    if not isinstance(current, dict) or not isinstance(desired, dict):
        return current == desired
    for key, value in desired.items():
        if isinstance(value, dict) and isinstance(current.get(key), dict):
            if not _managed_match(current.get(key), value):
                return False
        elif current.get(key) != value:
            return False
    return True


def _domain_body(params):
    name = params["name"]
    visible = params.get("visible") or ["default"]
    if len(visible) == 1:
        neighbors = {"value": visible[0]}
    else:
        neighbors = [{"value": item} for item in visible]
    file_map = params["file_map"]
    monitoring = params["monitoring_map"]
    body = {
        "name": name,
        "mAdminState": params["admin_state"],
        "UserSummary": params.get("user_summary"),
        "ConfigMode": params["config_mode"],
        "ConfigPermissionsMode": params["config_permissions_mode"],
        "ImportFormat": params["import_format"],
        "LocalIPRewrite": _on_off(params["local_ip_rewrite"]),
        "MaxChkpoints": params["max_chkpoints"],
        "FileMap": {
            "Display": _on_off(file_map["display"]),
            "Exec": _on_off(file_map["exec"]),
            "CopyFrom": _on_off(file_map["copyfrom"]),
            "CopyTo": _on_off(file_map["copyto"]),
            "Delete": _on_off(file_map["delete"]),
            "Subdir": _on_off(file_map["subdir"]),
        },
        "MonitoringMap": {
            "Audit": _on_off(monitoring["audit"]),
            "Log": _on_off(monitoring["log"]),
        },
        "NeighborDomain": neighbors,
    }
    return {key: value for key, value in body.items() if value is not None}


def _neighbor_differs(current, desired):
    if isinstance(current, dict) and isinstance(desired, dict):
        return current.get("value") != desired.get("value")
    if isinstance(current, list) and isinstance(desired, list):
        got = sorted(item.get("value") for item in current if isinstance(item, dict))
        new = sorted(item.get("value") for item in desired if isinstance(item, dict))
        return got != new
    return current != desired


def _domain_differs(current, desired):
    current = clean_payload(current or {})
    for key, new_value in desired.items():
        got = current.get(key)
        if key == "NeighborDomain":
            if _neighbor_differs(got, new_value):
                return True
        elif got != new_value:
            return True
    return False


def _domain_rows(client):
    payload, _document = read_provider(client, DEFAULT_DOMAIN, "DomainStatus")
    return as_list(payload)


def _find_domain(rows, name):
    for row in rows:
        if isinstance(row, dict) and row.get("Domain") == name:
            return row
    return None


def manage_domain(client, params, check_mode):
    name = params["name"]
    state = params["state"]
    rows = _domain_rows(client)
    current_status = _find_domain(rows, name)
    exists = current_status is not None
    path = quote_path("mgmt", "config", DEFAULT_DOMAIN, "Domain", name)
    result = {"name": name, "domain": name, "changed": False}

    if state == "present":
        desired = _domain_body(params)
        current = None
        if exists:
            current_doc = client.get_or_none(path)
            current = clean_payload((current_doc or {}).get("Domain") or {})
        differs = (not exists) or _domain_differs(current, desired)
        result["diff"] = {"before": current, "after": desired}
        if not differs:
            result["msg"] = "The domain already matches."
            return result
        result["changed"] = True
        if check_mode:
            result["msg"] = "The domain would change."
            return result
        method = "PUT"
        response = client.request(method, path, {"Domain": desired})
        if response.status not in (200, 201):
            raise IDGError(error_text(response.data) or "The domain was not written.")
        result["msg"] = "The domain was written."
        return result

    if state == "absent":
        result["diff"] = {"before": current_status, "after": None}
        if not exists:
            result["msg"] = "The domain is already absent."
            return result
        result["changed"] = True
        if check_mode:
            result["msg"] = "The domain would be deleted."
            return result
        response = client.request("DELETE", path)
        if response.status != 200:
            raise IDGError(error_text(response.data) or "The domain was not deleted.")
        result["msg"] = "The domain was deleted."
        return result

    if not exists:
        raise IDGError("Domain {0} does not exist.".format(name))

    if state == "restarted":
        result["changed"] = True
        result["diff"] = {"before": current_status, "after": current_status}
        if check_mode:
            result["msg"] = "The domain would restart."
            return result
        posted = client.post_action(name, {"ResetThisDomain": {}})
        result.update(posted)
        return result

    quiesced = (current_status or {}).get("QuiesceState") == "quiesced"
    want_quiesce = state == "quiesced"
    result["diff"] = {"before": current_status, "after": current_status}
    if want_quiesce == quiesced:
        result["msg"] = "The quiesce state already matches."
        return result
    result["changed"] = True
    if check_mode:
        result["msg"] = "The quiesce state would change."
        return result
    if want_quiesce:
        quiesce = params.get("quiesce_conf") or {}
        body = {
            "DomainQuiesce": {
                "name": name,
                "delay": quiesce.get("delay", 0),
                "timeout": quiesce.get("timeout", 60),
            }
        }
    else:
        body = {"DomainUnquiesce": {"name": name}}
    result.update(client.post_action(name, body))
    return result


def _save_needed(client, domain):
    rows = _domain_rows(client)
    row = _find_domain(rows, domain)
    if row is None and len(rows) == 1:
        row = rows[0]
    if not isinstance(row, dict):
        raise IDGError("Domain {0} does not exist.".format(domain))
    return row.get("SaveNeeded")


def manage_domain_config(client, params, check_mode):
    domain = params["domain"]
    state = params["state"]
    # Without the trailing slash this directory returns 400 Invalid URI.
    listing = client.get_or_none(quote_path("mgmt", "domains", "config") + "/")
    names = []
    if isinstance(listing, dict):
        for row in as_list(listing.get("domain")):
            if isinstance(row, dict) and row.get("name"):
                names.append(row.get("name"))
    if domain not in names:
        raise IDGError("Domain {0} does not exist.".format(domain))

    result = {"domain": domain, "changed": False}
    if state == "saved":
        needed = _save_needed(client, domain)
        result["diff"] = {
            "before": {"SaveNeeded": needed},
            "after": {"SaveNeeded": "off"},
        }
        if needed == "off":
            result["msg"] = "The domain is already saved."
            return result
        result["changed"] = True
        if check_mode:
            result["msg"] = "The domain would be saved."
            return result
        result.update(client.post_action(domain, {"SaveConfig": {}}))
        return result

    if state == "exported":
        export_body = {
            "Format": "ZIP",
            "AllFiles": _on_off(params["all_files"]),
            "Persisted": _on_off(params["persisted"]),
            "IncludeInternalFiles": _on_off(params["internal_files"]),
        }
        if params.get("user_summary"):
            export_body["UserComment"] = params["user_summary"]
        body = {"Export": export_body}
    else:
        body = {
            "Import": {
                "Format": "ZIP",
                "InputFile": params["zip_file"],
                "OverwriteFiles": _on_off(params["overwrite_files"]),
                "OverwriteObjects": _on_off(params["overwrite_objects"]),
                "DryRun": _on_off(params["dry_run"]),
                "RewriteLocalIP": _on_off(params["rewrite_local_ip"]),
            }
        }
    result["changed"] = True
    if check_mode:
        result["msg"] = "The action would be posted."
        return result
    result.update(client.post_action(domain, body))
    return result


def _class_name(event):
    value = event.get("Class") if isinstance(event, dict) else None
    if isinstance(value, dict):
        return value.get("value") or value.get("name")
    return value


def set_log_level(client, params, check_mode):
    domain = params["domain"]
    target = params["log_target"]
    level = params["log_level"]
    path = quote_path("mgmt", "config", domain, "LogTarget", target)
    current_doc = client.get(path).data
    current = clean_payload((current_doc or {}).get("LogTarget") or {})
    events = []
    has_all = False
    current_level = None
    for event in as_list(current.get("LogEvents")):
        if not isinstance(event, dict):
            continue
        updated = dict(event)
        if _class_name(updated) == "all":
            current_level = updated.get("Priority")
            updated["Priority"] = level
            has_all = True
        events.append(updated)
    if not has_all:
        events.append({"Class": "all", "Priority": level})
    desired = dict(current)
    desired["name"] = target
    desired["LogEvents"] = events
    result = {
        "domain": domain,
        "name": target,
        "log_events": events,
        "changed": current_level != level,
        "diff": {"before": current, "after": desired},
    }
    if current_level == level:
        result["msg"] = "The log level already matches."
        return result
    if check_mode:
        result["msg"] = "The log level would change."
        return result
    response = client.request(
        "PUT",
        path,
        {"LogTarget": {"name": target, "LogEvents": events}},
    )
    if response.status != 200:
        raise IDGError(error_text(response.data) or "The log level was not written.")
    result["msg"] = "The log level was written."
    return result


def _store(domain, url):
    parsed = urlsplit((url or "").strip())
    scheme = (parsed.scheme or "").lower()
    path = parsed.path or ""
    if not scheme:
        raise IDGError("The filestore path needs a directory such as local:.")
    if not path.startswith("/"):
        path = "/" + path
    if scheme == "sharedcert":
        domain = DEFAULT_DOMAIN
    prefix = "/mgmt/filestore/{0}/{1}".format(
        quote(str(domain), safe=""),
        quote(scheme, safe=""),
    )
    # DataPower returns 400 Invalid URI when a filestore resource ends in /.
    # The trailing slash belongs only on category roots such as /mgmt/filestore/.
    return domain, scheme, (prefix + path).rstrip("/"), prefix


def _assert_writable(scheme):
    if scheme in PROTECTED_STORES:
        raise IDGError("The collection does not write {0}:.".format(scheme))


def _remote_file(data):
    if not isinstance(data, dict):
        return None, False
    if "filestore" in data:
        return data.get("filestore"), True
    return data.get("file"), False


def _content_hash(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        raw = base64.b64decode(value)
    except (ValueError, TypeError):
        return None
    return hashlib.sha256(raw).hexdigest()


def upload_file(client, params, check_mode):
    domain = params["domain"]
    _domain, scheme, item, directory = _store(domain, params["target"])
    _assert_writable(scheme)
    try:
        with open(params["source"], "rb") as handle:
            raw = handle.read()
    except OSError:
        raise IDGError("The source file could not be read.")
    digest = hashlib.sha256(raw).hexdigest()
    encoded = base64.b64encode(raw).decode("ascii")
    current_doc = client.get_or_none(item)
    _file, is_dir = _remote_file(current_doc or {})
    if is_dir:
        raise IDGError("The destination is a directory.")
    remote_hash = None
    if isinstance(_file, dict):
        remote_hash = _content_hash(_file.get("content"))
    name = item.rstrip("/").rsplit("/", 1)[-1]
    before = {"name": name, "sha256": remote_hash}
    after = {"name": name, "sha256": digest}
    result = {
        "domain": domain,
        "target": params["target"],
        "source": params["source"],
        "diff": {"before": before if current_doc else None, "after": after},
        "changed": remote_hash != digest,
    }
    if remote_hash == digest:
        result["msg"] = "The file already matches."
        return result
    if check_mode:
        result["msg"] = "The file would be uploaded."
        return result
    body = {"file": {"name": name, "content": encoded}}
    if current_doc:
        response = client.request("PUT", item, body)
    else:
        response = client.request("POST", directory, body)
    if response.status not in (200, 201):
        raise IDGError(error_text(response.data) or "The file was not uploaded.")
    result["msg"] = "The file was uploaded."
    return result


def _redact_store(scheme, payload):
    if scheme not in SENSITIVE_STORES:
        return payload
    if isinstance(payload, dict) and "content" in payload:
        hidden = dict(payload)
        hidden["content"] = "VALUE_SPECIFIED_IN_NO_LOG_PARAMETER"
        return hidden
    return payload


def manage_files(client, params, check_mode):
    domain = params["domain"]
    state = params["state"]
    _domain, scheme, item, directory = _store(domain, params["target"])
    if state != "show":
        _assert_writable(scheme)
    current_doc = client.get_or_none(item)
    current = clean_payload(current_doc) if current_doc else None
    _file, is_dir = _remote_file(current or {})
    exists = current is not None
    result = {
        "domain": domain,
        "target": params["target"],
        "source": params.get("source"),
        "changed": False,
        "diff": {"before": _redact_store(scheme, current), "after": None},
    }

    if state == "show":
        if not exists:
            raise IDGError("The target does not exist.")
        result["changed"] = False
        result["content"] = _redact_store(scheme, current)
        result["diff"]["after"] = result["diff"]["before"]
        result["msg"] = "The filestore object was read."
        return result

    if state == "directory":
        desired = {"directory": {"name": urlsplit(params["target"]).path}}
        result["diff"]["after"] = desired
        if exists:
            result["msg"] = "The directory already exists."
            result["diff"]["after"] = result["diff"]["before"]
            return result
        result["changed"] = True
        if check_mode:
            result["msg"] = "The directory would be created."
            return result
        response = client.request("POST", directory, desired)
        if response.status != 201:
            raise IDGError(error_text(response.data) or "The directory was not created.")
        result["msg"] = "The directory was created."
        return result

    if state == "absent":
        if not exists:
            result["msg"] = "The target is already absent."
            return result
        result["changed"] = True
        result["diff"]["after"] = None
        if check_mode:
            result["msg"] = "The target would be deleted."
            return result
        response = client.request("DELETE", item)
        if response.status not in (200, 404):
            raise IDGError(error_text(response.data) or "The target was not deleted.")
        result["msg"] = "The target was deleted."
        return result

    source = params.get("source")
    if not source:
        raise IDGError("source is required.")
    _src_domain, src_scheme, src_item, _src_dir = _store(domain, source)
    source_doc = client.get_or_none(src_item)
    if source_doc is None:
        raise IDGError("The source does not exist.")
    source_file, source_is_dir = _remote_file(source_doc)
    if state == "copy" and source_is_dir:
        raise IDGError("The source is a directory.")
    if is_dir:
        raise IDGError("The destination is a directory.")
    source_hash = _content_hash((source_file or {}).get("content")) if isinstance(source_file, dict) else None
    dest_hash = _content_hash((_file or {}).get("content")) if isinstance(_file, dict) else None
    result["diff"]["before"] = {
        "source_sha256": source_hash,
        "target_sha256": dest_hash,
    }
    result["diff"]["after"] = {"target_sha256": source_hash}
    if state == "move" and source_doc is None:
        raise IDGError("The source does not exist.")
    if exists and dest_hash is not None and dest_hash == source_hash and state == "copy":
        result["msg"] = "The destination already matches."
        return result
    if state == "move" and source_doc is None and exists:
        result["msg"] = "The source is already absent."
        return result
    if exists and not params.get("overwrite"):
        raise IDGError("The destination exists and overwrite is false.")
    result["changed"] = True
    if check_mode:
        result["msg"] = "The file would be {0}d.".format(state)
        return result
    if state == "move":
        body = {
            "MoveFile": {
                "sURL": source,
                "dURL": params["target"],
                "Overwrite": _on_off(bool(params.get("overwrite"))),
            }
        }
    else:
        body = {
            "FetchFile": {
                "URL": source,
                "File": params["target"],
                "Overwrite": _on_off(bool(params.get("overwrite"))),
            }
        }
    posted = client.post_action(domain, body)
    result.update(posted)
    return result


def _object_path(domain, class_name, name=None):
    if str(class_name).lower() == "sharedcert":
        domain = DEFAULT_DOMAIN
    root = quote_path("mgmt", "config", domain, class_name)
    if name:
        return domain, root + "/" + quote(str(name), safe="")
    return domain, root


def _query(path, view=None, depth=None, include_state=False):
    parts = []
    if view:
        parts.append("view={0}".format(quote(str(view), safe="")))
    if depth is not None:
        parts.append("depth={0}".format(quote(str(depth), safe="")))
    if include_state:
        parts.append("state=1")
    if not parts:
        return path
    return path + "?" + "&".join(parts)


def _merge(base, overlay):
    if not isinstance(base, dict) or not isinstance(overlay, dict):
        return overlay
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def ensure_config(client, params, check_mode):
    domain = params["domain"]
    class_name = params["class_name"]
    name = params.get("name")
    state = params.get("state")
    body = params.get("config")
    domain, root = _object_path(domain, class_name, None)
    item = root + ("/" + quote(str(name), safe="") if name else "")
    if not state:
        path = _query(
            item if name else root,
            view=params.get("view"),
            depth=params.get("depth"),
            include_state=bool(name),
        )
        document = client.get(path).data
        cleaned = clean_payload(document)
        result = {"changed": False, "domain": domain, "config": cleaned}
        if params.get("raw"):
            result["raw"] = cleaned
        return result

    if state in ("merged", "replaced") and not isinstance(body, dict):
        raise IDGError("config is required.")
    desired_obj = body.get(class_name, body) if isinstance(body, dict) else {}
    if name and isinstance(desired_obj, dict):
        desired_obj = dict(desired_obj)
        desired_obj["name"] = name
    current_doc = client.get_or_none(item if name else root)
    current_obj = None
    if isinstance(current_doc, dict):
        current_obj = clean_payload(current_doc.get(class_name, current_doc))
        if isinstance(current_obj, list):
            current_obj = None
    if state == "deleted":
        result = {
            "changed": current_obj is not None,
            "domain": domain,
            "diff": {"before": current_obj, "after": None},
        }
        if current_obj is None:
            result["msg"] = "The object is already absent."
            return result
        if check_mode:
            result["msg"] = "The object would be deleted."
            return result
        response = client.request("DELETE", item)
        if response.status != 200:
            raise IDGError(error_text(response.data) or "The object was not deleted.")
        result["msg"] = "The object was deleted."
        return result

    if state == "merged":
        final_obj = _merge(current_obj or {}, desired_obj)
    else:
        final_obj = desired_obj
    if isinstance(final_obj, dict):
        final_obj = order_name_first(final_obj)
    final = {class_name: final_obj}
    differs = not same_config(current_obj, final_obj) if current_obj is not None else True
    result = {
        "changed": differs,
        "domain": domain,
        "config": clean_payload(final_obj),
        "diff": {"before": current_obj, "after": clean_payload(final_obj)},
    }
    if not differs:
        result["msg"] = "The object already matches."
        return result
    if check_mode:
        result["msg"] = "The object would change."
        return result
    if current_obj is None:
        response = client.request("POST", root, final)
    else:
        response = client.request("PUT", item, final)
    if response.status not in (200, 201):
        raise IDGError(error_text(response.data) or "The object was not written.")
    result["msg"] = "The object was written."
    return result


def post_named_action(client, params, check_mode):
    action = params["action"]
    if action in RESERVED_ACTIONS:
        raise IDGError("Use gr.idg.domain_config for {0}.".format(action))
    result = {"domain": params["domain"], "changed": True}
    if check_mode:
        result["msg"] = "The action would be posted."
        result["changed"] = True
        return result
    body = {action: params.get("parameters") or {}}
    result.update(client.post_action(params["domain"], body))
    return result


def _link_names(document):
    if not isinstance(document, dict):
        return []
    links = document.get("_links") or {}
    skip = {"self", "parent", "doc", "href"}
    return sorted(key for key in links.keys() if key not in skip)


def management_info(client, params):
    domain = params.get("domain") or DEFAULT_DOMAIN
    section = params["section"]
    class_name = params.get("class_name")
    if section == "config":
        path = quote_path("mgmt", "config") + "/"
    elif section == "status":
        path = quote_path("mgmt", "status") + "/"
    else:
        path = quote_path("mgmt", "actionqueue", domain, "operations")
    document = client.get(path).data
    result = {
        "changed": False,
        "domain": domain,
        "section": section,
        "classes": _link_names(document),
    }
    if class_name:
        meta_path = quote_path("mgmt", "metadata", domain, class_name)
        schema = client.get_or_none(meta_path)
        if schema is None:
            schema = client.get(quote_path("mgmt", "docs", "config", class_name)).data
        result["schema"] = clean_payload(schema)
    if params.get("raw"):
        result["raw"] = clean_payload(document)
    return result


def poll_action(client, params):
    domain = params["domain"]
    action_id = params["action_id"]
    path = quote_path("mgmt", "actionqueue", domain, "pending", action_id)
    document = client.get_or_none(path)
    if document is None:
        raise IDGError("Action {0} was not found.".format(action_id))
    status = document.get("status") if isinstance(document, dict) else document
    if isinstance(document, str):
        status = document
    result = {
        "changed": False,
        "domain": domain,
        "action_id": action_id,
        "status": status,
    }
    if isinstance(document, dict) and "result" in document:
        result["result"] = clean_payload(document.get("result"))
    return result


def run_cli(client, params):
    commands = params["commands"]
    mutating = False
    for command in commands:
        token = (command or "").strip().split(" ", 1)[0].lower()
        if token not in READ_ONLY_CLI:
            mutating = True
            break
    # Custom CLI bridge. It opens an internal telnet session.
    # The domain travels in the query string.
    path = "{0}?domain={1}".format(
        quote_path("v1", "system", "cli", "execute"),
        quote(str(params["domain"]), safe=""),
    )
    response = client.request("POST", path, commands, as_json=False)
    if response.status != 200:
        raise IDGError(error_text(response.data) or "The CLI request failed.")
    if isinstance(response.data, dict):
        screen = response.data.get("screen") or []
    elif isinstance(response.data, str) and response.data.strip():
        screen = [response.data.strip()]
    else:
        screen = []
    if not screen:
        raise IDGError("The CLI request returned no output.")
    return {
        "changed": mutating,
        "domain": params["domain"],
        "screen": screen,
        "msg": "The CLI commands were accepted.",
    }


def network_probe(client, action, fields):
    body = {action: fields}
    posted = client.post_action(DEFAULT_DOMAIN, body)
    posted["domain"] = DEFAULT_DOMAIN
    return posted


def checkpoint(client, params, check_mode):
    state = params["state"]
    actions = {
        "present": "SaveCheckpoint",
        "absent": "RemoveCheckpoint",
        "restored": "RollbackCheckpoint",
    }
    action = actions[state]
    result = {
        "domain": params["domain"],
        "name": params["name"],
        "changed": True,
    }
    if check_mode:
        result["msg"] = "The checkpoint action would be posted."
        return result
    try:
        result.update(client.post_action(
            params["domain"],
            {action: {"ChkName": params["name"]}},
        ))
    except IDGError as exc:
        if state == "absent" and "Cannot find Configuration Checkpoint" in str(exc):
            return {
                "domain": params["domain"],
                "name": params["name"],
                "changed": False,
                "msg": "The checkpoint is already absent.",
            }
        raise
    return result


def _member_key(server, port):
    return (server, "" if port in (None, 0) else port)


def _member_from_params(member):
    port = member.get("mapped_port")
    record = {
        "Server": member["server"],
        "MappedPort": "" if port in (None, 0) else port,
        "LBMemberState": member.get("admin_state") or "enabled",
    }
    if member.get("health_port"):
        record["HealthPort"] = member["health_port"]
    if member.get("weight"):
        record["Weight"] = member["weight"]
    return record


def load_balancer_members(client, params, check_mode):
    domain = params["domain"]
    group = params["balancer_group"]
    path = "/mgmt/config/{0}/LoadBalancerGroup/{1}/LBGroupMembers".format(
        quote(domain, safe=""),
        quote(group, safe=""),
    )
    current_doc = client.get(path).data or {}
    current = as_list(clean_payload(current_doc.get("LBGroupMembers")))
    current = [row for row in current if isinstance(row, dict)]
    indexed = {
        _member_key(row.get("Server"), row.get("MappedPort")): row
        for row in current
    }
    requested = [_member_from_params(item) for item in params["members"]]
    if params["state"] == "present":
        desired = list(current)
        for member in requested:
            key = _member_key(member["Server"], member["MappedPort"])
            if key in indexed:
                merged = dict(indexed[key])
                merged["LBMemberState"] = member["LBMemberState"]
                if "HealthPort" in member:
                    merged["HealthPort"] = member["HealthPort"]
                if "Weight" in member:
                    merged["Weight"] = member["Weight"]
                member = merged
                desired = [
                    member if _member_key(row.get("Server"), row.get("MappedPort")) == key else row
                    for row in desired
                ]
            else:
                desired.append(member)
    else:
        remove = {_member_key(item["Server"], item["MappedPort"]) for item in requested}
        desired = [
            row for row in current
            if _member_key(row.get("Server"), row.get("MappedPort")) not in remove
        ]
    result = {
        "domain": domain,
        "balancer_group": group,
        "changed": not same_config(current, desired),
        "members": desired,
        "diff": {"before": current, "after": desired},
    }
    if not result["changed"]:
        result["msg"] = "The members already match."
        return result
    if check_mode:
        result["msg"] = "The members would change."
        return result
    response = client.request("POST", path, {"LBGroupMembers": desired})
    if response.status != 200:
        raise IDGError(error_text(response.data) or "The members were not written.")
    result["msg"] = "The members were written."
    return result


def refresh_wsdl(client, params):
    return client.post_action(params["domain"], {
        "RefreshWSDL": {
            "WSGateway": params["ws_gateway"],
            "WSDL": params["wsdl_source_location"],
        }
    })


def flush_stylesheet(client, params):
    posted = client.post_action(params["domain"], {
        "FlushStylesheetCache": {"XMLManager": params["xml_manager"]}
    })
    posted["xml_manager"] = params["xml_manager"]
    return posted


def sync_subscription(client, params):
    return client.post_action(params["domain"], {
        "WsrrSynchronize": {"WSRRSubscription": params["subscription"]}
    })


def fetch_log_summary(client, params):
    domain = params["domain"]
    path = "/logs/fetch/xml/error-summary/{0}?bottom_ts={1}".format(
        quote(domain, safe=""),
        int(params.get("bottom_ts") or 0),
    )
    document = client.get(path).data
    return {
        "changed": False,
        "domain": domain,
        "summary": clean_payload(document),
        "msg": "The summary was read.",
    }


def show_gateway(client, params):
    domain = params["domain"]
    name = params["name"]
    path = quote_path("mgmt", "config", domain, "WSGateway", name)
    payload, document = client.read_class(path, "WSGateway")
    result = {
        "changed": False,
        "domain": domain,
        "name": name,
        "config": payload if isinstance(payload, dict) else clean_payload(payload),
    }
    if params.get("raw"):
        result["raw"] = document
    return result


def _crypto_class(object_class):
    if object_class == "public-key":
        return "CryptoCertificate"
    return "CryptoKey"


def _crypto_desired(params, include_expiration):
    desired = {
        "name": params["name"],
        "mAdminState": params["admin_state"],
        "Filename": params.get("file_name"),
    }
    if include_expiration:
        desired["IgnoreExpiration"] = _on_off(params.get("ignore_expiration"))
    if params.get("password_alias"):
        desired["Alias"] = {"value": params["password_alias"]}
    return {key: value for key, value in desired.items() if value is not None}


def _load_crypto(client, domain, class_name, name):
    _domain, root = _object_path(domain, class_name)
    item = root + "/" + quote(name, safe="")
    current_doc = client.get_or_none(item)
    current = None
    if isinstance(current_doc, dict):
        current = clean_payload(current_doc.get(class_name) or {})
        current.pop("PasswordAlias", None)
        alias = current.get("Alias")
        if isinstance(alias, dict):
            current["Alias"] = {"value": alias.get("value")}
    return root, item, current


def _ensure_crypto_object(client, params, check_mode, class_name, include_expiration):
    domain = params["domain"]
    name = params["name"]
    root, item, current = _load_crypto(client, domain, class_name, name)
    desired = _crypto_desired(params, include_expiration)
    result = {
        "domain": domain,
        "name": name,
        "changed": False,
        "diff": {"before": current, "after": desired if params["state"] == "present" else None},
    }
    if params["state"] == "absent":
        if current is None:
            result["msg"] = "The crypto object is already absent."
            return result
        result["changed"] = True
        if check_mode:
            result["msg"] = "The crypto object would be deleted."
            return result
        response = client.request("DELETE", item)
        if response.status != 200:
            raise IDGError(error_text(response.data) or "The crypto object was not deleted.")
        result["msg"] = "The crypto object was deleted."
        return result
    if current is not None and _managed_match(current, desired):
        result["msg"] = "The crypto object already matches."
        return result
    result["changed"] = True
    if check_mode:
        result["msg"] = "The crypto object would change."
        return result
    if current is None:
        response = client.request("POST", root, {class_name: desired})
    else:
        response = client.request("PUT", item, {class_name: desired})
    if response.status not in (200, 201):
        raise IDGError(error_text(response.data) or "The crypto object was not written.")
    result["config"] = desired
    result["msg"] = "The crypto object was written."
    return result


def ensure_crypto(client, params, check_mode):
    class_name = _crypto_class(params["object_class"])
    return _ensure_crypto_object(
        client,
        params,
        check_mode,
        class_name,
        params["object_class"] == "public-key",
    )


_CRYPTO_STORES = frozenset(("cert", "sharedcert", "pubcert"))
_SHARED_STORES = frozenset(("sharedcert", "pubcert"))


def normalize_filestore(url):
    """Return scheme:///path. cert:, cert:/ and cert:// name the same file."""
    text = str(url or "").strip()
    if ":" not in text:
        return ""
    scheme, _, rest = text.partition(":")
    scheme = scheme.strip().lower()
    rest = rest.lstrip("/")
    if scheme not in _CRYPTO_STORES or not rest:
        return ""
    return "{0}:///{1}".format(scheme, rest)


def filestore_domain(url, object_domain):
    """cert: belongs to the object domain. sharedcert: and pubcert: belong to default."""
    normalized = normalize_filestore(url)
    scheme = normalized.split(":", 1)[0] if normalized else ""
    if scheme in _SHARED_STORES:
        return DEFAULT_DOMAIN
    return object_domain


def _alias_text(current):
    if not isinstance(current, dict):
        return ""
    alias = current.get("Alias")
    if isinstance(alias, dict):
        return str(alias.get("value") or "").strip()
    if isinstance(alias, str):
        return alias.strip()
    return ""


def _without_runtime(current):
    desired = dict(current or {})
    desired.pop("state", None)
    desired.pop("PasswordAlias", None)
    return desired


def _retarget_desired(current, params, apply_alias):
    filename = normalize_filestore(params.get("file_name"))
    if not filename:
        raise IDGError("file_name is required.")
    desired = _without_runtime(current)
    comparable = _without_runtime(current)
    current_file = normalize_filestore(desired.get("Filename"))
    if current_file:
        comparable["Filename"] = current_file
    desired["Filename"] = filename
    current_alias = _alias_text(comparable)
    if current_alias:
        comparable["Alias"] = {"value": current_alias}
    else:
        comparable.pop("Alias", None)
    alias_param = params.get("password_alias") if apply_alias else None
    if apply_alias and alias_param is not None:
        if str(alias_param).strip():
            desired["Alias"] = {"value": str(alias_param).strip()}
        else:
            desired.pop("Alias", None)
    elif current_alias:
        desired["Alias"] = {"value": current_alias}
    else:
        desired.pop("Alias", None)
    return desired, comparable


def _retarget_crypto_object(client, params, check_mode, class_name, apply_alias):
    """Change Filename on an existing object and send the rest of it back."""
    domain = params["domain"]
    name = params["name"]
    if not name:
        raise IDGError("name is required.")
    _root, item, current = _load_crypto(client, domain, class_name, name)
    if current is None:
        raise IDGError("The crypto object does not exist.")
    desired, comparable = _retarget_desired(current, params, apply_alias)
    previous = {
        "name": name,
        "file_name": current.get("Filename") or "",
        "alias": _alias_text(current),
        "admin_state": current.get("mAdminState") or "",
        "ignore_expiration": current.get("IgnoreExpiration") == "on",
    }
    matches = same_config(comparable, desired)
    result = {
        "domain": domain,
        "name": name,
        "changed": not matches,
        "file_name": desired.get("Filename"),
        "previous": previous,
        "diff": {"before": comparable, "after": desired},
    }
    if matches:
        result["msg"] = "The crypto object already matches."
        return result
    if check_mode:
        result["msg"] = "The crypto object would change."
        return result
    body = order_name_first(desired)
    response = client.request("PUT", item, {class_name: body})
    if response.status not in (200, 201):
        raise IDGError(error_text(response.data) or "The crypto object was not written.")
    result["config"] = body
    result["msg"] = "The crypto object was written."
    return result


def ensure_crypto_key(client, params, check_mode):
    if params.get("state") == "retarget":
        return _retarget_crypto_object(client, params, check_mode, "CryptoKey", True)
    return _ensure_crypto_object(client, params, check_mode, "CryptoKey", False)


_CERTIFICATE_SECRET_KEYS = frozenset((
    "keyvalue",
    "modulus",
    "exponent",
    "pem",
    "content",
))


def _public_certificate_detail(details):
    """Drop key material. Keep the identity and validity fields."""

    def walk(value):
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            cleaned = {}
            for key, item in value.items():
                if str(key).lower().replace("-", "").replace("_", "") in _CERTIFICATE_SECRET_KEYS:
                    continue
                cleaned[str(key).replace("-", "_")] = walk(item)
            return cleaned
        return value

    return snake_record(walk(details))


def _certificate_details(document):
    if not isinstance(document, dict):
        return None
    certificate = document.get("CryptoCertificate")
    if isinstance(certificate, dict) and isinstance(certificate.get("CertificateDetails"), dict):
        return certificate.get("CertificateDetails")
    if isinstance(document.get("CertificateDetails"), dict):
        return document.get("CertificateDetails")
    return None


def read_certificate_detail(client, params):
    """Post ViewCertificateDetails and return the inline certificate record."""
    domain = params["domain"]
    name = params["name"]
    path = quote_path("mgmt", "actionqueue", domain)
    body = {"ViewCertificateDetails": {"CertificateObject": name}}
    response = client.request("POST", path, body)
    if response.status not in (200, 202):
        raise IDGError(error_text(response.data) or "The certificate detail was not read.")
    details = _certificate_details(response.data)
    if details is None:
        queued = action_id_from_body(response.data)
        message = status_message(response.data, "ViewCertificateDetails")
        if queued:
            raise IDGError(
                "The certificate detail was accepted as {0} and did not include CertificateDetails.".format(queued)
            )
        if message:
            raise IDGError("The certificate detail was not returned. {0}".format(message))
        raise IDGError("The certificate detail was not returned.")
    return {
        "changed": False,
        "domain": domain,
        "name": name,
        "detail": _public_certificate_detail(details),
        "msg": "The certificate detail was read.",
    }


def _certificate_record(cert):
    """Public fields of one parsed certificate. The key material stays out."""
    from cryptography.hazmat.primitives import hashes

    public = cert.public_key()
    signature = None
    if cert.signature_hash_algorithm is not None:
        signature = cert.signature_hash_algorithm.name
    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "serial_number": format(cert.serial_number, "x"),
        "not_before": cert.not_valid_before_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "not_after": cert.not_valid_after_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fingerprint_sha1": cert.fingerprint(hashes.SHA1()).hex(),
        "subject_public_key_algorithm": public.__class__.__name__,
        "subject_public_key_bit_length": getattr(public, "key_size", None),
        "signature_algorithm": signature,
    }


def _load_pem_certificates(raw):
    from cryptography import x509

    text = raw.decode("ascii", errors="ignore")
    blocks = re.findall(
        r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
        text,
        re.DOTALL,
    )
    return [x509.load_pem_x509_certificate(block.encode("ascii")) for block in blocks]


def _classify_certificate_bytes(raw):
    """Return kind, detail and chain. Never return the original bytes."""
    if not raw:
        return "unknown", None, []
    text = raw.decode("ascii", errors="ignore")
    has_cert = "BEGIN CERTIFICATE" in text
    has_key = "PRIVATE KEY" in text
    if has_cert:
        try:
            certs = _load_pem_certificates(raw)
        except Exception:
            return "unknown", None, []
        if not certs:
            return "unknown", None, []
        detail = _certificate_record(certs[0])
        chain = [_certificate_record(item) for item in certs[1:]]
        return "certificate", detail, chain
    if has_key:
        return "key", None, []
    if raw[:1] == b"\x30":
        try:
            from cryptography import x509

            detail = _certificate_record(x509.load_der_x509_certificate(raw))
        except Exception:
            return "unknown", None, []
        return "certificate", detail, []
    return "unknown", None, []


def inspect_certificate_file(client, params):
    """Read one filestore file and keep only its certificate detail."""
    domain = params["domain"]
    target = params["file_name"]
    _domain, _scheme, item, _directory = _store(domain, target)
    current = client.get_or_none(item)
    if current is None:
        raise IDGError("The target does not exist.")
    payload = clean_payload(current)
    remote, is_dir = _remote_file(payload or {})
    if is_dir:
        raise IDGError("The target is a directory.")
    encoded = remote.get("content") if isinstance(remote, dict) else None
    try:
        raw = base64.b64decode(encoded or "")
    except (ValueError, TypeError):
        raw = b""
    kind, detail, chain = _classify_certificate_bytes(raw)
    del raw, encoded
    result = {
        "changed": False,
        "domain": domain,
        "file_name": target,
        "kind": kind,
        "certificate": kind == "certificate",
        "msg": "The file is a certificate." if kind == "certificate" else "The file is not a certificate.",
    }
    if detail is not None:
        result["detail"] = detail
    if chain:
        result["chain"] = chain
    return result


def ensure_crypto_certificate(client, params, check_mode):
    if params["state"] == "detail":
        if params.get("file_name") and not params.get("name"):
            return inspect_certificate_file(client, params)
        if not params.get("name"):
            raise IDGError("name or file_name is required.")
        return read_certificate_detail(client, params)
    if params["state"] == "retarget":
        return _retarget_crypto_object(client, params, check_mode, "CryptoCertificate", False)
    if not params.get("name"):
        raise IDGError("name is required.")
    return _ensure_crypto_object(client, params, check_mode, "CryptoCertificate", True)


def ensure_password_alias(client, params, check_mode):
    domain = params["domain"]
    name = params["name"]
    _domain, root = _object_path(domain, "PasswordAlias")
    item = root + "/" + quote(name, safe="")
    current_doc = client.get_or_none(item)
    current = None
    if isinstance(current_doc, dict):
        current = clean_payload(current_doc.get("PasswordAlias") or {})
    desired = {
        "name": name,
        "mAdminState": params["admin_state"],
        "Password": params.get("password"),
        "UserSummary": params.get("summary"),
    }
    desired = {key: value for key, value in desired.items() if value is not None}
    comparable = dict(desired)
    comparable.pop("Password", None)
    current_public = dict(current or {})
    current_public.pop("Password", None)
    result = {
        "domain": domain,
        "name": name,
        "changed": False,
        "diff": {
            "before": current_public or None,
            "after": comparable if params["state"] == "present" else None,
        },
    }
    if params["state"] == "absent":
        if current is None:
            result["msg"] = "The password alias is already absent."
            return result
        result["changed"] = True
        if check_mode:
            result["msg"] = "The password alias would be deleted."
            return result
        response = client.request("DELETE", item)
        if response.status != 200:
            raise IDGError(error_text(response.data) or "The password alias was not deleted.")
        result["msg"] = "The password alias was deleted."
        return result
    fields_match = current is not None and _managed_match(current_public, comparable)
    if fields_match and not params.get("password"):
        result["msg"] = "The password alias already matches."
        return result
    # The GET does not return the password, so a supplied password is written.
    result["changed"] = True
    if check_mode:
        result["msg"] = "The password alias would change."
        return result
    if current is None:
        response = client.request("POST", root, {"PasswordAlias": desired})
    else:
        response = client.request("PUT", item, {"PasswordAlias": desired})
    if response.status not in (200, 201):
        raise IDGError(error_text(response.data) or "The password alias was not written.")
    result["msg"] = "The password alias was written."
    return result
