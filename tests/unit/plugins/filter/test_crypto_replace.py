# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

from ansible_collections.gr.idg.plugins.filter.crypto_replace import (
    crypto_replace_entries,
    crypto_replace_group,
    crypto_replace_plan,
    crypto_replace_report,
    crypto_replace_rescue,
    crypto_replace_saved,
    crypto_replace_scope,
    crypto_replace_verified,
)
from ansible_collections.gr.idg.plugins.module_utils.ops import normalize_filestore


def test_normalize_filestore_collapses_slashes_and_rejects_other_stores():
    assert normalize_filestore("cert:/portal.pem") == "cert:///portal.pem"
    assert normalize_filestore("cert://portal.pem") == "cert:///portal.pem"
    assert normalize_filestore("cert:///portal.pem") == "cert:///portal.pem"
    assert normalize_filestore("local:///portal.pem") == ""


def test_entries_keep_the_alias_name_and_drop_the_password():
    result = crypto_replace_entries([{
        "old": "cert:/old.pem",
        "new": "cert:///new.pem",
        "password": "s3cret",
        "password_alias": "portal",
    }])
    assert result["errors"] == []
    assert result["replacements"] == [{
        "old": "cert:///old.pem",
        "new": "cert:///new.pem",
        "password_alias": "portal",
    }]
    assert "s3cret" not in json.dumps(result)


def test_entries_reject_a_repeated_or_foreign_path():
    repeated = crypto_replace_entries([
        {"old": "cert:///a.pem", "new": "cert:///b.pem"},
        {"old": "cert:/a.pem", "new": "cert:///c.pem"},
    ])
    assert repeated["errors"]
    same = crypto_replace_entries([
        {"old": "cert:///a.pem", "new": "cert:/a.pem"},
    ])
    assert same["errors"]
    foreign = crypto_replace_entries([
        {"old": "local:///a.pem", "new": "cert:///b.pem"},
    ])
    assert foreign["errors"]


def _listed(domain, class_name, objects):
    return {
        "domain_name": domain,
        "domain": domain,
        "failed": False,
        "config": {class_name: objects},
    }


def test_scope_splits_local_files_from_domain_aliases():
    scope = crypto_replace_scope({
        "replacements": [
            {"old": "cert:///old.pem", "new": "cert:///new.pem"},
            {
                "old": "sharedcert:///old.key",
                "new": "sharedcert:///new.key",
                "password_alias": "hsm",
                "password": "s3cret",
            },
        ],
        "domains": [
            {"domain": "default", "m_admin_state": "enabled"},
            {"domain": "pagos", "m_admin_state": "enabled"},
            {"domain": "portal", "m_admin_state": "enabled"},
            {"domain": "viejo", "m_admin_state": "disabled"},
        ],
        "key_reads": [
            _listed("pagos", "CryptoKey", [{
                "name": "pagos-key",
                "Filename": "sharedcert:/old.key",
                "mAdminState": "enabled",
                "Alias": {"value": "old"},
            }]),
            _listed("portal", "CryptoKey", [{
                "name": "portal-key",
                "Filename": "sharedcert:///old.key",
                "mAdminState": "enabled",
                "PasswordAlias": "old",
            }]),
            _listed("viejo", "CryptoKey", [{
                "name": "retired",
                "Filename": "sharedcert:///old.key",
                "mAdminState": "enabled",
            }]),
        ],
        "certificate_reads": [
            _listed("pagos", "CryptoCertificate", [{
                "name": "pagos-cert",
                "Filename": "cert:///old.pem",
                "mAdminState": "enabled",
                "IgnoreExpiration": "on",
            }]),
            _listed("portal", "CryptoCertificate", [{
                "name": "portal-cert",
                "Filename": "cert:///old.pem",
                "mAdminState": "disabled",
                "IgnoreExpiration": "off",
            }]),
        ],
    })
    assert scope["errors"] == []
    assert "s3cret" not in json.dumps(scope)
    assert scope["file_reads"] == [
        {"domain": "default", "path": "sharedcert:///new.key", "shared": True},
        {"domain": "pagos", "path": "cert:///new.pem", "shared": False},
        {"domain": "portal", "path": "cert:///new.pem", "shared": False},
    ]
    assert scope["alias_reads"] == [
        {"domain": "pagos", "name": "hsm"},
        {"domain": "portal", "name": "hsm"},
    ]
    assert all(match["domain"] != "viejo" for match in scope["matches"])
    pagos_key = [
        match for match in scope["matches"]
        if match["name"] == "pagos-key"
    ][0]
    assert pagos_key["pending"] is True
    assert pagos_key["password_alias"] == "hsm"
    assert pagos_key["alias"] == "old"


