#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: status
short_description: "Read one status class"
description:
  - "Reads one status class by name."
  - "Does not change configuration."
  - "Fails with the class name when the firmware does not provide it."
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
      - "Status class name, such as ObjectStatus or DNSCacheStatus."
    type: str
    required: true
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
  - "Use a dedicated sensor module when you want its named record."
seealso:
  - module: gr.idg.mgmt_info
    description: "List status classes on this firmware."

"""

EXAMPLES = r"""
- name: Read object status
  gr.idg.status:
    domain: pagos
    name: ObjectStatus

"""

RETURN = r"""
changed:
  description:
    - "Whether this task changed the appliance."
  returned: always
  type: bool
status:
  description:
    - "Status records in snake_case."
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
            "raw": {
                "type": "bool",
                "default": False,
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.snake_status(client, module.params['domain'], module.params['name'], 'status', module.params['raw'])

    guard(module, work)


if __name__ == "__main__":
    main()
