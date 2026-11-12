#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: file_upload
short_description: "Upload one file to the filestore"
description:
  - "Uploads one local file when its content differs from the appliance."
  - "Does not upload when the content already matches, so a second run returns changed false."
  - "Does not write cert: or sharedcert:."
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
  source:
    description:
      - "Local file path on the controller."
    type: str
    required: true
  target:
    description:
      - "Filestore URL, such as local:///xsl/transform.xsl."
    type: str
    required: true
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
  - "This task does not save the domain and does not read the file back."
seealso:
  - module: gr.idg.file_management
    description: "Copy, move, show or delete a filestore object."

"""

EXAMPLES = r"""
- name: Upload a stylesheet
  gr.idg.file_upload:
    domain: pagos
    source: files/transform.xsl
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
            "source": {
                "type": "str",
                "required": True,
            },
            "target": {
                "type": "str",
                "required": True,
            },
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        return ops.upload_file(client, module.params, module.check_mode)

    guard(module, work)


if __name__ == "__main__":
    main()
