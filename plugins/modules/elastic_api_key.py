#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module: elastic_api_key."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: elastic_api_key
short_description: Manage Elasticsearch API keys
description:
    - Manage Elasticsearch API keys in Elastic.
    - Supports create, update, and delete operations.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    state:
        description: Desired state of the resource.
        type: str
        default: present
        choices: [present, absent]
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
- name: Create a api key
  stevefulme1.elastic.elastic_api_key:
    name: my-api-key
    state: present

- name: Delete a api key
  stevefulme1.elastic.elastic_api_key:
    key_id: "example-id"
    state: absent
"""

RETURN = r"""
api_key:
    description: Resource details.
    returned: on success
    type: dict
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
            state=dict(type="str", default="present", choices=["present", "absent"]),
            key_id=dict(type="str"),
            name=dict(type="str"),
            host=dict(type="str", required=True),
            username=dict(type="str"),
            password=dict(type="str", no_log=True),
            api_key=dict(type="str", no_log=True),
            validate_certs=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
        required_if=[
            ("state", "absent", ("key_id",)),
        ],
    )

    if not HAS_CLIENT:
        module.fail_json(msg="Required Python libraries not found.")

    client = ApiClient(module)
    state = module.params["state"]
    resource_id = module.params.get("key_id")

    if state == "present":
        if resource_id:
            result = client.update("api_key", resource_id, module.params)
        else:
            if module.check_mode:
                module.exit_json(changed=True)
            result = client.create("api_key", module.params)
        module.exit_json(changed=True, api_key=result)
    else:
        if module.check_mode:
            module.exit_json(changed=True)
        client.delete("api_key", resource_id)
        module.exit_json(changed=True)


if __name__ == "__main__":
    main()
