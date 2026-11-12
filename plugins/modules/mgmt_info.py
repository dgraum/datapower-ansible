#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: mgmt_info
short_description: "List REST classes on the appliance"
description:
  - "Lists configuration classes, status providers or actions."
  - "With class_name, also reads the metadata or config document for that class."
  - "Does not change configuration."
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
    default: "default"
  section:
    description:
      - "config, status or actions."
    type: str
    required: true
    choices:
      - "config"
      - "status"
      - "actions"
  class_name:
    description:
      - "Class whose metadata should be included."
    type: str
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
  - "This task only reads."
seealso:
  - module: gr.idg.config
    description: "Read or write one class."
  - module: gr.idg.status
    description: "Read one status class."

"""

EXAMPLES = r"""
- name: List status classes
  gr.idg.mgmt_info:
    section: status

"""

RETURN = r"""
changed:
  description:
    - "Whether this task changed the appliance."
  returned: always
  type: bool
classes:
  description:
    - "Class or action names advertised by the appliance."
  returned: success
  type: list
  elements: str
schema:
  description:
    - "Metadata or documentation for class_name."
  returned: when class_name is set
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
                "default": 'default',
            },
            "section": {
                "type": "str",
                "required": True,
                "choices": ['config', 'status', 'actions'],
            },
            "class_name": {
                "type": "str",
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
        return ops.management_info(client, module.params)

    guard(module, work)


if __name__ == "__main__":
    main()
