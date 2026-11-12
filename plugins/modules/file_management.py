#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: file_management
short_description: "Manage one filestore object"
description:
  - "Creates a directory, copies, moves, shows or deletes one filestore object."
  - "Does not confirm the write with a second GET."
  - "A matching copy or an existing directory returns changed false."
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
  state:
    description:
      - "directory, copy, move, show or absent."
    type: str
    required: true
    choices:
      - "absent"
      - "directory"
      - "move"
      - "show"
      - "copy"
  target:
    description:
      - "Destination filestore URL."
    type: str
    required: true
  source:
    description:
      - "Source filestore URL for copy and move."
    type: str
  overwrite:
    description:
      - "Overwrite the destination on copy or move."
    type: bool
    default: false
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
  - "cert: and sharedcert: are not written."
  - "sharedcert: is read from the default domain."
  - "Save the domain in a separate task when the change must persist."
seealso:
  - module: gr.idg.file_upload
    description: "Upload a file from the controller."

"""

EXAMPLES = r"""
- name: Create a directory
  gr.idg.file_management:
    domain: pagos
    state: directory
    target: local:///xsl

- name: Show a file
  gr.idg.file_management:
    domain: pagos
    state: show
    target: local:///xsl/transform.xsl

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
content:
  description:
    - "Cleaned filestore document. Key and certificate content is redacted."
  returned: when state is show
  type: dict
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
            "state": {
                "type": "str",
                "required": True,
                "choices": ['absent', 'directory', 'move', 'show', 'copy'],
            },
            "target": {
                "type": "str",
                "required": True,
            },
            "source": {
                "type": "str",
            },
            "overwrite": {
                "type": "bool",
                "default": False,
            },
        },
        supports_check_mode=True,
        required_if=[['state', 'move', ['source']], ['state', 'copy', ['source']]],
    )

    def work():
        client = connect(module)
        return ops.manage_files(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
