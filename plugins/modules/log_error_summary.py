#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: log_error_summary
short_description: "Read the error log summary"
description:
  - "Reads the error summary for one domain."
  - "Does not change configuration."
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
  bottom_ts:
    description:
      - "Lower timestamp bound. Epoch 0 reads the available window."
    type: int
    default: 0
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
  - "This task only reads. It does not fetch the log file itself."
seealso:
  - module: gr.idg.file_management
    description: "Read a file such as logtemp:///default-log."

"""

EXAMPLES = r"""
- name: Read the error summary
  gr.idg.log_error_summary:
    domain: pagos
    bottom_ts: 0

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
summary:
  description:
    - "Cleaned error summary document."
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
                "required": True,
            },
            "bottom_ts": {
                "type": "int",
                "default": 0,
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.fetch_log_summary(client, module.params)

    guard(module, work)


if __name__ == "__main__":
    main()
