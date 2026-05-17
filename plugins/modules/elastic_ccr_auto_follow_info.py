#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""elastic_ccr_auto_follow_info module."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: elastic_ccr_auto_follow_info
short_description: Retrieve CCR auto-follow pattern information
description:
    - Retrieve details about Elasticsearch CCR auto-follow patterns.
    - Read-only module.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    host:
        description: API host address.
        type: str
        required: true
    pattern_name:
        description: ID of a specific resource.
        type: str
    name:
        description: Filter by name.
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
- name: List all CCR auto-follow patterns
  stevefulme1.elastic.elastic_ccr_auto_follow_info:
    host: api.example.com
  register: result

- name: Get a specific CCR auto-follow pattern
  stevefulme1.elastic.elastic_ccr_auto_follow_info:
    host: api.example.com
    pattern_name: "example-id"
  register: result
"""

RETURN = r"""
ccr_auto_follows:
    description: List of resource details.
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
            pattern_name=dict(type="str"),
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
    resource_id = module.params.get("pattern_name")

    if resource_id:
        result = client.get("ccr_auto_follow", resource_id)
        resources = [result] if result else []
    else:
        resources = client.list("ccr_auto_follow", module.params)

    module.exit_json(changed=False, ccr_auto_follows=resources)


if __name__ == "__main__":
    main()
