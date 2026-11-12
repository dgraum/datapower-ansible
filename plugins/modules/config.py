#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: config
short_description: "Read or write one configuration object"
description:
  - "Lists or shows a class when config is omitted."
  - "merged, replaced and deleted write only when the cleaned object differs."
  - "A second run with the same object returns changed false."
  - "Does not create child objects and does not save the domain."
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
  class_name:
    description:
      - "REST configuration class."
    type: str
    required: true
  name:
    description:
      - "Object name. Omit it to list the class."
    type: str
  state:
    description:
      - "merged, replaced or deleted. Omit it to read."
    type: str
    choices:
      - "merged"
      - "replaced"
      - "deleted"
  config:
    description:
      - "REST object body. Keys stay as DataPower sends them."
    type: dict
  view:
    description:
      - "DataPower view query parameter for a read."
    type: str
  depth:
    description:
      - "DataPower depth query parameter for a read."
    type: int
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
    support: full
notes:
  - "Save with gr.idg.domain_config state saved."
seealso:
  - module: gr.idg.domain_config
    description: "Save the domain."
  - module: gr.idg.mgmt_info
    description: "List configuration classes."

"""

EXAMPLES = r"""
- name: Show an object
  gr.idg.config:
    domain: pagos
    class_name: MultiProtocolGateway
    name: payments

- name: Replace an object
  gr.idg.config:
    domain: pagos
    class_name: MultiProtocolGateway
    name: payments
    state: replaced
    config:
      name: payments
      mAdminState: enabled

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
diff:
  description:
    - "Before and after documents for this task."
  returned: when diff is enabled
  type: dict
config:
  description:
    - "Cleaned configuration document that can be sent again."
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
            "class_name": {
                "type": "str",
                "required": True,
            },
            "name": {
                "type": "str",
            },
            "state": {
                "type": "str",
                "choices": ['merged', 'replaced', 'deleted'],
            },
            "config": {
                "type": "dict",
            },
            "view": {
                "type": "str",
            },
            "depth": {
                "type": "int",
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
        return ops.ensure_config(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
