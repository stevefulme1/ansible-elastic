#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: fleet_agent_policy_info
short_description: Retrieve information about Fleet agent policies
version_added: "1.0.0"
description:
  - Retrieve a single Fleet agent policy by its identifier, or list all agent policies.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  policy_id:
    description:
      - The unique identifier of the agent policy to retrieve.
      - When omitted, all agent policies are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific Fleet agent policy
  stevefulme1.elastic.fleet_agent_policy_info:
    policy_id: "my-policy-id"
  register: result

- name: List all Fleet agent policies
  stevefulme1.elastic.fleet_agent_policy_info:
  register: result
"""

RETURN = r"""
fleet_agent_policies:
  description: List of Fleet agent policy resources matching the query.
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


def fetch_single(client, policy_id):
    """Retrieve a single Fleet agent policy by identifier."""
    try:
        response = client.get("/api/fleet/agent_policies/{0}".format(policy_id))
        return response.get("item", response) if isinstance(response, dict) else response
    except ClientError:
        return None


def fetch_list(client):
    """List all Fleet agent policies."""
    try:
        response = client.get("/api/fleet/agent_policies")
        if isinstance(response, dict):
            return response.get("items", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            policy_id=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        fleet_agent_policies=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        policy_id = module.params.get("policy_id")

        if policy_id is not None:
            item = fetch_single(client, policy_id)
            result["fleet_agent_policies"] = [item] if item else []
        else:
            result["fleet_agent_policies"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
