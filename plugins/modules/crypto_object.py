#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: crypto_object
short_description: "Manage a crypto key or certificate object"
description:
  - "Creates, updates or deletes one CryptoKey or CryptoCertificate."
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
      - "Object name."
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
  object_class:
    description:
      - "key or public-key."
    type: str
    default: "key"
    choices:
      - "key"
      - "public-key"
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
      - "Filestore path of the key or certificate."
    type: str
  ignore_expiration:
    description:
      - "Ignore certificate expiration. Used for public-key."
    type: bool
    default: false
  password_alias:
    description:
      - "Password alias that opens the key."
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
  - "New playbooks use gr.idg.crypto_key or gr.idg.crypto_certificate."
seealso:
  - module: gr.idg.crypto_key
    description: "Manage one CryptoKey."
  - module: gr.idg.crypto_certificate
    description: "Manage one CryptoCertificate, or read its detail."
  - module: gr.idg.password_alias
    description: "Manage a password alias."

"""

EXAMPLES = r"""
- name: Ensure a crypto key object
  gr.idg.crypto_object:
    domain: pagos
    name: portal-key
    object_class: key
    file_name: cert:///portal-key.pem
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
config:
  description:
    - "Object that was written, without secret values."
  returned: when the object is written
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
            "object_class": {
                "type": "str",
                "default": 'key',
                "choices": ['key', 'public-key'],
            },
            "admin_state": {
                "type": "str",
                "default": 'enabled',
                "choices": ['enabled', 'disabled'],
            },
            "file_name": {
                "type": "str",
            },
            "ignore_expiration": {
                "type": "bool",
                "default": False,
            },
            "password_alias": {
                "type": "str",
                "no_log": True,
            },
        },
        supports_check_mode=True,
        required_if=[['state', 'present', ['file_name']]],
    )

    def work():
        client = connect(module)
        return ops.ensure_crypto(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
