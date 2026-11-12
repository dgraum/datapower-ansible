# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: rest_mgmt
short_description: REST management for IBM DataPower
description:
  - HttpApi plugin for the DataPower REST management interface.
  - Inventory selects it with C(ansible_network_os=gr.idg.rest_mgmt).
author:
  - David Grau Merconchini (@dgraum)
version_added: 1.0.0
options:
  timeout:
    description:
      - Seconds to wait for one REST call.
      - Export, import and long synchronizations should raise this value.
    type: int
    default: 30
    vars:
      - name: ansible_httpapi_timeout
      - name: ansible_command_timeout
"""

import json

from ansible.module_utils.six.moves.urllib.error import HTTPError

from ansible_collections.ansible.netcommon.plugins.plugin_utils.httpapi_base import (
    HttpApiBase,
)
from ansible_collections.gr.idg.plugins.module_utils.client import HTTP_AGENT


class HttpApi(HttpApiBase):
    """Send one REST call. A 404 is returned to the module, not raised."""

    def handle_httperror(self, exc):
        if isinstance(exc, HTTPError) and exc.code == 401:
            return super(HttpApi, self).handle_httperror(exc)
        return exc

    def send_request(self, method, path, body=None, headers=None):
        data = None
        if body is not None:
            data = json.dumps(body)
        req_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            req_headers.update(headers)
        response, response_data = self.connection.send(
            path,
            data,
            headers=req_headers,
            method=method,
            timeout=self.get_option("timeout"),
            http_agent=HTTP_AGENT,
        )
        raw = response_data.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8", errors="replace")
        else:
            text = raw
        code = getattr(response, "code", None)
        if code is None:
            code = getattr(response, "status", 0)
        return {"status": int(code), "body": text}
