#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module: elastic_ilm_policy_info."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: elastic_ilm_policy_info
short_description: Retrieve ilm policy information
description:
    - Retrieve details about ilm policys.
    - This is a read-only module.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    host:
        description: API host address.
        type: str
        required: true
    username:
        description: Authentication username.
        type: str
    password:
        description: Authentication password.
        type: str
        no_log: true
    api_key:
        description: API key for authentication.
        type: str
        no_log: true
    validate_certs:
        description: Whether to validate SSL certificates.
        type: bool
        default: true
"""

EXAMPLES = r"""
- name: List all ilm policys
  stevefulme1.elastic.elastic_ilm_policy_info:
  register: result

- name: Get a specific ilm policy
  stevefulme1.elastic.elastic_ilm_policy_info:
    policy_name: "example-id"
  register: result
"""

RETURN = r"""
ilm_policys:
    description: List of ilm policy details.
    returned: always
    type: list
    elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ApiClient
    HAS_CLIENT = True
except ImportError:
    HAS_CLIENT = False


def main():
    module = AnsibleModule(
        argument_spec=dict(
            policy_name=dict(type="str"),
            name=dict(type="str"),
            host=dict(type="str", required=True),
            username=dict(type="str"),
            password=dict(type="str", no_log=True),
            api_key=dict(type="str", no_log=True),
            validate_certs=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )

    if not HAS_CLIENT:
        module.fail_json(msg="Required Python libraries not found.")

    client = ApiClient(module)
    resource_id = module.params.get("policy_name")

    if resource_id:
        result = client.get("ilm_policy", resource_id)
        resources = [result] if result else []
    else:
        resources = client.list("ilm_policy", module.params)

    module.exit_json(changed=False, ilm_policys=resources)


if __name__ == "__main__":
    main()
