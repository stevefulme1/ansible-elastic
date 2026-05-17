#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""elastic_slm_policy module."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: elastic_slm_policy
short_description: Manage Elasticsearch SLM policies
description:
    - Manage Elasticsearch SLM policies.
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
    policy_name:
        description: Unique identifier.
        type: str
    name:
        description: Display name.
        type: str
    username:
        description: Authentication username.
        type: str
    password:
        description: Authentication password.
        type: str
    api_key:
        description: API key for authentication.
        type: str
    validate_certs:
        description: Validate SSL certificates.
        type: bool
        default: true
"""

EXAMPLES = r"""
- name: Create
  stevefulme1.elastic.elastic_slm_policy:
    host: api.example.com
    name: my-resource
    state: present

- name: Delete
  stevefulme1.elastic.elastic_slm_policy:
    host: api.example.com
    policy_name: "example-id"
    state: absent
"""

RETURN = r"""
slm_policy:
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
        required_if=[("state", "absent", ("policy_name",))],
    )

    if not HAS_CLIENT:
        module.fail_json(msg="Required Python libraries not found.")

    client = ApiClient(module)
    state = module.params["state"]
    resource_id = module.params.get("policy_name")

    if state == "present":
        existing = None
        if resource_id:
            existing = client.get("slm_policy", resource_id)
        elif module.params.get("name"):
            candidates = client.list("slm_policy", {{"name": module.params["name"]}})
            if candidates:
                existing = candidates[0]

        if existing:
            if module.check_mode:
                module.exit_json(changed=False, slm_policy=existing)
            result = client.update("slm_policy", resource_id or existing.get("id", ""), module.params)
            module.exit_json(changed=True, slm_policy=result)
        else:
            if module.check_mode:
                module.exit_json(changed=True)
            result = client.create("slm_policy", module.params)
            module.exit_json(changed=True, slm_policy=result)
    else:
        existing = None
        if resource_id:
            existing = client.get("slm_policy", resource_id)
        if not existing:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        client.delete("slm_policy", resource_id)
        module.exit_json(changed=True)


if __name__ == "__main__":
    main()
