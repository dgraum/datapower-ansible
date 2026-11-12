# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

"""Plan a crypto file replacement from reads. The filter does not write."""

from ansible_collections.gr.idg.plugins.filter.certificate_inventory import active_domains
from ansible_collections.gr.idg.plugins.module_utils.ops import (
    filestore_domain,
    normalize_filestore,
)

_FAILED_RESULTS = frozenset(("blocked", "reverted", "failed"))


def _rows(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _alias_name(obj):
    if not isinstance(obj, dict):
        return ""
    alias = obj.get("Alias")
    if isinstance(alias, dict):
        return str(alias.get("value") or "").strip()
    if isinstance(alias, str):
        return alias.strip()
    named = obj.get("PasswordAlias")
    if isinstance(named, dict):
        return str(named.get("value") or named.get("name") or "").strip()
    if isinstance(named, str):
        return named.strip()
    return ""


def _replacements(value):
    """Keep old, new and the alias name. Drop every other key, including password."""
    errors = []
    if not isinstance(value, list) or not value:
        return [], ["Pass a list of old and new filestore paths."]
    seen = {}
    clean = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            errors.append("Replacement {0} is not a mapping.".format(index))
            continue
        old = normalize_filestore(item.get("old"))
        new = normalize_filestore(item.get("new"))
        if not old or not new:
            errors.append(
                "Replacement {0} must use cert, sharedcert or pubcert.".format(index)
            )
            continue
        if old == new:
            errors.append("Replacement {0} uses the same path twice.".format(index))
            continue
        if old in seen:
            errors.append("Replacement {0} repeats {1}.".format(index, old))
            continue
        alias = item.get("password_alias")
        if alias is None:
            alias = ""
        if not isinstance(alias, str):
            errors.append("Replacement {0} has a password alias that is not a name.".format(index))
            continue
        seen[old] = new
        clean.append({
            "old": old,
            "new": new,
            "password_alias": alias.strip(),
        })
    return clean, errors


def crypto_replace_entries(replacements):
    """Validate the caller's list and return the public fields."""
    if isinstance(replacements, dict):
        replacements = replacements.get("replacements")
    clean, errors = _replacements(replacements)
    return {"replacements": clean, "errors": errors}


def _crypto_rows(results, class_name):
    rows = []
    failures = []
    for result in _rows(results):
        if not isinstance(result, dict) or result.get("skipped"):
            continue
        domain = str(result.get("domain_name") or result.get("domain") or "").strip()
        if result.get("failed"):
            if domain:
                failures.append({
                    "domain": domain,
                    "class_name": class_name,
                    "message": result.get("msg") or "The {0} list was not read.".format(class_name),
                })
            continue
        config = result.get("config") if isinstance(result.get("config"), dict) else {}
        for obj in _rows(config.get(class_name)):
            if not isinstance(obj, dict) or not obj.get("name"):
                continue
            rows.append({
                "domain": domain,
                "class_name": class_name,
                "name": str(obj.get("name")),
                "file": normalize_filestore(obj.get("Filename") or ""),
                "admin_state": str(obj.get("mAdminState") or ""),
                "ignore_expiration": obj.get("IgnoreExpiration") == "on",
                "alias": _alias_name(obj),
            })
    return rows, failures


def _matches(objects, replacements):
    matched = []
    for obj in objects:
        if not obj.get("file"):
            continue
        for repl in replacements:
            on_old = obj["file"] == repl["old"]
            on_new = obj["file"] == repl["new"]
            if not on_old and not on_new:
                continue
            requested = repl["password_alias"] if obj["class_name"] == "CryptoKey" else ""
            alias_change = bool(requested) and requested != obj.get("alias")
            matched.append({
                "domain": obj["domain"],
                "class_name": obj["class_name"],
                "name": obj["name"],
                "file": obj["file"],
                "old_file": repl["old"],
                "new_file": repl["new"],
                "pending": on_old or alias_change,
                "alias": obj.get("alias") or "",
                "password_alias": requested,
                "admin_state": obj.get("admin_state") or "",
                "ignore_expiration": bool(obj.get("ignore_expiration")),
            })
            break
    return matched


def crypto_replace_scope(payload):
    """List the file and alias reads. cert: and PasswordAlias stay in the object domain."""
    payload = payload if isinstance(payload, dict) else {}
    source = payload.get("replacements")
    if source and isinstance(source, list) and source and "old" in (source[0] or {}):
        replacements, errors = _replacements(source)
    else:
        parsed = crypto_replace_entries(source)
        replacements, errors = parsed["replacements"], parsed["errors"]
    if errors:
        return {
            "errors": errors,
            "replacements": replacements,
            "matches": [],
            "file_reads": [],
            "alias_reads": [],
            "read_failures": [],
        }
    keys, key_failures = _crypto_rows(payload.get("key_reads"), "CryptoKey")
    certificates, certificate_failures = _crypto_rows(
        payload.get("certificate_reads"), "CryptoCertificate"
    )
    objects = keys + certificates
    failures = key_failures + certificate_failures
    if "domains" in payload:
        active = set(active_domains(payload.get("domains") or []))
        objects = [row for row in objects if row["domain"] in active]
        failures = [row for row in failures if row["domain"] in active]
    matches = _matches(objects, replacements)
    file_reads = []
    seen_files = set()
    alias_reads = []
    seen_aliases = set()
    for match in matches:
        file_domain = filestore_domain(match["new_file"], match["domain"])
        file_key = (file_domain, match["new_file"])
        if file_key not in seen_files:
            seen_files.add(file_key)
            file_reads.append({
                "domain": file_domain,
                "path": match["new_file"],
                "shared": file_domain == "default" and not match["new_file"].startswith("cert:"),
            })
        if match["password_alias"]:
            alias_key = (match["domain"], match["password_alias"])
            if alias_key not in seen_aliases:
                seen_aliases.add(alias_key)
                alias_reads.append({
                    "domain": match["domain"],
                    "name": match["password_alias"],
                })
    return {
        "errors": [],
        "replacements": replacements,
        "matches": matches,
        "file_reads": file_reads,
        "alias_reads": alias_reads,
        "read_failures": failures,
    }


def _presence(results, requests, kind):
    found = {}
    for result in _rows(results):
        if not isinstance(result, dict):
            continue
        marker = result.get(kind) if isinstance(result.get(kind), dict) else {}
        if kind == "file_check":
            domain = str(marker.get("domain") or result.get("domain") or "").strip()
            path = normalize_filestore(marker.get("path") or result.get("target"))
            key = (domain, path)
        else:
            domain = str(marker.get("domain") or result.get("domain") or "").strip()
            name = str(marker.get("name") or "").strip()
            if not name:
                config = result.get("config") if isinstance(result.get("config"), dict) else {}
                body = config.get("PasswordAlias")
                if isinstance(body, dict):
                    name = str(body.get("name") or "").strip()
            key = (domain, name)
        if not key[0] or not key[1]:
            continue
        present = not result.get("failed") and not result.get("skipped")
        if kind == "alias_check" and present:
            config = result.get("config") if isinstance(result.get("config"), dict) else {}
            body = config.get("PasswordAlias")
            present = isinstance(body, dict) and bool(body.get("name"))
        found[key] = {
            "present": bool(present),
            "message": "" if present else (result.get("msg") or "The read failed."),
        }
    for request in _rows(requests):
        if not isinstance(request, dict):
            continue
        if kind == "file_check":
            key = (request.get("domain"), normalize_filestore(request.get("path")))
            label = "The file was not read."
        else:
            key = (request.get("domain"), request.get("name"))
            label = "The password alias was not read."
        if key not in found:
            found[key] = {"present": False, "message": label}
    return found


def _save_needed(row):
    if not isinstance(row, dict):
        return ""
    value = row.get("save_needed")
    if value is None:
        value = row.get("SaveNeeded")
    return str(value or "").strip().lower()


def _domain_rows(rows):
    indexed = {}
    for row in _rows(rows):
        if not isinstance(row, dict):
            continue
        name = str(row.get("domain") or row.get("Domain") or "").strip()
        if name:
            indexed[name] = row
    return indexed


def _missing(matches, files, aliases):
    reasons = []
    for match in matches:
        file_domain = filestore_domain(match["new_file"], match["domain"])
        file_row = files.get((file_domain, match["new_file"])) or {}
        if not file_row.get("present"):
            text = "The file {0} is not in domain {1}.".format(match["new_file"], file_domain)
            if text not in reasons:
                reasons.append(text)
        if match.get("password_alias"):
            alias_row = aliases.get((match["domain"], match["password_alias"])) or {}
            if not alias_row.get("present"):
                text = "The password alias {0} is not in domain {1}.".format(
                    match["password_alias"], match["domain"]
                )
                if text not in reasons:
                    reasons.append(text)
    return reasons


def _replacement_rows(replacements, matches, files):
    rows = []
    for repl in replacements:
        related = [match for match in matches if match["old_file"] == repl["old"]]
        locations = {
            (filestore_domain(match["new_file"], match["domain"]), match["new_file"])
            for match in related
        }
        if not related:
            file_status = "unused"
        elif locations and all(files.get(key, {}).get("present") for key in locations):
            file_status = "present"
        else:
            file_status = "missing"
        row = {
            "old": repl["old"],
            "new": repl["new"],
            "objects_found": len(related),
            "objects_pending": len([match for match in related if match["pending"]]),
            "objects_already": len([match for match in related if not match["pending"]]),
            "objects_updated": 0,
            "file_status": file_status,
        }
        if repl.get("password_alias"):
            row["password_alias"] = repl["password_alias"]
        rows.append(row)
    return rows


def crypto_replace_plan(payload):
    """Decide which domains may change. A missing shared file blocks every domain that uses it."""
    payload = payload if isinstance(payload, dict) else {}
    scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else payload
    replacements = scope.get("replacements") or []
    matches = scope.get("matches") or []
    failures = scope.get("read_failures") or []
    files = _presence(
        payload.get("file_results"),
        scope.get("file_reads"),
        "file_check",
    )
    aliases = _presence(
        payload.get("alias_results"),
        scope.get("alias_reads"),
        "alias_check",
    )
    status = _domain_rows(payload.get("domains"))
    failure_by_domain = {}
    for failure in failures:
        failure_by_domain.setdefault(failure["domain"], [])
        message = failure.get("message") or "The crypto list was not read."
        if message not in failure_by_domain[failure["domain"]]:
            failure_by_domain[failure["domain"]].append(message)
    names = []
    for match in matches:
        if match["domain"] not in names:
            names.append(match["domain"])
    for domain in failure_by_domain:
        if domain not in names:
            names.append(domain)
    domains = []
    for domain in names:
        group = [match for match in matches if match["domain"] == domain]
        pending = [match for match in group if match["pending"]]
        reasons = list(failure_by_domain.get(domain) or [])
        if reasons:
            result = "failed"
        else:
            reasons.extend(_missing(group, files, aliases))
            if not pending:
                result = "blocked" if reasons else "unchanged"
                if result == "unchanged":
                    reasons.append("The objects already use the new file.")
            else:
                needed = _save_needed(status.get(domain))
                if needed != "off":
                    if needed:
                        reasons.append("SaveNeeded is {0}.".format(needed))
                    else:
                        reasons.append("SaveNeeded was not returned.")
                result = "blocked" if reasons else "ready"
                if result == "ready":
                    reasons.append("The domain can be updated.")
        domains.append({
            "domain": domain,
            "result": result,
            "message": " ".join(reasons),
            "objects": group,
        })
    return {
        "schema": "gr.idg.crypto_replace/v1",
        "appliance": payload.get("appliance"),
        "replacements": _replacement_rows(replacements, matches, files),
        "domains": domains,
    }


def crypto_replace_updated(results):
    """Count retarget results that wrote or would write."""
    count = 0
    for item in _rows(results):
        if not isinstance(item, dict) or item.get("skipped") or item.get("failed"):
            continue
        if item.get("changed"):
            count += 1
    return count


def _read_body(result, class_name):
    config = result.get("config") if isinstance(result.get("config"), dict) else {}
    body = config.get(class_name)
    if isinstance(body, dict):
        return body
    if isinstance(body, list):
        for item in body:
            if isinstance(item, dict):
                return item
    return {}


def _marker_key(item):
    marker = item.get("crypto_object") if isinstance(item.get("crypto_object"), dict) else {}
    class_name = marker.get("class_name") or item.get("class_name") or ""
    name = marker.get("name") or item.get("name") or ""
    if not name:
        return None
    return (class_name, name)


def crypto_replace_verified(payload):
    """Compare a re-read object with the file, alias, state and expiration that were requested."""
    payload = payload if isinstance(payload, dict) else {}
    writes = {}
    for item in _rows(payload.get("writes")):
        if not isinstance(item, dict) or item.get("skipped"):
            continue
        key = _marker_key(item)
        if key:
            writes[key] = item
    reads = {}
    for item in _rows(payload.get("reads")):
        if not isinstance(item, dict) or item.get("skipped"):
            continue
        key = _marker_key(item)
        if key:
            reads[key] = item
    mismatches = []
    for obj in _rows(payload.get("objects")):
        if not isinstance(obj, dict) or not obj.get("pending"):
            continue
        name = obj.get("name")
        key = (obj.get("class_name") or "", name)
        read = reads.get(key)
        if not isinstance(read, dict) or read.get("failed"):
            mismatches.append("{0} was not read back.".format(name))
            continue
        body = _read_body(read, obj.get("class_name"))
        got_file = normalize_filestore(body.get("Filename"))
        if got_file != obj.get("new_file"):
            mismatches.append("{0} still uses {1}.".format(name, got_file or "no file"))
        write = writes.get(key) or {}
        previous = write.get("previous") if isinstance(write.get("previous"), dict) else {}
        expected_alias = obj.get("password_alias") or previous.get("alias") or obj.get("alias") or ""
        got_alias = _alias_name(body)
        if got_alias != expected_alias:
            mismatches.append("{0} alias is {1}.".format(name, got_alias or "empty"))
        expected_admin = previous.get("admin_state") or obj.get("admin_state") or ""
        got_admin = str(body.get("mAdminState") or "")
        if expected_admin and got_admin != expected_admin:
            mismatches.append("{0} admin state is {1}.".format(name, got_admin or "empty"))
        if obj.get("class_name") == "CryptoCertificate":
            expected_ignore = previous.get("ignore_expiration")
            if expected_ignore is None:
                expected_ignore = bool(obj.get("ignore_expiration"))
            if bool(expected_ignore) != (body.get("IgnoreExpiration") == "on"):
                mismatches.append("{0} ignore expiration changed.".format(name))
    return {
        "ok": not mismatches,
        "message": " ".join(mismatches) if mismatches else "The objects match the new file.",
    }


def crypto_replace_saved(payload):
    """Outcome after a domain block. A save that leaves SaveNeeded on stays failed."""
    payload = payload if isinstance(payload, dict) else {}
    domain = payload.get("domain")
    updated = int(payload.get("updated") or 0)
    if payload.get("check_mode"):
        if updated > 0:
            return {
                "domain": domain,
                "result": "checked",
                "message": "Check mode did not write.",
                "updated": 0,
            }
        return {
            "domain": domain,
            "result": "unchanged",
            "message": "The objects already use the new file.",
            "updated": 0,
        }
    if updated <= 0:
        return {
            "domain": domain,
            "result": "unchanged",
            "message": "The objects already use the new file.",
            "updated": 0,
        }
    needed = ""
    for row in _rows(payload.get("domains")):
        if isinstance(row, dict) and str(row.get("domain") or "") == str(domain):
            needed = _save_needed(row)
            break
    if needed == "off":
        return {
            "domain": domain,
            "result": "saved",
            "message": "The domain was saved.",
            "updated": updated,
        }
    if needed:
        message = "SaveNeeded stayed {0} after SaveConfig.".format(needed)
    else:
        message = "SaveNeeded was not returned after SaveConfig."
    return {
        "domain": domain,
        "result": "failed",
        "message": message,
        "updated": updated,
    }


def crypto_replace_rescue(payload):
    """Outcome after a failure. Check mode never claims a revert."""
    payload = payload if isinstance(payload, dict) else {}
    domain = payload.get("domain")
    cause = payload.get("message") or "The domain was not saved."
    if payload.get("check_mode"):
        return {"domain": domain, "result": "failed", "message": cause, "updated": 0}
    updated = crypto_replace_updated(payload.get("writes"))
    restored = crypto_replace_restored(payload.get("restores"))
    if updated > 0 and restored["ok"]:
        return {
            "domain": domain,
            "result": "reverted",
            "message": "The objects were restored to the previous file. {0}".format(cause),
            "updated": 0,
        }
    if updated > 0:
        return {
            "domain": domain,
            "result": "failed",
            "message": restored["message"],
            "updated": 0,
        }
    return {"domain": domain, "result": "failed", "message": cause, "updated": 0}


def crypto_replace_restored(results):
    """True when every restore task that ran completed."""
    messages = []
    for item in _rows(results):
        if not isinstance(item, dict) or item.get("skipped"):
            continue
        if item.get("failed"):
            messages.append(item.get("msg") or "The previous file was not restored.")
    return {
        "ok": not messages,
        "message": " ".join(messages) if messages else "The previous file was restored.",
    }


def _outcome_map(outcomes):
    mapped = {}
    for row in _rows(outcomes):
        if isinstance(row, dict) and row.get("domain"):
            mapped[row["domain"]] = row
    return mapped


def _as_bool(value, default=False):
    """Read a flag from a report. The string false stays false."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in ("true", "yes", "1", "on"):
        return True
    if text in ("false", "no", "0", "off", ""):
        return False
    return default


def _report_counts(report):
    replacements = report.get("replacements") if isinstance(report.get("replacements"), list) else []
    found = 0
    unmatched = 0
    for item in replacements:
        if not isinstance(item, dict):
            continue
        count = int(item.get("objects_found") or 0)
        found += count
        if count == 0:
            unmatched += 1
    return found, unmatched


def crypto_replace_group(payload):
    """Accept the group when every required appliance matched its files and every report is ok.

    An appliance is required unless required is false. A required appliance with no
    matching object stops the group before any domain is saved.
    """
    payload = payload if isinstance(payload, dict) else {}
    expected = [str(name) for name in _rows(payload.get("expected")) if str(name or "").strip()]
    reviewed = []
    problems = []
    seen = []
    for row in _rows(payload.get("hosts")):
        if not isinstance(row, dict):
            problems.append("One appliance review was not a record.")
            continue
        appliance = str(row.get("appliance") or "").strip()
        report = row.get("report") if isinstance(row.get("report"), dict) else {}
        required = _as_bool(row.get("required"), True)
        ok = _as_bool(report.get("ok"), False)
        found, unmatched = _report_counts(report)
        summary = report.get("summary") if isinstance(report.get("summary"), list) else []
        reasons = []
        if required and found == 0:
            reasons.append("This required appliance has no matching crypto objects.")
        elif required and unmatched:
            reasons.append("{0} replacements matched no object.".format(unmatched))
        if not ok:
            text = " ".join(str(item) for item in summary if item)
            reasons.append(text or "The appliance report is not ok.")
        if not required and found == 0 and ok:
            message = "This appliance is not required and has no matching crypto objects."
        elif reasons:
            message = " ".join(reasons)
        else:
            message = "The appliance can be updated."
        if appliance in seen:
            problems.append("{0}: The appliance was reviewed twice.".format(appliance or "unknown"))
        elif appliance:
            seen.append(appliance)
        reviewed.append({
            "appliance": appliance,
            "required": required,
            "ok": ok,
            "accepted": not reasons,
            "objects_found": found,
            "unmatched": unmatched,
            "message": message,
        })
        if reasons:
            problems.append("{0}: {1}".format(appliance or "unknown", message))
    if not reviewed and not expected:
        problems.append("No appliance was reviewed.")
    for name in expected:
        if name not in seen:
            problems.append("{0}: The appliance was not reviewed.".format(name))
    return {
        "schema": "gr.idg.crypto_replace/v1",
        "ok": not problems,
        "summary": problems or ["Every required appliance can be updated."],
        "hosts": reviewed,
    }


def crypto_replace_report(payload):
    """Final report. ok is false when a domain was left blocked, reverted or failed."""
    payload = payload if isinstance(payload, dict) else {}
    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
    outcomes = _outcome_map(payload.get("outcomes"))
    domains = []
    updated_by_domain = {}
    for row in _rows(plan.get("domains")):
        if not isinstance(row, dict):
            continue
        outcome = outcomes.get(row.get("domain")) or {}
        result = outcome.get("result") or row.get("result")
        if row.get("result") == "ready" and not outcome:
            result = "failed"
            message = "The domain outcome was not recorded."
        else:
            message = outcome.get("message") or row.get("message") or ""
        updated = int(outcome.get("updated") or 0) if result == "saved" else 0
        updated_by_domain[row.get("domain")] = updated
        domains.append({
            "domain": row.get("domain"),
            "result": result,
            "message": message,
        })
    replacements = []
    for row in _rows(plan.get("replacements")):
        if not isinstance(row, dict):
            continue
        copied = dict(row)
        copied.pop("password", None)
        copied["objects_updated"] = 0
        replacements.append(copied)
    for domain in _rows(plan.get("domains")):
        updated = updated_by_domain.get(domain.get("domain")) or 0
        if updated <= 0:
            continue
        pending = {}
        for obj in _rows(domain.get("objects")):
            if isinstance(obj, dict) and obj.get("pending"):
                pending[obj.get("old_file")] = pending.get(obj.get("old_file"), 0) + 1
        for row in replacements:
            row["objects_updated"] += pending.get(row.get("old"), 0)
    counts = {}
    for row in domains:
        counts[row["result"]] = counts.get(row["result"], 0) + 1
    unmatched = len([row for row in replacements if row.get("objects_found") == 0])
    missing_files = len([row for row in replacements if row.get("file_status") == "missing"])
    bad = len([row for row in domains if row["result"] in _FAILED_RESULTS])
    if replacements and unmatched == len(replacements):
        notice = "This appliance has no matching crypto objects."
    else:
        notice = "{0} replacements; {1} matched no object.".format(len(replacements), unmatched)
    summary = [
        notice,
        "{0} files are missing.".format(missing_files),
        "{0} domains saved, {1} unchanged, {2} checked, {3} blocked, {4} reverted, {5} failed.".format(
            counts.get("saved", 0),
            counts.get("unchanged", 0),
            counts.get("checked", 0),
            counts.get("blocked", 0),
            counts.get("reverted", 0),
            counts.get("failed", 0),
        ),
    ]
    ok = missing_files == 0 and bad == 0 and len(replacements) > 0
    return {
        "schema": "gr.idg.crypto_replace/v1",
        "appliance": plan.get("appliance"),
        "ok": ok,
        "summary": summary,
        "replacements": replacements,
        "domains": domains,
    }


class FilterModule(object):
    def filters(self):
        return {
            "normalize_filestore": normalize_filestore,
            "crypto_replace_entries": crypto_replace_entries,
            "crypto_replace_scope": crypto_replace_scope,
            "crypto_replace_plan": crypto_replace_plan,
            "crypto_replace_updated": crypto_replace_updated,
            "crypto_replace_verified": crypto_replace_verified,
            "crypto_replace_restored": crypto_replace_restored,
            "crypto_replace_saved": crypto_replace_saved,
            "crypto_replace_rescue": crypto_replace_rescue,
            "crypto_replace_report": crypto_replace_report,
            "crypto_replace_group": crypto_replace_group,
        }