def test_plan_blocks_one_domain_for_its_alias_and_all_for_a_shared_file():
    scope = crypto_replace_scope({
        "replacements": [{
            "old": "sharedcert:///old.key",
            "new": "sharedcert:///new.key",
            "password_alias": "hsm",
        }],
        "domains": [
            {"domain": "pagos", "m_admin_state": "enabled", "save_needed": "off"},
            {"domain": "portal", "m_admin_state": "enabled", "save_needed": "off"},
        ],
        "key_reads": [
            _listed("pagos", "CryptoKey", [{
                "name": "pagos-key",
                "Filename": "sharedcert:///old.key",
                "mAdminState": "enabled",
                "Alias": {"value": "old"},
            }]),
            _listed("portal", "CryptoKey", [{
                "name": "portal-key",
                "Filename": "sharedcert:///old.key",
                "mAdminState": "enabled",
                "Alias": {"value": "old"},
            }]),
        ],
        "certificate_reads": [],
    })
    present_file = {
        "file_check": {"domain": "default", "path": "sharedcert:///new.key"},
        "domain": "default",
        "target": "sharedcert:///new.key",
        "failed": False,
        "content": {"file": {"name": "new.key"}},
    }
    pagos_alias = {
        "alias_check": {"domain": "pagos", "name": "hsm"},
        "domain": "pagos",
        "failed": False,
        "config": {"PasswordAlias": {"name": "hsm", "mAdminState": "enabled"}},
    }
    portal_alias = {
        "alias_check": {"domain": "portal", "name": "hsm"},
        "domain": "portal",
        "failed": True,
        "msg": "The target does not exist.",
    }
    plan = crypto_replace_plan({
        "appliance": "idg01",
        "domains": [
            {"domain": "pagos", "save_needed": "off"},
            {"domain": "portal", "save_needed": "off"},
        ],
        "scope": scope,
        "file_results": [present_file],
        "alias_results": [pagos_alias, portal_alias],
    })
    by_domain = {row["domain"]: row for row in plan["domains"]}
    assert by_domain["pagos"]["result"] == "ready"
    assert by_domain["portal"]["result"] == "blocked"
    assert "portal" in by_domain["portal"]["message"]
    assert plan["replacements"][0]["file_status"] == "present"
    assert "s3cret" not in json.dumps(plan)

    missing = crypto_replace_plan({
        "appliance": "idg01",
        "domains": [
            {"domain": "pagos", "save_needed": "off"},
            {"domain": "portal", "save_needed": "off"},
        ],
        "scope": scope,
        "file_results": [{
            "file_check": {"domain": "default", "path": "sharedcert:///new.key"},
            "failed": True,
            "msg": "The target does not exist.",
        }],
        "alias_results": [pagos_alias, portal_alias],
    })
    assert {row["result"] for row in missing["domains"]} == {"blocked"}
    assert missing["replacements"][0]["file_status"] == "missing"


def test_plan_blocks_a_dirty_domain_and_accepts_an_object_already_retargeted():
    scope = crypto_replace_scope({
        "replacements": [{
            "old": "cert:///old.pem",
            "new": "cert:///new.pem",
        }],
        "domains": [
            {"domain": "pagos", "m_admin_state": "enabled"},
        ],
        "certificate_reads": [
            _listed("pagos", "CryptoCertificate", [{
                "name": "portal-cert",
                "Filename": "cert:/new.pem",
                "mAdminState": "enabled",
                "IgnoreExpiration": "off",
            }]),
        ],
    })
    file_result = {
        "file_check": {"domain": "pagos", "path": "cert:///new.pem"},
        "failed": False,
        "content": {"file": {"name": "new.pem"}},
    }
    clean = crypto_replace_plan({
        "domains": [{"domain": "pagos", "save_needed": "on"}],
        "scope": scope,
        "file_results": [file_result],
        "alias_results": [],
    })
    assert clean["domains"][0]["result"] == "unchanged"
    dirty_scope = crypto_replace_scope({
        "replacements": [{
            "old": "cert:///old.pem",
            "new": "cert:///new.pem",
        }],
        "domains": [{"domain": "pagos", "m_admin_state": "enabled"}],
        "certificate_reads": [
            _listed("pagos", "CryptoCertificate", [{
                "name": "portal-cert",
                "Filename": "cert:///old.pem",
                "mAdminState": "disabled",
                "IgnoreExpiration": "on",
            }]),
        ],
    })
    dirty = crypto_replace_plan({
        "domains": [{"domain": "pagos", "save_needed": "on"}],
        "scope": dirty_scope,
        "file_results": [file_result],
        "alias_results": [],
    })
    assert dirty["domains"][0]["result"] == "blocked"
    assert "SaveNeeded" in dirty["domains"][0]["message"]


