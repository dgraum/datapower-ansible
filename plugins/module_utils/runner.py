# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

"""Module helpers. Redaction happens here, on the way out."""

from ansible.module_utils.connection import Connection
from ansible.module_utils.connection import ConnectionError

from ansible_collections.gr.idg.plugins.module_utils.client import (
    IDGClient,
    IDGError,
    redact,
    redact_text,
)


def connect(module):
    """Build a client on the httpapi socket Ansible opened for this task."""
    connection = Connection(module._socket_path)

    def request_fn(method, path, body, headers):
        try:
            result = connection.send_request(method, path, body, headers)
        except ConnectionError as exc:
            message = redact_text(getattr(exc, "args", ("",))[0] or str(exc))
            module.fail_json(msg=message or "The REST connection failed.")
        if not isinstance(result, dict) or "status" not in result:
            module.fail_json(msg="The REST plugin returned an unexpected response.")
        return result["status"], result.get("body")

    return IDGClient(request_fn)


def _public(result, diff_enabled):
    payload = {"changed": bool(result.get("changed", False))}
    for key, value in result.items():
        if key in ("changed", "diff") or value is None:
            continue
        payload[key] = redact(value)
    diff = result.get("diff") or {}
    if diff_enabled and diff:
        public_diff = {}
        for side in ("before", "after"):
            if diff.get(side) is not None:
                public_diff[side] = redact(diff[side])
        if public_diff:
            payload["diff"] = public_diff
    return payload


def finish(module, result):
    module.exit_json(**_public(result, module._diff))


def fail(module, msg, result=None):
    extra = _public(result or {}, module._diff)
    extra.pop("changed", None)
    module.fail_json(msg=redact_text(msg) or "The request failed.", **extra)


def guard(module, work):
    """Run ``work`` and turn client errors into fail_json. No traceback."""
    try:
        result = work()
    except IDGError as exc:
        fail(module, str(exc))
    except Exception as exc:
        fail(module, "The request failed: {0}".format(exc.__class__.__name__))
    else:
        finish(module, result)
