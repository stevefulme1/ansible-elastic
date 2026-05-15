#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)

"""Ansible module: elastic_ilm_policy."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: elastic_ilm_policy
short_description: Manage Elasticsearch ILM policies
description:
    - Manage Elasticsearch ILM policies in Elastic.
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
    policy_name:
        description: Unique identifier of the ilm policy.
        type: str
    name:
        description: Display name of the ilm policy.
        type: str
"""

EXAMPLES = r"""
- name: Create a ilm policy
  stevefulme1.elastic.elastic_ilm_policy:
    name: my-ilm-policy
    state: present

- name: Delete a ilm policy
  stevefulme1.elastic.elastic_ilm_policy:
    policy_name: "example-id"
    state: absent
"""

RETURN = r"""
ilm_policy:
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
            policy_name=dict(type="str"),
            name=dict(type="str"),
            host=dict(type="str", required=True),
            username=dict(type="str"),
            password=dict(type="str", no_log=True),
            api_key=dict(type="str", no_log=True),
            validate_certs=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
        required_if=[
            ("state", "absent", ("policy_name",)),
        ],
    )

    if not HAS_CLIENT:
        module.fail_json(msg="Required Python libraries not found.")

    client = ApiClient(module)
    state = module.params["state"]
    resource_id = module.params.get("policy_name")

    if state == "present":
        if resource_id:
            result = client.update("ilm_policy", resource_id, module.params)
        else:
            if module.check_mode:
                module.exit_json(changed=True)
            result = client.create("ilm_policy", module.params)
        module.exit_json(changed=True, ilm_policy=result)
    else:
        if module.check_mode:
            module.exit_json(changed=True)
        client.delete("ilm_policy", resource_id)
        module.exit_json(changed=True)


if __name__ == "__main__":
    main()