def test_verified_report_and_rescue_keep_the_saved_result_immutable():
    checked = crypto_replace_verified({
        "objects": [{
            "class_name": "CryptoCertificate",
            "name": "portal-cert",
            "new_file": "cert:///new.pem",
            "pending": True,
            "alias": "portal",
            "password_alias": "",
            "admin_state": "disabled",
            "ignore_expiration": True,
        }],
        "writes": [{
            "crypto_object": {"class_name": "CryptoCertificate", "name": "portal-cert"},
            "name": "portal-cert",
            "changed": True,
            "previous": {
                "alias": "portal",
                "admin_state": "disabled",
                "ignore_expiration": True,
            },
        }],
        "reads": [{
            "crypto_object": {"class_name": "CryptoCertificate", "name": "portal-cert"},
            "failed": False,
            "config": {"CryptoCertificate": {
                "name": "portal-cert",
                "Filename": "cert:/new.pem",
                "mAdminState": "disabled",
                "IgnoreExpiration": "on",
                "Alias": {"value": "portal"},
            }},
        }],
    })
    assert checked["ok"] is True

    changed_state = crypto_replace_verified({
        "objects": [{
            "class_name": "CryptoKey",
            "name": "portal-key",
            "new_file": "cert:///new.key",
            "pending": True,
            "password_alias": "hsm",
            "alias": "old",
        }],
        "writes": [{
            "crypto_object": {"class_name": "CryptoKey", "name": "portal-key"},
            "previous": {"alias": "old", "admin_state": "disabled", "ignore_expiration": False},
        }],
        "reads": [{
            "crypto_object": {"class_name": "CryptoKey", "name": "portal-key"},
            "config": {"CryptoKey": {
                "Filename": "cert:///new.key",
                "mAdminState": "enabled",
                "Alias": {"value": "hsm"},
            }},
        }],
    })
    assert changed_state["ok"] is False
    assert "admin state" in changed_state["message"]

    plan = {
        "schema": "gr.idg.crypto_replace/v1",
        "appliance": "idg01",
        "replacements": [{
            "old": "cert:///old.pem",
            "new": "cert:///new.pem",
            "objects_found": 1,
            "objects_pending": 1,
            "objects_already": 0,
            "objects_updated": 0,
            "file_status": "present",
        }],
        "domains": [{
            "domain": "pagos",
            "result": "ready",
            "message": "The domain can be updated.",
            "objects": [{
                "old_file": "cert:///old.pem",
                "pending": True,
                "name": "portal-cert",
            }],
        }],
    }
    saved = crypto_replace_saved({
        "domain": "pagos",
        "updated": 1,
        "check_mode": False,
        "domains": [{"domain": "pagos", "save_needed": "off"}],
    })
    report = crypto_replace_report({"plan": plan, "outcomes": [saved]})
    assert report["ok"] is True
    assert report["replacements"][0]["objects_updated"] == 1
    assert report["domains"][0]["result"] == "saved"

    dirty = crypto_replace_saved({
        "domain": "pagos",
        "updated": 1,
        "domains": [{"domain": "pagos", "save_needed": "on"}],
    })
    assert dirty["result"] == "failed"
    failed = crypto_replace_report({"plan": plan, "outcomes": [dirty]})
    assert failed["ok"] is False

    rescue = crypto_replace_rescue({
        "domain": "pagos",
        "check_mode": True,
        "message": "The object was not read back.",
        "writes": [{"changed": True, "failed": False}],
        "restores": [],
    })
    assert rescue["result"] == "failed"
    reverted = crypto_replace_rescue({
        "domain": "pagos",
        "check_mode": False,
        "message": "The object was not read back.",
        "writes": [{"changed": True}],
        "restores": [{"failed": False, "changed": True}],
    })
    assert reverted["result"] == "reverted"


