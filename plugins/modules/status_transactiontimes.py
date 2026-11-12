#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: status_transactiontimes
short_description: "Read HTTP transaction times"
description:
  - "Reads HTTPMeanTransactionTime2 and returns snake_case records."
  - "Does not change configuration."
  - "Fails with the class name when it is missing on this firmware."
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
  - "This task only reads. Saving the domain is a separate gr.idg.domain_config task."
seealso:
  - module: gr.idg.status
    description: "Read a status class that has no dedicated module."

"""

EXAMPLES = r"""
- name: Read HTTP transaction times
  gr.idg.status_transactiontimes:
    domain: pagos
    raw: false

"""

RETURN = r"""
changed:
  description:
    - "Whether this task changed the appliance."
  returned: always
  type: bool
transaction_times:
  description:
    - "Stable record for this read."
  returned: success
  type: list
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
            "raw": {
                "type": "bool",
                "default": False,
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.snake_status(client, module.params['domain'], 'HTTPMeanTransactionTime2', 'transaction_times', module.params['raw'], area='status')

    guard(module, work)


if __name__ == "__main__":
    main()
