#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: tcpconnectiontest
short_description: "Test a TCP connection from the appliance"
description:
  - "Posts TCPConnectionTest and returns action_id."
  - "The probe runs every time. This module does not wait."
version_added: "1.0.0"
author:
  - "David Grau Merconchini (@dgraum)"
extends_documentation_fragment:
  - gr.idg.connection
options:
  domain:
    description:
      - "Accepted so module_defaults can set a domain. This module reads the default domain."
    type: str
    default: "default"
  host:
    description:
      - "Remote host."
    type: str
    required: true
  port:
    description:
      - "Remote port."
    type: int
    required: true
  timeout:
    description:
      - "Probe timeout in seconds."
    type: int
  ip_version:
    description:
      - "IP version hint."
    type: str
  local_address:
    description:
      - "Local address to send from."
    type: str
attributes:
  check_mode:
    description:
      - Check mode behavior for this module.
    support: none
  diff_mode:
    description:
      - Diff support for this module.
    support: none
notes:
  - "Wait with gr.idg.action_queue when the result is asynchronous."
seealso:
  - module: gr.idg.ping
    description: "Ping from the appliance."

"""

EXAMPLES = r"""
- name: Test TCP 443
  gr.idg.tcpconnectiontest:
    host: 10.0.0.8
    port: 443

"""

RETURN = r"""
changed:
  description:
    - "Whether this task changed the appliance."
  returned: always
  type: bool
msg:
  description:
    - "What this task did."
  returned: always
  type: str
action_id:
  description:
    - "Identifies the accepted action. This module does not wait for it to finish."
  returned: when the action is accepted
  type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.gr.idg.plugins.module_utils import ops
from ansible_collections.gr.idg.plugins.module_utils.runner import connect, guard


def main():
    module = AnsibleModule(
        argument_spec={
            "domain": {
                "type": "str",
                "default": 'default',
            },
            "host": {
                "type": "str",
                "required": True,
            },
            "port": {
                "type": "int",
                "required": True,
            },
            "timeout": {
                "type": "int",
            },
            "ip_version": {
                "type": "str",
            },
            "local_address": {
                "type": "str",
            },
        },
        supports_check_mode=False,
    )

    def work():
        client = connect(module)
        fields = {'RemoteHost': module.params['host'], 'RemotePort': module.params['port']}
        if module.params.get('timeout'):
            fields['timeout'] = module.params['timeout']
        if module.params.get('ip_version'):
            fields['useIPv'] = module.params['ip_version']
        if module.params.get('local_address'):
            fields['LocalAddress'] = module.params['local_address']
        return ops.network_probe(client, 'TCPConnectionTest', fields)

    guard(module, work)


if __name__ == "__main__":
    main()
