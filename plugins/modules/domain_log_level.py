#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: domain_log_level
short_description: "Set the domain log level"
description:
  - "Sets the all class priority on one log target."
  - "Does not save the domain."
  - "A second run with the same level returns changed false."
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
  log_target:
    description:
      - "Log target object name."
    type: str
    default: "default-log"
  log_level:
    description:
      - "Priority for the all event class."
    type: str
    required: true
    choices:
      - "emergency"
      - "alert"
      - "critical"
      - "error"
      - "warning"
      - "notice"
      - "information"
      - "debug"
  state:
    description:
      - "Only present is supported."
    type: str
    default: "present"
    choices:
      - "present"
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

"""

EXAMPLES = r"""
- name: Set the default log to error
  gr.idg.domain_log_level:
    domain: pagos
    log_target: default-log
    log_level: error

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
log_events:
  description:
    - "Log events written, or the events that already matched."
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
            "log_target": {
                "type": "str",
                "default": 'default-log',
            },
            "log_level": {
                "type": "str",
                "required": True,
                "choices": ['emergency', 'alert', 'critical', 'error', 'warning', 'notice', 'information', 'debug'],
            },
            "state": {
                "type": "str",
                "default": 'present',
                "choices": ['present'],
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.set_log_level(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
