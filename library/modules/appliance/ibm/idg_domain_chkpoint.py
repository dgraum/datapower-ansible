#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2018, [David Grau Merconchini <david@gallorojo.com.mx>]
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: idg_domain_chkpoint
short_description: Manages IBM DataPower Gateway(IDG) domains configuration checkpoints.
description:
  - Manages IBM DataPower Gateway(IDG) domains configuration checkpoints.
version_added: "2.7"
options:

  name:
    description:
      - Checkpoint identifier.
    required: True

  domain:
    description:
      - Domain identifier.
    required: True

  state:
    description:
      - Specifies the current state of the checkpoint inside the domain.
      - C(present), C(absent). Create or remove a checkpoint.
      - C(restored) return the domain configuration at the time that the checkpoint was created.
    default: present
    required: False
    choices:
      - present
      - absent
      - restored

extends_documentation_fragment: idg

author:
  - David Grau Merconchini (@dgraum)
'''

EXAMPLES = '''
- name: Test DataPower checkpoint module
  connection: local
  hosts: localhost
  vars:
    domain_name: test
    chkpoint_name: checkpoint1
    remote_idg:
        server: idghost
        server_port: 5554
        user: admin
        password: admin
        validate_certs: false
        timeout: 15

  tasks:

  - name: Create checkpoint
    idg_domain_chkpoint:
        name: "{{ chkpoint_name }}"
        domain: "{{ domain_name }}"
        idg_connection: "{{ remote_idg }}"
        state: present

  # Uncontrollable modifications

  - name: Restore from checkpoint
    idg_domain_chkpoint:
        name: "{{ chkpoint_name }}"
        domain: "{{ domain_name }}"
        idg_connection: "{{ remote_idg }}"
        state: restored

'''

RETURN = '''
domain:
  description:
    - The name of the domain.
  returned: changed and success
  type: string
  sample:
    - core-security-wrap
    - DevWSOrchestration

name:
  description:
    - The name of the checkpoint that is being worked on.
  returned: changed and success
  type: string
  sample:
    - checkpoint1

