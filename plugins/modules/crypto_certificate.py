#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: crypto_certificate
short_description: "Manage one crypto certificate"
description:
  - "Creates, updates or deletes one CryptoCertificate."
  - "state retarget changes Filename on an existing certificate and sends the rest of the object back."
  - "state detail reads one certificate and does not write."
  - "With name, detail posts ViewCertificateDetails for that CryptoCertificate."
  - "With file_name and no name, detail reads that filestore file and reports whether it is a certificate."
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
      - "CryptoCertificate object name. Required to write. For detail, pass name or file_name."
    type: str
  state:
    description:
      - "present, absent, detail, or retarget. retarget updates an existing certificate and does not create one."
    type: str
    default: "present"
    choices:
      - "present"
      - "absent"
      - "detail"
      - "retarget"
  admin_state:
    description:
      - "Administrative state. Used for present."
    type: str
    default: "enabled"
    choices:
      - "enabled"
      - "disabled"
  file_name:
    description:
      - "Filestore path. Required for present and retarget. For detail without name, the file is read and classified."
    type: str
  ignore_expiration:
    description:
      - "Ignore certificate expiration. Used for present."
    type: bool
    default: false
  password_alias:
    description:
      - "Password alias that opens the certificate file."
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
  - "The certificate file must already be on the appliance. Save in a separate task."
  - "state retarget does not create the certificate or the file. It keeps the current alias."
  - "state detail returns subject, issuer and validity. It omits the key material."
  - "A file that is a key or an unrecognized object returns certificate false and does not write."
seealso:
  - module: gr.idg.crypto_key
    description: "Manage the key that matches this certificate."
  - module: gr.idg.password_alias
    description: "Manage a password alias."
  - module: gr.idg.config
    description: "List CryptoCertificate objects in the domain."

"""

EXAMPLES = r"""
- name: Ensure a crypto certificate
  gr.idg.crypto_certificate:
    domain: pagos
    name: portal-cert
    file_name: cert:///portal.pem
    state: present

- name: Read the certificate detail
  gr.idg.crypto_certificate:
    domain: pagos
    name: portal-cert
    state: detail

- name: Read a certificate file without writing
  gr.idg.crypto_certificate:
    domain: pagos
    file_name: cert:///portal.pem
    state: detail

- name: Point an existing certificate at a new file
  gr.idg.crypto_certificate:
    domain: pagos
    name: portal-cert
    file_name: cert:///portal-2026.pem
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
  returned: when diff is enabled and state writes
  type: dict
config:
  description:
    - "Object that was written, without secret values."
  returned: when the object is written
  type: dict
detail:
  description:
    - "Certificate subject, issuer, validity and extensions. Key material is omitted."
  returned: when state is detail and the target is a certificate
  type: dict
certificate:
  description:
    - "Whether a filestore file is a certificate."
  returned: when state is detail and file_name is used
  type: bool
kind:
  description:
    - "certificate, key or unknown."
  returned: when state is detail and file_name is used
  type: str
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
            },
            "state": {
                "type": "str",
                "default": "present",
                "choices": ["present", "absent", "detail", "retarget"],
            },
            "admin_state": {
                "type": "str",
                "default": "enabled",
                "choices": ["enabled", "disabled"],
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
        required_if=[
            ["state", "present", ["file_name"]],
            ["state", "retarget", ["name", "file_name"]],
        ],
    )

    def work():
        state = module.params["state"]
        if state == "detail":
            if not module.params.get("name") and not module.params.get("file_name"):
                module.fail_json(msg="name or file_name is required.")
        elif not module.params.get("name"):
            module.fail_json(msg="name is required.")
        client = connect(module)
        return ops.ensure_crypto_certificate(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
