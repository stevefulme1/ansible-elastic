#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: connector_info
short_description: >-
  Retrieve information about Elasticsearch connector resources
version_added: "0.1.0"
description:
  - >-
    Retrieve a single connector by its identifier,
    or list all connector resources.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  connector_id:
    description:
      - The unique identifier of the connector to retrieve.
      - When omitted, all connector resources are listed.
    type: str
    required: false
  name:
    description:
      - Filter results by name.
    type: str
    required: false
  from:
    description:
      - Starting offset for paginated results.
      - Only applies when listing resources.
    type: int
    required: false
  size:
    description:
      - Number of results to return.
      - Only applies when listing resources.
    type: int
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific connector
  stevefulme1.elastic.connector_info:
    connector_id: "example_id"
  register: result
- name: List all connector resources
  stevefulme1.elastic.connector_info:
  register: result
- name: List connector resources filtered by name
  stevefulme1.elastic.connector_info:
    name: "my_connector"
  register: result
- name: List connector resources with pagination
  stevefulme1.elastic.connector_info:
    from: 0
    size: 50
  register: result
"""

RETURN = r"""
connectors:
  description: List of connector resources matching the query.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
    auth_mutually_exclusive,
    auth_required_one_of,
    auth_required_together,
)


def fetch_single(client, connector_id):
    """Retrieve a single connector by identifier."""
    return client.get("/_connector/{0}".format(connector_id))


def fetch_list(client, module):
    """List connector resources with optional filtering and pagination."""
    params = {}

    name_filter = module.params.get("name")
    if name_filter is not None:
        params["name"] = name_filter

    from_param = module.params.get("from")
    size_param = module.params.get("size")

    if from_param is not None:
        params["from"] = from_param
    if size_param is not None:
        params["size"] = size_param

    response = client.get("/_connector", params=params)
    if isinstance(response, dict):
        return response.get("results", [])
    return response if isinstance(response, list) else []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            connector_id=dict(type="str", required=False),
            name=dict(type="str", required=False),
            **{"from": dict(type="int", required=False)},
            size=dict(type="int", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        mutually_exclusive=auth_mutually_exclusive(),
        required_together=auth_required_together(),
        required_one_of=auth_required_one_of(),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        connectors=[],
    )

    try:
        client = Client(module)
        connector_id = module.params.get("connector_id")

        if connector_id is not None:
            item = fetch_single(client, connector_id)
            result["connectors"] = [item] if item else []
        else:
            result["connectors"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
