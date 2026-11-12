#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: domain_config
short_description: "Save, export or import a domain"
description:
  - "Posts one of exported, imported or saved."
  - "Does not restart the domain. Restart is gr.idg.domain state restarted."
  - "saved calls SaveConfig only when SaveNeeded is not off, so a second run returns changed false."
  - "exported and imported run every time and return action_id without waiting."
version_added: "1.0.0"
author:
  - "David Grau Merconchini (@dgraum)"
extends_documentation_fragment:
  - gr.idg.connection
options:
  domain:
    description:
      - "Application domain."
    type: str
    required: true
    aliases:
      - "name"
  state:
    description:
      - "exported, imported or saved."
    type: str
    required: true
    choices:
      - "exported"
      - "imported"
      - "saved"
  user_summary:
    description:
      - "Comment stored with an export."
    type: str
  all_files:
    description:
      - "Include all local: files in an export."
    type: bool
    default: false
  persisted:
    description:
      - "Export the persisted configuration."
    type: bool
    default: false
  internal_files:
    description:
      - "Include internal files in an export."
    type: bool
    default: true
  zip_file:
    description:
      - "Base64 ZIP to import."
    type: str
  overwrite_files:
    description:
      - "Overwrite files during import."
    type: bool
    default: false
  overwrite_objects:
    description:
      - "Overwrite objects during import."
    type: bool
    default: false
  dry_run:
    description:
      - "Validate the import without applying it."
    type: bool
    default: false
  rewrite_local_ip:
    description:
      - "Rewrite local IP bindings during import."
    type: bool
    default: false
attributes:
  check_mode:
    description:
      - Check mode behavior for this module.
    support: partial
    details:
      - saved compares SaveNeeded. export and import are reported and are not sent.
  diff_mode:
    description:
      - Diff support for this module.
    support: partial
notes:
  - "Restart was removed from this module. Use gr.idg.domain state restarted."
  - "Wait for export or import with gr.idg.action_queue."
  - "An export package is confidential."
seealso:
  - module: gr.idg.domain
    description: "Restart the domain."
  - module: gr.idg.action_queue
    description: "Wait for an accepted action."

"""

EXAMPLES = r"""
- name: Save the domain
  gr.idg.domain_config:
    domain: pagos
    state: saved

- name: Export the domain
  gr.idg.domain_config:
    domain: pagos
    state: exported
  register: exported

- name: Wait for the export
  gr.idg.action_queue:
    domain: pagos
    action_id: "{{ exported.action_id }}"
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
            "domain": {
                "type": "str",
                "required": True,
                "aliases": ['name'],
            },
            "state": {
                "type": "str",
                "required": True,
                "choices": ['exported', 'imported', 'saved'],
            },
            "user_summary": {
                "type": "str",
            },
            "all_files": {
                "type": "bool",
                "default": False,
            },
            "persisted": {
                "type": "bool",
                "default": False,
            },
            "internal_files": {
                "type": "bool",
                "default": True,
            },
            "zip_file": {
                "type": "str",
                "no_log": True,
            },
            "overwrite_files": {
                "type": "bool",
                "default": False,
            },
            "overwrite_objects": {
                "type": "bool",
                "default": False,
            },
            "dry_run": {
                "type": "bool",
                "default": False,
            },
            "rewrite_local_ip": {
                "type": "bool",
                "default": False,
            },
        },
        supports_check_mode=True,
        required_if=[['state', 'imported', ['zip_file']]],
    )

    def work():
        client = connect(module)
        return ops.manage_domain_config(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
