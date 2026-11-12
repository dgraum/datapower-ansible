#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: service_resolve_by_endpoint
short_description: Find the service that owns a URL
description:
  - "Reads active services and configuration until it finds who owns a URL."
  - "Does not change configuration."
version_added: "1.0.0"
author:
  - "David Grau Merconchini (@dgraum)"
extends_documentation_fragment:
  - gr.idg.connection
options:
  domain:
    description:
      - "Accepted so module_defaults can set a domain. The search uses domains and skip_domains."
    type: str
    default: "default"
  target_url:
    description:
      - "URL whose front-side service should be found."
    type: str
    required: true
  skip_domains:
    description:
      - "Domains left out of the search."
    type: list
    elements: str
    default:
      - default
  domains:
    description:
      - "Domains to search. When omitted, every enabled domain is searched."
    type: list
    elements: str
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
seealso:
  - module: gr.idg.domain_active_services
    description: "List active services in one domain."
"""

EXAMPLES = r"""
- name: Find the service for a URL
  gr.idg.service_resolve_by_endpoint:
    target_url: https://payments.example.com:8443/pay
    domains:
      - pagos
"""

RETURN = r"""
changed:
  description:
    - "Whether this task changed the appliance."
  returned: always
  type: bool
parsed:
  description:
    - "Normalized target URL."
  returned: success
  type: dict
matches:
  description:
    - "Services that own the URL."
  returned: success
  type: list
  elements: dict
match_count:
  description:
    - "Number of matches."
  returned: success
  type: int
ambiguous:
  description:
    - "Whether the same socket is served by more than one domain."
  returned: success
  type: bool
socket_conflicts:
  description:
    - "Sockets claimed by more than one domain."
  returned: success
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.gr.idg.plugins.module_utils.resolve import resolve_endpoint
from ansible_collections.gr.idg.plugins.module_utils.runner import connect, guard


def main():
    module = AnsibleModule(
        argument_spec={
            "domain": {"type": "str", "default": "default"},
            "target_url": {"type": "str", "required": True},
            "skip_domains": {
                "type": "list",
                "elements": "str",
                "default": ["default"],
            },
            "domains": {"type": "list", "elements": "str"},
        },
        supports_check_mode=True,
    )

    def work():
        client = connect(module)
        parsed, matches, ambiguous, conflicts = resolve_endpoint(
            client,
            module.params["target_url"],
            module.params["skip_domains"],
            module.params["domains"],
        )
        return {
            "changed": False,
            "parsed": parsed,
            "matches": matches,
            "match_count": len(matches),
            "ambiguous": ambiguous,
            "socket_conflicts": conflicts,
        }

    guard(module, work)


if __name__ == "__main__":
    main()
