# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    """Inventory connection. These are not module options."""

    DOCUMENTATION = r"""
notes:
  - >-
    The play uses C(ansible.netcommon.httpapi). Set C(ansible_host),
    C(ansible_user), C(ansible_password), C(ansible_httpapi_use_ssl=true),
    C(ansible_httpapi_port=5554) and C(ansible_httpapi_validate_certs=true)
    on the host. C(ansible_network_os) is C(gr.idg.rest_mgmt).
  - >-
    Client certificates use C(ansible_httpapi_client_cert) and
    C(ansible_httpapi_client_key). The password belongs in Ansible Vault.
  - >-
    One REST call waits C(ansible_httpapi_timeout) or C(ansible_command_timeout)
    seconds. The default is 30. Raise it for export, import and long syncs.
attributes:
  platform:
    description: IBM DataPower Gateway REST management, run on the controller.
    support: full
    platforms: DataPower
"""
