#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)

"""Ansible module: kibana_space."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_space
short_description: Manage Kibana spaces for multi-tenancy
description:
    - Manage Kibana spaces for multi-tenancy in Elastic.
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
    space_id:
        description: Unique identifier of the space.
        type: str
    name:
        description: Display name of the space.
        type: str
"""

EXAMPLES = r"""
- name: Create a space
  stevefulme1.elastic.kibana_space:
    name: my-space
    state: present

- name: Delete a space
  stevefulme1.elastic.kibana_space:
    space_id: "example-id"
    state: absent
"""

RETURN = r"""
space:
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
            space_id=dict(type="str"),
            name=dict(type="str"),
            host=dict(type="str", required=True),
            username=dict(type="str"),
            password=dict(type="str", no_log=True),
            api_key=dict(type="str", no_log=True),
            validate_certs=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
        required_if=[
            ("state", "absent", ("space_id",)),
        ],
    )

    if not HAS_CLIENT:
        module.fail_json(msg="Required Python libraries not found.")

    client = ApiClient(module)
    state = module.params["state"]
    resource_id = module.params.get("space_id")

    if state == "present":
        if resource_id:
            result = client.update("space", resource_id, module.params)
        else:
            if module.check_mode:
                module.exit_json(changed=True)
            result = client.create("space", module.params)
        module.exit_json(changed=True, space=result)
    else:
        if module.check_mode:
            module.exit_json(changed=True)
        client.delete("space", resource_id)
        module.exit_json(changed=True)


if __name__ == "__main__":
    main()
