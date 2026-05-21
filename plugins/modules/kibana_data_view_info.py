#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_data_view_info
short_description: Retrieve information about Kibana data views
version_added: "1.0.0"
description:
  - Retrieve a single Kibana data view by its identifier, or list all data views.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  data_view_id:
    description:
      - The unique identifier of the data view to retrieve.
      - When omitted, all data views are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific Kibana data view
  stevefulme1.elastic.kibana_data_view_info:
    data_view_id: "my-data-view-id"
  register: result

- name: List all Kibana data views
  stevefulme1.elastic.kibana_data_view_info:
  register: result
"""

RETURN = r"""
kibana_data_views:
  description: List of Kibana data view resources matching the query.
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


def fetch_single(client, data_view_id):
    """Retrieve a single Kibana data view by identifier."""
    try:
        response = client.get("/api/data_views/data_view/{0}".format(data_view_id))
        if isinstance(response, dict):
            return response.get("data_view", response)
        return response
    except ClientError:
        return None


def fetch_list(client):
    """List all Kibana data views."""
    try:
        response = client.get("/api/data_views")
        if isinstance(response, dict):
            return response.get("data_view", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            data_view_id=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        kibana_data_views=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        data_view_id = module.params.get("data_view_id")

        if data_view_id is not None:
            item = fetch_single(client, data_view_id)
            result["kibana_data_views"] = [item] if item else []
        else:
            result["kibana_data_views"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
