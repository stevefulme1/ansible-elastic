#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: fleet_server_host_info
short_description: Retrieve information about Fleet server hosts
version_added: "1.0.0"
description:
  - Retrieve a single Fleet server host by its identifier, or list all server hosts.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  host_id:
    description:
      - The unique identifier of the Fleet server host to retrieve.
      - When omitted, all server hosts are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific Fleet server host
  stevefulme1.elastic.fleet_server_host_info:
    host_id: "my-host-id"
  register: result

- name: List all Fleet server hosts
  stevefulme1.elastic.fleet_server_host_info:
  register: result
"""

RETURN = r"""
fleet_server_hosts:
  description: List of Fleet server host resources matching the query.
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


def fetch_single(client, host_id):
    """Retrieve a single Fleet server host by identifier."""
    try:
        response = client.get("/api/fleet/fleet_server_hosts/{0}".format(host_id))
        return response.get("item", response) if isinstance(response, dict) else response
    except ClientError:
        return None


def fetch_list(client):
    """List all Fleet server hosts."""
    try:
        response = client.get("/api/fleet/fleet_server_hosts")
        if isinstance(response, dict):
            return response.get("items", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            host_id=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        fleet_server_hosts=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        host_id = module.params.get("host_id")

        if host_id is not None:
            item = fetch_single(client, host_id)
            result["fleet_server_hosts"] = [item] if item else []
        else:
            result["fleet_server_hosts"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
