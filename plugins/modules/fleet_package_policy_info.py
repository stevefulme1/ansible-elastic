#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: fleet_package_policy_info
short_description: Retrieve information about Fleet package policies
version_added: "1.0.0"
description:
  - Retrieve a single Fleet package policy by its identifier, or list all package policies.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  package_policy_id:
    description:
      - The unique identifier of the package policy to retrieve.
      - When omitted, all package policies are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific Fleet package policy
  stevefulme1.elastic.fleet_package_policy_info:
    package_policy_id: "my-package-policy-id"
  register: result

- name: List all Fleet package policies
  stevefulme1.elastic.fleet_package_policy_info:
  register: result
"""

RETURN = r"""
fleet_package_policies:
  description: List of Fleet package policy resources matching the query.
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


def fetch_single(client, package_policy_id):
    """Retrieve a single Fleet package policy by identifier."""
    try:
        response = client.get("/api/fleet/package_policies/{0}".format(package_policy_id))
        return response.get("item", response) if isinstance(response, dict) else response
    except ClientError:
        return None


def fetch_list(client):
    """List all Fleet package policies."""
    try:
        response = client.get("/api/fleet/package_policies")
        if isinstance(response, dict):
            return response.get("items", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            package_policy_id=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        fleet_package_policies=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        package_policy_id = module.params.get("package_policy_id")

        if package_policy_id is not None:
            item = fetch_single(client, package_policy_id)
            result["fleet_package_policies"] = [item] if item else []
        else:
            result["fleet_package_policies"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
