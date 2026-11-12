#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: wsrr_savedsearchsubscription_sync
short_description: "Synchronize one WSRR subscription"
description:
  - "Posts WsrrSynchronize and returns action_id."
  - "The sync runs every time. This module does not wait and does not read status afterwards."
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
  subscription:
    description:
      - "WSRR saved-search subscription name."
    type: str
    required: true
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
  - "Read status with gr.idg.wsrr_savedsearchsubscription_status."
seealso:
  - module: gr.idg.wsrr_savedsearchsubscription_status
    description: "Read subscription status."
  - module: gr.idg.action_queue
    description: "Wait for the sync."

"""

EXAMPLES = r"""
- name: Synchronize a subscription
  gr.idg.wsrr_savedsearchsubscription_sync:
    domain: pagos
    subscription: payments
  register: posted

- name: Wait for the sync
  gr.idg.action_queue:
    domain: pagos
    action_id: "{{ posted.action_id }}"
  register: queue
  until: queue.status in ['processed', 'completed']
  retries: 60
  delay: 5

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
            "subscription": {
                "type": "str",
                "required": True,
            },
        },
        supports_check_mode=False,
    )

    def work():
        client = connect(module)
        posted = ops.sync_subscription(client, module.params)
        posted['domain'] = module.params['domain']
        return posted

    guard(module, work)


if __name__ == "__main__":
    main()
