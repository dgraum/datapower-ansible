#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: domain
short_description: "Create or change an application domain"
description:
  - "Creates, updates, deletes, restarts or changes the quiesce state of one domain."
  - "Does not save the domain."
  - "A second run with the same desired configuration returns changed false."
version_added: "1.0.0"
author:
  - "David Grau Merconchini (@dgraum)"
extends_documentation_fragment:
  - gr.idg.connection
options:
  name:
    description:
      - "Domain object name."
    type: str
    required: true
  state:
    description:
      - "Desired state. restarted and quiesce actions do not save."
    type: str
    default: "present"
    choices:
      - "present"
      - "absent"
      - "restarted"
      - "quiesced"
      - "unquiesced"
  user_summary:
    description:
      - "Domain description."
    type: str
  admin_state:
    description:
      - "Administrative state."
    type: str
    default: "enabled"
    choices:
      - "enabled"
      - "disabled"
  quiesce_conf:
    description:
      - "Quiesce delay and timeout."
    type: dict
    default: {"delay": 0, "timeout": 60}
    suboptions:
      delay:
        description:
          - "Seconds to wait before quiesce."
        type: int
        default: 0
      timeout:
        description:
          - "Seconds to wait for transactions to finish."
        type: int
        default: 60
  file_map:
    description:
      - "local: file permissions."
    type: dict
    default: {"display": true, "exec": true, "copyfrom": true, "copyto": true, "delete": true, "subdir": true}
    suboptions:
      display:
        description:
          - "Files in local: can be displayed."
        type: bool
        default: true
      exec:
        description:
          - "Files in local: can be executed."
        type: bool
        default: true
      copyfrom:
        description:
          - "Files can be copied from local:."
        type: bool
        default: true
      copyto:
        description:
          - "Files can be copied to local:."
        type: bool
        default: true
      delete:
        description:
          - "Files can be deleted from local:."
        type: bool
        default: true
      subdir:
        description:
          - "Subdirectories can be created in local:."
        type: bool
        default: true
  monitoring_map:
    description:
      - "Events for local: file changes."
    type: dict
    default: {"audit": false, "log": false}
    suboptions:
      audit:
        description:
          - "Generate audit events for local: changes."
        type: bool
        default: false
      log:
        description:
          - "Generate log events for local: changes."
        type: bool
        default: false
  max_chkpoints:
    description:
      - "Maximum configuration checkpoints."
    type: int
    default: 3
  visible:
    description:
      - "Application domains visible to this domain."
    type: list
    default: ["default"]
    elements: str
  config_mode:
    description:
      - "Configuration mode."
    type: str
    default: "local"
  config_permissions_mode:
    description:
      - "Configuration permissions mode."
    type: str
    default: "scope-domain"
  import_format:
    description:
      - "Import format."
    type: str
    default: "ZIP"
  local_ip_rewrite:
    description:
      - "Rewrite local IP bindings on import."
    type: bool
    default: true
attributes:
  check_mode:
    description:
      - Check mode behavior for this module.
    support: partial
    details:
      - present, absent and quiesce compare without writing. restarted is reported and is not sent.
  diff_mode:
    description:
      - Diff support for this module.
    support: full
notes:
  - "Save the domain with gr.idg.domain_config state saved."
  - "Restart and quiesce return action_id and do not wait."
  - "name is the domain object. It is not the module_defaults domain option."
seealso:
  - module: gr.idg.domain_config
    description: "Save, export or import the domain."
  - module: gr.idg.action_queue
    description: "Wait for an accepted action."

"""

EXAMPLES = r"""
- name: Create a domain
  gr.idg.domain:
    name: pagos
    state: present
    user_summary: Payments domain

- name: Read nothing more
  gr.idg.domain:
    name: pagos
    state: absent

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
            "name": {
                "type": "str",
                "required": True,
            },
            "state": {
                "type": "str",
                "default": 'present',
                "choices": ['present', 'absent', 'restarted', 'quiesced', 'unquiesced'],
            },
            "user_summary": {
                "type": "str",
            },
            "admin_state": {
                "type": "str",
                "default": 'enabled',
                "choices": ['enabled', 'disabled'],
            },
            "quiesce_conf": {
                "type": "dict",
                "default": {'delay': 0, 'timeout': 60},
                "options": {
                    "delay": {
                        "type": "int",
                        "default": 0,
                    },
                    "timeout": {
                        "type": "int",
                        "default": 60,
                    },
                },
            },
            "file_map": {
                "type": "dict",
                "default": {'display': True, 'exec': True, 'copyfrom': True, 'copyto': True, 'delete': True, 'subdir': True},
                "options": {
                    "display": {
                        "type": "bool",
                        "default": True,
                    },
                    "exec": {
                        "type": "bool",
                        "default": True,
                    },
                    "copyfrom": {
                        "type": "bool",
                        "default": True,
                    },
                    "copyto": {
                        "type": "bool",
                        "default": True,
                    },
                    "delete": {
                        "type": "bool",
                        "default": True,
                    },
                    "subdir": {
                        "type": "bool",
                        "default": True,
                    },
                },
            },
            "monitoring_map": {
                "type": "dict",
                "default": {'audit': False, 'log': False},
                "options": {
                    "audit": {
                        "type": "bool",
                        "default": False,
                    },
                    "log": {
                        "type": "bool",
                        "default": False,
                    },
                },
            },
            "max_chkpoints": {
                "type": "int",
                "default": 3,
            },
            "visible": {
                "type": "list",
                "default": ['default'],
                "elements": "str",
            },
            "config_mode": {
                "type": "str",
                "default": 'local',
            },
            "config_permissions_mode": {
                "type": "str",
                "default": 'scope-domain',
            },
            "import_format": {
                "type": "str",
                "default": 'ZIP',
            },
            "local_ip_rewrite": {
                "type": "bool",
                "default": True,
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.manage_domain(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
