#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: chkpoint
short_description: "Save, remove or restore a checkpoint"
description:
  - "Posts one checkpoint action and returns action_id."
  - "Does not save the running configuration except through the checkpoint action itself."
  - "Removing a checkpoint that is already absent returns changed false."
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
      - "Checkpoint name."
    type: str
    required: true
  state:
    description:
      - "present saves, absent removes, restored rolls back."
    type: str
    default: "present"
    choices:
      - "present"
      - "absent"
      - "restored"
attributes:
  check_mode:
    description:
      - Check mode behavior for this module.
    support: partial
    details:
      - The checkpoint action is reported and is not sent.
  diff_mode:
    description:
      - Diff support for this module.
    support: none
notes:
  - "Wait with gr.idg.action_queue. This module does not poll."
seealso:
  - module: gr.idg.chkpoint_status
    description: "Read checkpoint status."
  - module: gr.idg.action_queue
    description: "Wait for the checkpoint action."

"""

EXAMPLES = r"""
- name: Save a checkpoint
  gr.idg.chkpoint:
    domain: pagos
    name: before-change
    state: present
  register: posted

- name: Wait for the checkpoint
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
                "required": True,
            },
            "name": {
                "type": "str",
                "required": True,
            },
            "state": {
                "type": "str",
                "default": 'present',
                "choices": ['present', 'absent', 'restored'],
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.checkpoint(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
