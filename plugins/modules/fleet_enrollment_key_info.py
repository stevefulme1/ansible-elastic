#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: fleet_enrollment_key_info
short_description: Retrieve information about Fleet enrollment API keys
version_added: "1.0.0"
description:
  - Retrieve a single Fleet enrollment key by its identifier, or list all enrollment keys.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  key_id:
    description:
      - The unique identifier of the enrollment key to retrieve.
      - When omitted, all enrollment keys are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific Fleet enrollment key
  stevefulme1.elastic.fleet_enrollment_key_info:
    key_id: "my-key-id"
  register: result

- name: List all Fleet enrollment keys
  stevefulme1.elastic.fleet_enrollment_key_info:
  register: result
"""

RETURN = r"""
fleet_enrollment_keys:
  description: List of Fleet enrollment key resources matching the query.
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


def fetch_single(client, key_id):
    """Retrieve a single Fleet enrollment key by identifier."""
    try:
        response = client.get("/api/fleet/enrollment_api_keys/{0}".format(key_id))
        return response.get("item", response) if isinstance(response, dict) else response
    except ClientError:
        return None


def fetch_list(client):
    """List all Fleet enrollment keys."""
    try:
        response = client.get("/api/fleet/enrollment_api_keys")
        if isinstance(response, dict):
            return response.get("items", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            key_id=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        fleet_enrollment_keys=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        key_id = module.params.get("key_id")

        if key_id is not None:
            item = fetch_single(client, key_id)
            result["fleet_enrollment_keys"] = [item] if item else []
        else:
            result["fleet_enrollment_keys"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