def test_an_appliance_without_matching_objects_is_ok():
    report = crypto_replace_report({
        "plan": {
            "appliance": "idg01",
            "replacements": [
                {
                    "old": "cert:///old.pem",
                    "new": "cert:///new.pem",
                    "objects_found": 0,
                    "objects_pending": 0,
                    "objects_already": 0,
                    "objects_updated": 0,
                    "file_status": "unused",
                },
                {
                    "old": "cert:///old.key",
                    "new": "cert:///new.key",
                    "objects_found": 0,
                    "objects_pending": 0,
                    "objects_already": 0,
                    "objects_updated": 0,
                    "file_status": "unused",
                },
            ],
            "domains": [],
        },
        "outcomes": [],
    })
    assert report["ok"] is True
    assert report["summary"][0] == "This appliance has no matching crypto objects."


def _host_report(appliance, replacements, domains):
    return crypto_replace_report({
        "plan": {
            "appliance": appliance,
            "replacements": replacements,
            "domains": domains,
        },
        "outcomes": [],
    })


def _unused_replacement(old, new):
    return {
        "old": old,
        "new": new,
        "objects_found": 0,
        "objects_pending": 0,
        "objects_already": 0,
        "objects_updated": 0,
        "file_status": "unused",
    }


def test_group_review_rejects_a_required_appliance_without_objects():
    report = _host_report("idg02", [
        _unused_replacement("cert:///old.pem", "cert:///new.pem"),
        _unused_replacement("cert:///old.key", "cert:///new.key"),
    ], [])
    group = crypto_replace_group({
        "expected": ["idg02"],
        "hosts": [{"appliance": "idg02", "required": True, "report": report}],
    })
    assert report["ok"] is True
    assert group["ok"] is False
    assert group["summary"][0] == (
        "idg02: This required appliance has no matching crypto objects."
    )


def test_group_review_accepts_an_optional_appliance_without_objects():
    idle = _host_report("idg01", [
        _unused_replacement("cert:///old.pem", "cert:///new.pem"),
    ], [])
    ready = _host_report("idg02", [{
        "old": "cert:///old.pem",
        "new": "cert:///new.pem",
        "objects_found": 1,
        "objects_pending": 1,
        "objects_already": 0,
        "objects_updated": 0,
        "file_status": "present",
    }], [{
        "domain": "pagos",
        "result": "unchanged",
        "message": "The objects already use the new file.",
    }])
    group = crypto_replace_group({
        "expected": ["idg01", "idg02"],
        "hosts": [
            {"appliance": "idg01", "required": "false", "report": idle},
            {"appliance": "idg02", "required": "true", "report": ready},
        ],
    })
    assert idle["ok"] is True
    assert ready["ok"] is True
    assert group["ok"] is True
    assert group["summary"] == ["Every required appliance can be updated."]
    assert group["hosts"][0]["required"] is False
    assert group["hosts"][1]["required"] is True


def test_group_review_stops_when_a_required_file_is_missing():
    report = _host_report("idg02", [{
        "old": "cert:///old.pem",
        "new": "cert:///new.pem",
        "objects_found": 1,
        "objects_pending": 1,
        "objects_already": 0,
        "objects_updated": 0,
        "file_status": "missing",
    }], [{
        "domain": "pagos",
        "result": "blocked",
        "message": "The file cert:///new.pem is not in domain pagos.",
    }])
    group = crypto_replace_group({
        "expected": ["idg01", "idg02"],
        "hosts": [{"appliance": "idg02", "required": True, "report": report}],
    })
    assert report["ok"] is False
    assert group["ok"] is False
    assert "files are missing" in group["summary"][0]
    assert group["summary"][1] == "idg01: The appliance was not reviewed."


def test_group_review_rejects_a_required_path_that_matches_nothing():
    report = _host_report("idg02", [
        {
            "old": "cert:///old.pem",
            "new": "cert:///new.pem",
            "objects_found": 2,
            "objects_pending": 2,
            "objects_already": 0,
            "objects_updated": 0,
            "file_status": "present",
        },
        _unused_replacement("cert:///missing.pem", "cert:///other.pem"),
    ], [{
        "domain": "pagos",
        "result": "checked",
        "message": "Check mode did not write.",
    }])
    group = crypto_replace_group({
        "expected": ["idg02"],
        "hosts": [{"appliance": "idg02", "required": True, "report": report}],
    })
    assert report["ok"] is True
    assert group["ok"] is False
    assert group["summary"][0] == "idg02: 1 replacements matched no object."
