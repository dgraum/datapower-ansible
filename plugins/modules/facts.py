#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: facts
short_description: "Read DataPower appliance identity"
description:
  - "Reads firmware, license features, the crypto engine and system settings."
  - "Does not change configuration."
  - "ansible_facts.datapower receives firmware, model and serial only."
version_added: "1.0.0"
author:
  - "David Grau Merconchini (@dgraum)"
extends_documentation_fragment:
  - gr.idg.connection
options:
  raw:
    description:
      - "When true, include the cleaned appliance payload."
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
    support: none
notes:
  - "This task only reads."
  - "ansible_facts.datapower does not include license material or the raw payload."
seealso:
  - module: gr.idg.domain
    description: "Create or change an application domain."

"""

EXAMPLES = r"""
- name: Read appliance identity
  gr.idg.facts:
    raw: false

"""

RETURN = r"""
changed:
  description:
    - "Whether this task changed the appliance."
  returned: always
  type: bool
info:
  description:
    - "Stable record for this read."
  returned: success
  type: dict
ansible_facts:
  description:
    - "Sets datapower.firmware, datapower.model and datapower.serial."
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.gr.idg.plugins.module_utils import ops
from ansible_collections.gr.idg.plugins.module_utils.runner import connect, guard


def main():
    module = AnsibleModule(
        argument_spec={
            "raw": {
                "type": "bool",
                "default": False,
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.gather_facts(client, module.params['raw'])

    guard(module, work)


if __name__ == "__main__":
    main()