msg:
  description:
    - Message returned by the device API.
  returned: always
  type: string
  sample:
    - Configuration was created.
    - Unknown error for (https://idg-host1:5554/mgmt/domains/config/). <open_url error timed out>
'''

import json
import yaml
# import pdb

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

# Common package of our implementation for IDG
try:
    from ansible.module_utils.appliance.ibm.idg_common import result, idg_endpoint_spec, IDGUtils
    from ansible.module_utils.appliance.ibm.idg_rest_mgmt import IDGApi, ErrorHandler
    HAS_IDG_DEPS = True
except ImportError:
    HAS_IDG_DEPS = False

# Version control
__MODULE_NAME = yaml.load(DOCUMENTATION)['module']
__MODULE_VERSION = "1.0"
__MODULE_FULLNAME = __MODULE_NAME + '-' + __MODULE_VERSION


def main():

    try:
        # Arguments/parameters that a user can pass to the module
        module_args = dict(
            state=dict(type='str', choices=['present', 'absent', 'restored'], default='present'),  # Checkpoint state
            idg_connection=dict(type='dict', options=idg_endpoint_spec, required=True),  # IDG connection
            domain=dict(type='str', required=True),  # Domain
            name=dict(type='str', required=True)  # Checkpoint
        )

        # AnsibleModule instantiation
        module = AnsibleModule(
            argument_spec=module_args,
            supports_check_mode=True
        )

        # Validates the dependence of the utility module
        if not HAS_IDG_DEPS:
            module.fail_json(msg="The IDG utils modules is required")

        # Parse arguments to dict
        idg_data_spec = IDGUtils.parse_to_dict(module, module.params['idg_connection'], 'IDGConnection', IDGUtils.ANSIBLE_VERSION)

        # Status & domain
        state = module.params['state']
        domain_name = module.params['domain']
        chkpoint_name = module.params['name']

        # Init IDG API connect
        idg_mgmt = IDGApi(ansible_module=module,
                          idg_host="https://{0}:{1}".format(idg_data_spec['server'], idg_data_spec['server_port']),
                          headers=IDGUtils.BASIC_HEADERS,
                          http_agent=IDGUtils.HTTP_AGENT_SPEC,
                          use_proxy=idg_data_spec['use_proxy'],
                          timeout=idg_data_spec['timeout'],
                          validate_certs=idg_data_spec['validate_certs'],
                          user=idg_data_spec['user'],
                          password=idg_data_spec['password'],
                          force_basic_auth=IDGUtils.BASIC_AUTH_SPEC)

        # Action messages:
        # Save checkpoint
        save_act_msg = {"SaveCheckpoint": {"ChkName": chkpoint_name}}

        # Rollback checkpoint
        rollback_act_msg = {"RollbackCheckpoint": {"ChkName": chkpoint_name}}

        # Remove checkpoint
        remove_act_msg = {"RemoveCheckpoint": {"ChkName": chkpoint_name}}

        #
        # Here the action begins
        #

        # Variable to store the status of the action
        action_result = ''

        # Intermediate values ​​for result
        tmp_result={"name": chkpoint_name, "domain": domain_name, "msg": None, "changed": None, "failed": None}

        # List of configured domains
        chk_code, chk_msg, chk_data = idg_mgmt.api_call(IDGApi.URI_DOMAIN_LIST, method='GET')

        if chk_code == 200 and chk_msg == 'OK':  # If the answer is correct

            if isinstance(chk_data['domain'], dict):  # if has only default domain
                configured_domains = [chk_data['domain']['name']]
            else:
                configured_domains = [d['name'] for d in chk_data['domain']]

            if domain_name in configured_domains:  # Domain EXIST.

                # pdb.set_trace()
                if state == 'present':

                    # If the user is working in only check mode we do not want to make any changes
                    IDGUtils.implement_check_mode(module, result)

                    # pdb.set_trace()
                    create_code, create_msg, create_data = idg_mgmt.api_call(IDGApi.URI_ACTION.format(domain_name), method='POST',
                                                                             data=json.dumps(save_act_msg))

                    if create_code == 202 and create_msg == 'Accepted':
                        # Asynchronous actions save accepted. Wait for complete
                        action_result = idg_mgmt.wait_for_action_end(IDGApi.URI_ACTION.format(domain_name), href=create_data['_links']['location']['href'],
                                                                     state=state)

                        # Create checkpoint completed. Get result
                        dcr_code, dcr_msg, dcr_data = idg_mgmt.api_call(create_data['_links']['location']['href'], method='GET')

                        if dcr_code == 200 and dcr_msg == 'OK':

                            if dcr_data['status'] == 'error':
                                # pdb.set_trace()
                                tmp_result['changed'] = False
                                if ("Configuration Checkpoint '" + chkpoint_name + "' already exists.") in dcr_data['error']:
                                    tmp_result['msg'] = IDGUtils.IMMUTABLE_MESSAGE
                                else:
                                    tmp_result['msg'] = IDGApi.GENERAL_ERROR.format(__MODULE_FULLNAME, state, domain_name) + str(ErrorHandler(dcr_data['error']))
                                    tmp_result['failed'] = True
                            else:
                                tmp_result['msg'] = dcr_data['status'].capitalize()
                                tmp_result['changed'] = True
                        else:
                            # Can't retrieve the create checkpoint result
                            module.fail_json(msg=IDGApi.ERROR_RETRIEVING_RESULT.format(state, domain_name))

                    elif create_code == 200 and create_msg == 'OK':
                        # Successfully processed synchronized action
                        tmp_result['msg'] = idg_mgmt.status_text(create_data['SaveCheckpoint'])
                        tmp_result['changed'] = True

                    else:
                        # Create checkpoint not accepted
                        module.fail_json(msg=IDGApi.ERROR_ACCEPTING_ACTION.format(state, domain_name))

                elif state == 'absent':

                    # If the user is working in only check mode we do not want to make any changes
                    IDGUtils.implement_check_mode(module, result)

                    # pdb.set_trace()
                    rm_code, rm_msg, rm_data = idg_mgmt.api_call(IDGApi.URI_ACTION.format(domain_name), method='POST',
                                                                 data=json.dumps(remove_act_msg))

                    if rm_code == 202 and rm_msg == 'Accepted':
                        # Asynchronous actions remove accepted. Wait for complete
                        action_result = idg_mgmt.wait_for_action_end(IDGApi.URI_ACTION.format(domain_name), href=rm_data['_links']['location']['href'],
                                                                     state=state)

                        # Remove checkpoint completed. Get result
                        drm_code, drm_msg, drm_data = idg_mgmt.api_call(rm_data['_links']['location']['href'], method='GET')

                        if drm_code == 200 and drm_msg == 'OK':

                            if drm_data['status'] == 'error':
                                # pdb.set_trace()
                                tmp_result['msg'] = IDGApi.GENERAL_ERROR.format(__MODULE_FULLNAME, state, domain_name) + str(ErrorHandler(drm_data['error']))
                                tmp_result['changed'] = False
                                tmp_result['failed'] = True
                            else:
                                tmp_result['msg'] = drm_data['status'].capitalize()
                                tmp_result['changed'] = True
                        else:
                            # Can't retrieve the create checkpoint result
                            module.fail_json(msg=IDGApi.ERROR_RETRIEVING_RESULT.format(state, domain_name))

                    elif rm_code == 200 and rm_msg == 'OK':
                        # Successfully processed synchronized action
                        tmp_result['msg'] = idg_mgmt.status_text(rm_data['RemoveCheckpoint'])
                        tmp_result['changed'] = True

                    elif rm_code == 400 and rm_msg == 'Bad Request':
                        # Wrong request, maybe there simply is no checkpoint
                        if ("Cannot find Configuration Checkpoint '" + chkpoint_name + "'.") in rm_data['error']:
                            tmp_result['msg'] = IDGUtils.IMMUTABLE_MESSAGE
                        else:
                            tmp_result['msg'] = IDGApi.GENERAL_ERROR.format(__MODULE_FULLNAME, state, domain_name) + str(ErrorHandler(rm_data['error']))
                            tmp_result['failed'] = True

                    else:
                        # Create checkpoint not accepted
                        module.fail_json(msg=IDGApi.ERROR_ACCEPTING_ACTION.format(state, domain_name))

                elif state == 'restored':

                    # If the user is working in only check mode we do not want to make any changes
                    IDGUtils.implement_check_mode(module, result)

                    # pdb.set_trace()
                    bak_code, bak_msg, bak_data = idg_mgmt.api_call(IDGApi.URI_ACTION.format(domain_name), method='POST',
                                                                    data=json.dumps(rollback_act_msg))

                    if bak_code == 202 and bak_msg == 'Accepted':
                        # Asynchronous actions remove accepted. Wait for complete
                        action_result = idg_mgmt.wait_for_action_end(IDGApi.URI_ACTION.format(domain_name), href=bak_data['_links']['location']['href'],
                                                                     state=state)

                        # Remove checkpoint completed. Get result
                        dbak_code, dbak_msg, dbak_data = idg_mgmt.api_call(bak_data['_links']['location']['href'], method='GET')

                        if dbak_code == 200 and dbak_msg == 'OK':

                            if dbak_data['status'] == 'error':
                                # pdb.set_trace()
                                tmp_result['msg'] = IDGApi.GENERAL_ERROR.format(__MODULE_FULLNAME, state, domain_name) + str(ErrorHandler(dbak_data['error']))
                                tmp_result['changed'] = False
                                tmp_result['failed'] = True
                            else:
                                tmp_result['msg'] = dbak_data['status'].capitalize()
                                tmp_result['changed'] = True
                        else:
                            # Can't retrieve the create checkpoint result
                            module.fail_json(msg=IDGApi.ERROR_RETRIEVING_RESULT.format(state, domain_name))

                    elif bak_code == 200 and bak_msg == 'OK':
                        # Successfully processed synchronized action
                        tmp_result['msg'] = idg_mgmt.status_text(bak_data['RollbackCheckpoint'])
                        tmp_result['changed'] = True

                    else:
                        # Create checkpoint not accepted
                        module.fail_json(msg=IDGApi.ERROR_ACCEPTING_ACTION.format(state, domain_name))

            else:  # Domain NOT EXIST.
                # Can't work the configuration of non-existent domain
                module.fail_json(msg=(IDGApi.ERROR_REACH_STATE + " " + IDGApi.ERROR_NOT_DOMAIN).format(state, domain_name))

        else:  # Can't read domain's lists
            module.fail_json(msg=IDGApi.ERROR_GET_DOMAIN_LIST)

        #
        # Finish
        #
        # Update
        for k, v in tmp_result.items():
            if v != None:
                result[k] = v

    except (NameError, UnboundLocalError) as e:
        # Very early error
        module_except = AnsibleModule(argument_spec={})
        module_except.fail_json(msg=to_native(e))

    except Exception as e:
        # Uncontrolled exception
        module.fail_json(msg=(IDGUtils.UNCONTROLLED_EXCEPTION + '. {0}').format(to_native(e)))
    else:
        # That's all folks!
        module.exit_json(**result)


if __name__ == '__main__':
    main()
