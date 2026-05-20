#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_role_mapping_info
short_description: Retrieve information about Elasticsearch security role mappings
version_added: "1.0.0"
description:
  - Retrieve a single security role mapping by name, or list all security role mappings.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  name:
    description:
      - The name of the security role mapping to retrieve.
      - When omitted, all security role mappings are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific security role mapping
  stevefulme1.elastic.security_role_mapping_info:
    name: "my_mapping"
  register: result

- name: List all security role mappings
  stevefulme1.elastic.security_role_mapping_info:
  register: result
"""

RETURN = r"""
security_role_mappings:
  description: List of security role mapping resources matching the query.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, name):
    """Retrieve a single security role mapping by name."""
    try:
        response = client.get("/_security/role_mapping/{0}".format(name))
        if isinstance(response, dict) and name in response:
            mapping = response[name]
            mapping["name"] = name
            return mapping
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List all security role mappings."""
    response = client.get("/_security/role_mapping")
    mappings = []
    if isinstance(response, dict):
        for mapping_name, mapping_data in response.items():
            mapping_data["name"] = mapping_name
            mappings.append(mapping_data)
    return mappings


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            name=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        security_role_mappings=[],
    )

    try:
        client = Client(module)
        name = module.params.get("name")

        if name is not None:
            item = fetch_single(client, name)
            result["security_role_mappings"] = [item] if item else []
        else:
            result["security_role_mappings"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
