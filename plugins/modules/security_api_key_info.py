#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_api_key_info
short_description: Retrieve information about Elasticsearch API keys
version_added: "1.0.0"
description:
  - Retrieve a single API key by ID or name, or list all API keys.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  id:
    description:
      - The ID of the API key to retrieve.
      - Mutually exclusive with C(name).
    type: str
    required: false
  name:
    description:
      - The name of the API key to retrieve.
      - Mutually exclusive with C(id).
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get an API key by ID
  stevefulme1.elastic.security_api_key_info:
    id: "abc123"
  register: result

- name: Get an API key by name
  stevefulme1.elastic.security_api_key_info:
    name: "my-api-key"
  register: result

- name: List all API keys
  stevefulme1.elastic.security_api_key_info:
  register: result
"""

RETURN = r"""
security_api_keys:
  description: List of API key resources matching the query.
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


def fetch_single(client, key_id=None, name=None):
    """Retrieve a single API key by ID or name."""
    try:
        params = {}
        if key_id:
            params["id"] = key_id
        elif name:
            params["name"] = name

        response = client.get("/_security/api_key", params=params)
        api_keys = response.get("api_keys", [])
        if api_keys:
            return api_keys[0]
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List all API keys."""
    try:
        response = client.get("/_security/api_key")
        return response.get("api_keys", [])
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            id=dict(type="str", required=False),
            name=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("id", "name"),
        ],
    )

    result = dict(
        changed=False,
        security_api_keys=[],
    )

    try:
        client = Client(module)
        key_id = module.params.get("id")
        name = module.params.get("name")

        if key_id is not None or name is not None:
            item = fetch_single(client, key_id=key_id, name=name)
            result["security_api_keys"] = [item] if item else []
        else:
            result["security_api_keys"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
