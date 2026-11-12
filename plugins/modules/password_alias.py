#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: password_alias
short_description: "Manage a password alias"
description:
  - "Creates, updates or deletes one PasswordAlias."
  - "The password is not returned by a GET. When the task supplies a password, the alias is written and changed is true."
  - "Other fields are compared. A matching alias without a new password returns changed false."
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
    required: true
  name:
    description:
      - "Password alias name."
    type: str
    required: true
  state:
    description:
      - "present or absent."
    type: str
    default: "present"
    choices:
      - "present"
      - "absent"
  password:
    description:
      - "Password to store. A supplied password is always written."
    type: str
  admin_state:
    description:
      - "Administrative state."
    type: str
    default: "enabled"
    choices:
      - "enabled"
      - "disabled"
  summary:
    description:
      - "Comment stored on the alias."
    type: str
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
  - "Save with gr.idg.domain_config state saved. The password is masked."
seealso:
  - module: gr.idg.crypto_key
    description: "Use the alias on a crypto key."
  - module: gr.idg.crypto_certificate
    description: "Use the alias on a crypto certificate."

"""

EXAMPLES = r"""
- name: Ensure a password alias
  gr.idg.password_alias:
    domain: pagos
    name: portal
    password: "{{ vault_idg_password }}"
    state: present

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
                "choices": ['present', 'absent'],
            },
            "password": {
                "type": "str",
                "no_log": True,
            },
            "admin_state": {
                "type": "str",
                "default": 'enabled',
                "choices": ['enabled', 'disabled'],
            },
            "summary": {
                "type": "str",
            },
        },
        supports_check_mode=True,
        required_if=[['state', 'present', ['password']]],
    )

    def work():
        client = connect(module)
        return ops.ensure_password_alias(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
