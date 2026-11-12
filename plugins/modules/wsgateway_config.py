#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: wsgateway_config
short_description: "Read one web service gateway"
description:
  - "Reads one WSGateway object."
  - "Does not change the gateway and does not save the domain."
version_added: "1.0.0"
author:
  - "David Grau Merconchini (@dgraum)"
extends_documentation_fragment:
  - gr.idg.connection
options:
  domain:
    description:
      - "Application domain the task reads or changes."
    type: str
    required: true
  name:
    description:
      - "WSGateway object name."
    type: str
    required: true
  state:
    description:
      - "Only show is supported. The task does not write the gateway."
    type: str
    default: show
    choices:
      - show
  raw:
    description:
      - "When true, include the cleaned appliance payload."
    type: bool
    default: false
attributes:
  check_mode:
    description:
      - Check mode behavior for this module.
    support: full
  diff_mode:
    description:
      - Diff support for this module.
    support: none
notes:
  - "To change the object, use gr.idg.config. To save, use gr.idg.domain_config."
seealso:
  - module: gr.idg.config
    description: "Write a configuration object from REST JSON."
  - module: gr.idg.wsgateway_wsdl_status
    description: "Read WSDL status."

"""

EXAMPLES = r"""
- name: Read a web service gateway
  gr.idg.wsgateway_config:
    domain: pagos
    name: payments

"""

RETURN = r"""
changed:
  description:
    - "Whether this task changed the appliance."
  returned: always
  type: bool
config:
  description:
    - "Cleaned WSGateway object. It can be sent again to gr.idg.config."
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.gr.idg.plugins.module_utils import ops
from ansible_collections.gr.idg.plugins.module_utils.runner import connect, guard


def main():
    module = AnsibleModule(
        argument_spec={
            "domain": {
                "type": "str",
                "required": True,
            },
            "name": {
                "type": "str",
                "required": True,
            },
            "state": {
                "type": "str",
                "default": "show",
                "choices": ["show"],
            },
            "raw": {
                "type": "bool",
                "default": False,
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.show_gateway(client, module.params)

    guard(module, work)


if __name__ == "__main__":
    main()
