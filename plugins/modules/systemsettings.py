#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: systemsettings
short_description: "Read system settings"
description:
  - "System settings in snake_case."
  - "Does not change configuration. A second run returns changed false."
  - "Fails with the class name when SystemSettings is missing on this firmware."
version_added: "1.0.0"
author:
  - "David Grau Merconchini (@dgraum)"
extends_documentation_fragment:
  - gr.idg.connection
options:
  domain:
    description:
      - "Accepted so module_defaults can set a domain. This module reads the default domain."
    type: str
    default: "default"
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
  - "This task only reads. It does not save or restart."
  - "The domain option is ignored. The read uses the default domain."
seealso:
  - module: gr.idg.status
    description: "Read a status class that has no dedicated module."

"""

EXAMPLES = r"""
- name: Read system settings
  gr.idg.systemsettings:
    raw: false

"""

RETURN = r"""
changed:
  description:
    - "Whether this task changed the appliance."
  returned: always
  type: bool
system_settings:
  description:
    - "Stable record for this read."
  returned: success
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
                "default": 'default',
            },
            "raw": {
                "type": "bool",
                "default": False,
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.snake_status(client, 'default', 'SystemSettings', 'system_settings', module.params['raw'], area='config')

    guard(module, work)


if __name__ == "__main__":
    main()
