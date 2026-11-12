#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: loadbalancer_groupmembers
short_description: "Set load balancer group members"
description:
  - "Writes the member set with one POST."
  - "Does not write when the desired set already matches, so a second run returns changed false."
  - "Does not save the domain and does not read the members again after the write."
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
  balancer_group:
    description:
      - "Load balancer group name."
    type: str
    required: true
  state:
    description:
      - "present adds or updates. absent removes the named members."
    type: str
    default: "present"
    choices:
      - "present"
      - "absent"
  members:
    description:
      - "Members to add, update or remove."
    type: list
    required: true
    elements: dict
    suboptions:
      server:
        description:
          - "Server name or address."
        type: str
        required: true
      health_port:
        description:
          - "Health-check port."
        type: int
      admin_state:
        description:
          - "Member administrative state."
        type: str
        default: "enabled"
        choices:
          - "enabled"
          - "disabled"
      mapped_port:
        description:
          - "Port on the real server."
        type: int
      weight:
        description:
          - "Relative weight."
        type: int
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
  - module: gr.idg.loadbalancer_status
    description: "Read load balancer status."

"""

EXAMPLES = r"""
- name: Set members
  gr.idg.loadbalancer_groupmembers:
    domain: pagos
    balancer_group: payments
    state: present
    members:
      - server: 10.0.0.8
        mapped_port: 8443
        weight: 1

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
members:
  description:
    - "Desired member set."
  returned: success
  type: list
  elements: dict
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
            "balancer_group": {
                "type": "str",
                "required": True,
            },
            "state": {
                "type": "str",
                "default": 'present',
                "choices": ['present', 'absent'],
            },
            "members": {
                "type": "list",
                "required": True,
                "elements": "dict",
                "options": {
                    "server": {
                        "type": "str",
                        "required": True,
                    },
                    "health_port": {
                        "type": "int",
                    },
                    "admin_state": {
                        "type": "str",
                        "default": 'enabled',
                        "choices": ['enabled', 'disabled'],
                    },
                    "mapped_port": {
                        "type": "int",
                    },
                    "weight": {
                        "type": "int",
                    },
                },
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.load_balancer_members(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
