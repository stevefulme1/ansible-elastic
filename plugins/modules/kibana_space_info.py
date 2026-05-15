#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)

"""Ansible module: kibana_space_info."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_space_info
short_description: Retrieve space information
description:
    - Retrieve details about spaces.
    - This is a read-only module.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    space_id:
        description: ID of a specific space to retrieve.
        type: str
    name:
        description: Filter by name.
        type: str
"""

EXAMPLES = r"""
- name: List all spaces
  stevefulme1.elastic.kibana_space_info:
  register: result

- name: Get a specific space
  stevefulme1.elastic.kibana_space_info:
    space_id: "example-id"
  register: result
"""

RETURN = r"""
spaces:
    description: List of space details.
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
            space_id=dict(type="str"),
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
    resource_id = module.params.get("space_id")

    if resource_id:
        result = client.get("space", resource_id)
        resources = [result] if result else []
    else:
        resources = client.list("space", module.params)

    module.exit_json(changed=False, spaces=resources)


if __name__ == "__main__":
    main()
