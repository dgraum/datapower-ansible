# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import base64
import json
import os
import stat
import tempfile

from ansible_collections.gr.idg.plugins.module_utils.client import (
    IDGClient,
    REDACTED,
    action_id_from_body,
    clean_payload,
    is_absent,
    order_name_first,
    quote_path,
    redact,
    same_config,
    write_private,
)


def test_period_in_a_name_stays_literal():
    assert quote_path(
        "mgmt", "actionqueue", "payments.example"
    ) == "/mgmt/actionqueue/payments.example"
    assert quote_path(
        "mgmt", "config", "default", "Domain", "payments.example"
    ) == "/mgmt/config/default/Domain/payments.example"
    assert quote_path("mgmt", "domains", "config") == "/mgmt/domains/config"


def test_name_is_the_first_key():
    body = order_name_first({"Format": "ZIP", "name": "pagos", "AllFiles": False})
    encoded = json.dumps(body)
    assert list(body.keys())[0] == "name"
    assert encoded.index('"name"') < encoded.index('"Format"')
    assert body["AllFiles"] == "off"


def test_absent_is_404_or_resource_not_found():
    assert is_absent(404, {"error": "missing"})
    assert is_absent(400, {"error": "Resource not found"})
    assert not is_absent(500, {"error": "busy"})


def test_links_are_removed_from_output():
    cleaned = clean_payload({
        "name": "pagos",
        "href": "/mgmt/config/default/Domain/pagos",
        "_links": {"self": {"href": "/x"}},
        "mAdminState": "enabled",
    })
    assert cleaned == {"name": "pagos", "mAdminState": "enabled"}


def test_compare_uses_values_before_redaction():
    current = {"name": "alias", "Password": "one"}
    desired = {"name": "alias", "Password": "two"}
    assert not same_config(current, desired)
    assert redact(current)["Password"] == REDACTED
    assert redact(desired)["Password"] == REDACTED
    assert same_config(redact(current), redact(desired))


def test_action_id_does_not_follow_the_location():
    calls = []

    def transport(method, path, body, headers):
        calls.append((method, path))
        payload = {
            "SaveConfig": "Action request accepted.",
            "_links": {
                "location": {
                    "href": "/mgmt/actionqueue/pagos/pending/SaveConfig-20261031T120000Z-1"
                }
            },
        }
        return 202, json.dumps(payload)

    result = IDGClient(transport).post_action("pagos", {"SaveConfig": {}})
    assert result["action_id"] == "SaveConfig-20261031T120000Z-1"
    assert result["changed"] is True
    assert calls == [("POST", "/mgmt/actionqueue/pagos")]
    assert action_id_from_body({}) is None


def test_get_or_none_treats_404_as_absent():
    def transport(method, path, body, headers):
        return 404, json.dumps({"error": "Resource not found"})

    assert IDGClient(transport).get_or_none("/mgmt/config/pagos/Domain/missing") is None


def test_private_export_is_mode_0600():
    directory = tempfile.mkdtemp()
    path = os.path.join(directory, "export.zip")
    write_private(path, b"secret-package")
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600
    with open(path, "rb") as handle:
        assert handle.read() == b"secret-package"


def test_cli_posts_to_the_telnet_bridge():
    from ansible_collections.gr.idg.plugins.module_utils.ops import run_cli

    seen = {}

    class Response(object):
        status = 200
        data = {"screen": ["ok"]}

    class Client(object):
        def request(self, method, path, body, headers=None, as_json=True):
            seen["method"] = method
            seen["path"] = path
            seen["body"] = body
            seen["headers"] = headers
            seen["as_json"] = as_json
            return Response()

    result = run_cli(Client(), {
        "domain": "payments.example",
        "commands": ["traceroute 10.0.0.8"],
    })
    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/system/cli/execute?domain=payments.example"
    assert seen["body"] == ["traceroute 10.0.0.8"]
    assert seen["headers"] is None
    assert seen["as_json"] is False
    assert result["screen"] == ["ok"]
    assert result["changed"] is False


def test_cli_accepts_the_raw_screen():
    from ansible_collections.gr.idg.plugins.module_utils.client import IDGClient
    from ansible_collections.gr.idg.plugins.module_utils.ops import run_cli

    blob = base64.b64encode(b"Traceroute host (10.0.0.1)\n 1:  10.0.0.1  rtt= 1 ms\n").decode("ascii")

    def transport(method, path, body, headers):
        return 200, blob

    result = run_cli(IDGClient(transport), {
        "domain": "default",
        "commands": ["traceroute host"],
    })
    assert result["screen"] == [blob]
