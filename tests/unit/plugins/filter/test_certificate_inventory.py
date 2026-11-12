# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.gr.idg.plugins.filter.certificate_inventory import (
    active_domains,
    certificate_inventory,
    certificate_objects,
    certificate_path,
    filestore_entries,
)


def test_active_domains_keep_default_and_skip_disabled():
    rows = [
        {"domain": "default", "m_admin_state": "enabled"},
        {"domain": "pagos", "m_admin_state": "enabled"},
        {"domain": "viejo", "m_admin_state": "disabled"},
    ]
    assert active_domains(rows) == ["default", "pagos"]


def test_filestore_entries_keep_names_only():
    content = {
        "filestore": {
            "location": {
                "name": "cert:",
                "file": [
                    {"name": "portal.pem", "content": "SECRET"},
                    {"name": "."},
                ],
                "directory": {"name": "private"},
            }
        }
    }
    assert filestore_entries(content) == {
        "files": ["portal.pem"],
        "directories": ["private"],
    }
    assert certificate_path("cert:", "portal.pem") == "cert:///portal.pem"
    assert certificate_path("cert:///private", "a.pem") == "cert:///private/a.pem"


def test_inventory_separates_files_and_objects():
    report = certificate_inventory({
        "appliance": "idg01",
        "domains": ["default", "pagos"],
        "files": [
            {"domain": "default", "store": "sharedcert", "shared": True, "path": "sharedcert:///ca.pem"},
            {"domain": "pagos", "store": "cert", "shared": False, "path": "cert:///key.pem"},
        ],
        "file_reads": [
            {
                "certificate": True,
                "kind": "certificate",
                "detail": {
                    "subject": "CN=ca",
                    "issuer": "CN=ca",
                    "not_after": "2030-01-01T00:00:00Z",
                    "fingerprint_sha1": "aa",
                },
            },
            {"certificate": False, "kind": "key"},
        ],
        "objects": [
            {
                "domain": "pagos",
                "name": "portal-cert",
                "file": "cert:///portal.pem",
                "state": "enabled",
                "ignore_expiration": False,
            }
        ],
        "object_reads": [
            {"detail": {"subject": "CN=portal", "not_after": "2029-01-01T00:00:00Z"}}
        ],
    })
    assert report["schema"] == "gr.idg.certificate_inventory/v1"
    assert report["files"][0]["is_certificate"] is True
    assert report["files"][0]["shared"] is True
    assert report["files"][0]["subject"] == "CN=ca"
    assert report["files"][1]["kind"] == "key"
    assert report["objects"][0]["detail_ok"] is True
    assert report["objects"][0]["subject"] == "CN=portal"
    assert report["summary"][1] == "2 files checked; 1 certificates."
    assert "SECRET" not in str(report)


def test_certificate_objects_read_the_config_list():
    rows = certificate_objects([
        {
            "domain_name": "pagos",
            "config": {
                "CryptoCertificate": {
                    "name": "portal-cert",
                    "Filename": "cert:///portal.pem",
                    "mAdminState": "enabled",
                    "IgnoreExpiration": "off",
                }
            },
        }
    ])
    assert rows == [{
        "domain": "pagos",
        "name": "portal-cert",
        "file": "cert:///portal.pem",
        "state": "enabled",
        "ignore_expiration": False,
    }]
