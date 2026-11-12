#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: action
short_description: "Post one action"
description:
  - "Posts one action and returns action_id."
  - "Does not wait for the queue."
  - "Export, Import and LoadConfiguration stay on gr.idg.domain_config."
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
  action:
    description:
      - "Action name."
    type: str
    required: true
  parameters:
    description:
      - "Action parameters. Secret keys are redacted in the result."
    type: dict
    default: {}
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
  - "The next task polls gr.idg.action_queue until status is processed or completed."
seealso:
  - module: gr.idg.action_queue
    description: "Read an accepted action."
  - module: gr.idg.domain_config
    description: "Export, import or save."

"""

EXAMPLES = r"""
- name: Flush the document cache
  gr.idg.action:
    domain: pagos
    action: FlushDocumentCache
    parameters:
      XMLManager: default
  register: posted

- name: Wait for the flush
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
            "action": {
                "type": "str",
                "required": True,
            },
            "parameters": {
                "type": "dict",
                "default": {},
            },
        },
        supports_check_mode=False,
    )

    def work():
        client = connect(module)
        return ops.post_named_action(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
