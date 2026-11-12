#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: crypto_key
short_description: "Manage one crypto key"
description:
  - "Creates, updates or deletes one CryptoKey."
  - "state retarget changes Filename on an existing key and sends the rest of the object back."
  - "A key alias changes only when password_alias is passed. An empty password_alias clears it."
  - "Compares the fields DataPower returns before writing."
  - "A second run with the same fields returns changed false."
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
      - "CryptoKey object name."
    type: str
    required: true
  state:
    description:
      - "present, absent, or retarget. retarget updates an existing key and does not create one."
    type: str
    default: "present"
    choices:
      - "present"
      - "absent"
      - "retarget"
  admin_state:
    description:
      - "Administrative state."
    type: str
    default: "enabled"
    choices:
      - "enabled"
      - "disabled"
  file_name:
    description:
      - "Filestore path of the key. Required for present and retarget."
    type: str
  password_alias:
    description:
      - "Password alias that opens the key. On retarget, omit it to keep the current alias."
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
  - "The key file must already be on the appliance. Save in a separate task."
  - "state retarget does not create the key, the file, or the password alias."
seealso:
  - module: gr.idg.crypto_certificate
    description: "Manage the certificate that matches this key."
  - module: gr.idg.password_alias
    description: "Manage a password alias."

"""

EXAMPLES = r"""
- name: Ensure a crypto key
  gr.idg.crypto_key:
    domain: pagos
    name: portal-key
    file_name: cert:///portal-key.pem
    password_alias: portal
    state: present

- name: Point an existing key at a new file
  gr.idg.crypto_key:
    domain: pagos
    name: portal-key
    file_name: cert:///portal-key-2026.pem
    password_alias: portal
    state: retarget

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
config:
  description:
    - "Object that was written, without secret values."
  returned: when the object is written
  type: dict
previous:
  description:
    - "Filename and alias read before a retarget."
  returned: when state is retarget
  type: dict
file_name:
  description:
    - "Normalized filestore path requested by retarget."
  returned: when state is retarget
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
                "default": "present",
                "choices": ["present", "absent", "retarget"],
            },
            "admin_state": {
                "type": "str",
                "default": "enabled",
                "choices": ["enabled", "disabled"],
            },
            "file_name": {
                "type": "str",
            },
            "password_alias": {
                "type": "str",
                "no_log": True,
            },
        },
        supports_check_mode=True,
        required_if=[
            ["state", "present", ["file_name"]],
            ["state", "retarget", ["file_name"]],
        ],
    )

    def work():
        client = connect(module)
        return ops.ensure_crypto_key(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
