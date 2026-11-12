#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: wsgateway_wsdl_refresh
short_description: "Refresh one WSDL"
description:
  - "Posts RefreshWSDL and returns action_id."
  - "Does not read WSDL status before or after the post."
  - "Runs every time."
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
  ws_gateway:
    description:
      - "WSGateway name."
    type: str
    required: true
  wsdl_source_location:
    description:
      - "WSDL location to refresh."
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
  - "Read status with gr.idg.wsgateway_wsdl_status. Wait with gr.idg.action_queue."
seealso:
  - module: gr.idg.wsgateway_wsdl_status
    description: "Read WSDL status."
  - module: gr.idg.action_queue
    description: "Wait for the refresh."

"""

EXAMPLES = r"""
- name: Refresh a WSDL
  gr.idg.wsgateway_wsdl_refresh:
    domain: pagos
    ws_gateway: payments
    wsdl_source_location: local:///wsdl/payments.wsdl
  register: posted

- name: Wait for the refresh
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
            "ws_gateway": {
                "type": "str",
                "required": True,
            },
            "wsdl_source_location": {
                "type": "str",
                "required": True,
            },
        },
        supports_check_mode=False,
    )

    def work():
        client = connect(module)
        posted = ops.refresh_wsdl(client, module.params)
        posted['domain'] = module.params['domain']
        return posted

    guard(module, work)


if __name__ == "__main__":
    main()
