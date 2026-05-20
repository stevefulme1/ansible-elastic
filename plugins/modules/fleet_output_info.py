#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: fleet_output_info
short_description: Retrieve information about Fleet outputs
version_added: "1.0.0"
description:
  - Retrieve a single Fleet output by its identifier, or list all outputs.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  output_id:
    description:
      - The unique identifier of the output to retrieve.
      - When omitted, all outputs are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific Fleet output
  stevefulme1.elastic.fleet_output_info:
    output_id: "my-output-id"
  register: result

- name: List all Fleet outputs
  stevefulme1.elastic.fleet_output_info:
  register: result
"""

RETURN = r"""
fleet_outputs:
  description: List of Fleet output resources matching the query.
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


def fetch_single(client, output_id):
    """Retrieve a single Fleet output by identifier."""
    try:
        response = client.get("/api/fleet/outputs/{0}".format(output_id))
        return response.get("item", response) if isinstance(response, dict) else response
    except ClientError:
        return None


def fetch_list(client):
    """List all Fleet outputs."""
    try:
        response = client.get("/api/fleet/outputs")
        if isinstance(response, dict):
            return response.get("items", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            output_id=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        fleet_outputs=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        output_id = module.params.get("output_id")

        if output_id is not None:
            item = fetch_single(client, output_id)
            result["fleet_outputs"] = [item] if item else []
        else:
            result["fleet_outputs"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
