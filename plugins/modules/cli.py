#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: cli
short_description: "Run CLI commands"
description:
  - "Runs the given CLI commands in one domain."
  - "changed is false when every command is read-only, such as show."
  - "Does not save the domain."
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
  commands:
    description:
      - "CLI commands. The values are masked."
    type: list
    required: true
    elements: str
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
  - "Posts to /v1/system/cli/execute. The domain is the domain query parameter."
  - "commands is masked. Do not use -vvvv in production."
seealso:
  - module: gr.idg.domain_config
    description: "Save the domain after a command that changes it."

"""

EXAMPLES = r"""
- name: Show the firmware
  gr.idg.cli:
    domain: default
    commands:
      - show version

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
screen:
  description:
    - "CLI output lines."
  returned: success
  type: list
  elements: str
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
            "commands": {
                "type": "list",
                "required": True,
                "elements": "str",
                "no_log": True,
            },
        },
        supports_check_mode=False,
    )

    def work():
        client = connect(module)
        return ops.run_cli(client, module.params)

    guard(module, work)


if __name__ == "__main__":
    main()
