# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

"""Build a read-only certificate inventory from filestore and object reads."""


_KINDS = frozenset(("certificate", "key", "unknown", "error"))


def _rows(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _names(value):
    names = []
    for item in _rows(value):
        name = item.get("name") if isinstance(item, dict) else item
        text = str(name or "").strip()
        if text and text not in (".", "..") and text not in names:
            names.append(text)
    return names


def filestore_entries(content):
    """Names of files and directories. File bytes are not copied."""
    location = {}
    if isinstance(content, dict):
        location = content.get("filestore") or content
        if isinstance(location, dict) and isinstance(location.get("location"), dict):
            location = location.get("location") or {}
    if not isinstance(location, dict):
        location = {}
    return {
        "files": _names(location.get("file")),
        "directories": _names(location.get("directory")),
    }


def certificate_path(parent, name):
    """Join a filestore directory and one child name."""
    text = str(name or "").strip()
    if "://" in text:
        return text
    base = str(parent or "").strip().rstrip("/")
    if base.endswith(":"):
        return base + "///" + text.lstrip("/")
    return base + "/" + text.lstrip("/")


def active_domains(rows):
    """Enabled domains, including default. A missing admin state stays included."""
    source = rows
    if isinstance(source, dict):
        source = source.get("domains", source)
    names = []
    for row in _rows(source):
        if not isinstance(row, dict):
            continue
        name = row.get("domain") or row.get("Domain")
        admin = row.get("m_admin_state") or row.get("mAdminState") or row.get("admin_state")
        if admin and str(admin).lower() != "enabled":
            continue
        text = str(name or "").strip()
        if text and text not in names:
            names.append(text)
    return names


def _brief(detail):
    if not isinstance(detail, dict):
        return {}
    return {
        "subject": detail.get("subject"),
        "issuer": detail.get("issuer"),
        "serial": detail.get("serial_number"),
        "not_before": detail.get("not_before"),
        "not_after": detail.get("not_after"),
        "fingerprint_sha1": detail.get("fingerprint_sha1"),
        "algorithm": detail.get("signature_algorithm"),
        "bits": detail.get("subject_public_key_bit_length"),
    }


def _chain(value):
    rows = []
    for item in _rows(value):
        brief = _brief(item)
        if brief.get("subject") or brief.get("not_after"):
            rows.append({
                "subject": brief.get("subject"),
                "issuer": brief.get("issuer"),
                "not_after": brief.get("not_after"),
            })
    return rows


def _result_body(item):
    if not isinstance(item, dict):
        return {}, "The read did not return a result."
    if item.get("failed"):
        return {}, item.get("msg") or "The read failed."
    return item, None


def certificate_objects(results):
    """CryptoCertificate rows from gr.idg.config results. One row per object."""
    rows = []
    for result in _rows(results):
        if not isinstance(result, dict) or result.get("failed"):
            continue
        domain = result.get("domain_name") or result.get("item") or result.get("domain")
        config = result.get("config") if isinstance(result.get("config"), dict) else {}
        body = config.get("CryptoCertificate")
        for obj in _rows(body):
            if not isinstance(obj, dict):
                continue
            name = obj.get("name")
            if not name:
                continue
            rows.append({
                "domain": domain,
                "name": name,
                "file": obj.get("Filename") or "",
                "state": obj.get("mAdminState") or "",
                "ignore_expiration": obj.get("IgnoreExpiration") == "on",
            })
    return rows


def certificate_inventory(payload):
    """One report for an appliance. Input comes from read tasks only."""
    data = payload if isinstance(payload, dict) else {}
    domains = [str(item) for item in _rows(data.get("domains")) if item]
    files = _rows(data.get("files"))
    file_reads = _rows(data.get("file_reads"))
    objects = _rows(data.get("objects"))
    object_reads = _rows(data.get("object_reads"))
    reported_files = []
    certificate_count = 0
    for index, item in enumerate(files):
        source = item if isinstance(item, dict) else {}
        body, error = _result_body(file_reads[index] if index < len(file_reads) else {})
        kind = body.get("kind") or "unknown"
        if kind not in _KINDS:
            kind = "unknown"
        record = {
            "domain": source.get("domain"),
            "store": source.get("store"),
            "shared": bool(source.get("shared")),
            "path": source.get("path"),
            "is_certificate": bool(body.get("certificate")),
            "kind": kind,
        }
        if error:
            record["is_certificate"] = False
            record["kind"] = "error"
            record["message"] = error
        else:
            record.update(_brief(body.get("detail")))
            chain = _chain(body.get("chain"))
            if chain:
                record["chain"] = chain
        if record["is_certificate"]:
            certificate_count += 1
        reported_files.append(record)

    reported_objects = []
    for index, item in enumerate(objects):
        source = item if isinstance(item, dict) else {}
        body, error = _result_body(object_reads[index] if index < len(object_reads) else {})
        record = {
            "domain": source.get("domain"),
            "name": source.get("name"),
            "file": source.get("file"),
            "state": source.get("state"),
            "ignore_expiration": bool(source.get("ignore_expiration")),
            "detail_ok": error is None and isinstance(body.get("detail"), dict),
        }
        if error:
            record["message"] = error
        else:
            record.update(_brief(body.get("detail")))
        reported_objects.append(record)

    return {
        "schema": "gr.idg.certificate_inventory/v1",
        "appliance": data.get("appliance"),
        "domains": domains,
        "summary": [
            "{0} active domains, including default when it is enabled.".format(len(domains)),
            "{0} files checked; {1} certificates.".format(len(reported_files), certificate_count),
            "{0} CryptoCertificate objects.".format(len(reported_objects)),
        ],
        "files": reported_files,
        "objects": reported_objects,
    }


class FilterModule(object):
    def filters(self):
        return {
            "filestore_entries": filestore_entries,
            "certificate_path": certificate_path,
            "active_domains": active_domains,
            "certificate_objects": certificate_objects,
            "certificate_inventory": certificate_inventory,
        }
