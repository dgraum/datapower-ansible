#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: action_queue
short_description: "Read one queued action"
description:
  - "Reads one action already accepted by the appliance."
  - "Does not post another action and does not wait by itself."
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
  action_id:
    description:
      - "Identifier returned by the action that was posted."
    type: str
    required: true
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
  - "Use until when the play should wait for processed or completed."
seealso:
  - module: gr.idg.action
    description: "Post an action."

"""

EXAMPLES = r"""
- name: Read an action
  gr.idg.action_queue:
    domain: pagos
    action_id: "{{ posted.action_id }}"
  register: queue
  until: queue.status in ['processed', 'completed']
  retries: 30
  delay: 2

"""

RETURN = r"""
changed:
  description:
    - "Whether this task changed the appliance."
  returned: always
  type: bool
status:
  description:
    - "Queue status, such as processed or completed."
  returned: success
  type: str
action_id:
  description:
    - "The action that was read. This module does not post it."
  returned: always
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
                "required": True,
            },
            "action_id": {
                "type": "str",
                "required": True,
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.poll_action(client, module.params)

    guard(module, work)


if __name__ == "__main__":
    main()
