#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_connector_info
short_description: Retrieve information about Kibana connectors
version_added: "1.0.0"
description:
  - Retrieve a single Kibana connector by its identifier, or list all connectors.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  connector_id:
    description:
      - The unique identifier of the connector to retrieve.
      - When omitted, all connectors are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific Kibana connector
  stevefulme1.elastic.kibana_connector_info:
    connector_id: "my-connector-id"
  register: result

- name: List all Kibana connectors
  stevefulme1.elastic.kibana_connector_info:
  register: result
"""

RETURN = r"""
kibana_connectors:
  description: List of Kibana connector resources matching the query.
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


def fetch_single(client, connector_id):
    """Retrieve a single Kibana connector by identifier."""
    try:
        return client.get("/api/actions/connector/{0}".format(connector_id))
    except ClientError:
        return None


def fetch_list(client):
    """List all Kibana connectors."""
    try:
        items = client.get("/api/actions/connectors")
        return items if isinstance(items, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            connector_id=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        kibana_connectors=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        connector_id = module.params.get("connector_id")

        if connector_id is not None:
            item = fetch_single(client, connector_id)
            result["kibana_connectors"] = [item] if item else []
        else:
            result["kibana_connectors"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
