#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_space_info
short_description: Retrieve information about Kibana spaces
version_added: "1.0.0"
description:
  - Retrieve a single Kibana space by its identifier, or list all spaces.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  space_id:
    description:
      - The unique identifier of the space to retrieve.
      - When omitted, all spaces are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific Kibana space
  stevefulme1.elastic.kibana_space_info:
    space_id: "marketing"
  register: result

- name: List all Kibana spaces
  stevefulme1.elastic.kibana_space_info:
  register: result
"""

RETURN = r"""
kibana_spaces:
  description: List of Kibana space resources matching the query.
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


def fetch_single(client, space_id):
    """Retrieve a single Kibana space by identifier."""
    try:
        item = client.get("/api/spaces/space/{0}".format(space_id))
        return item if isinstance(item, dict) else None
    except ClientError:
        return None


def fetch_list(client):
    """List all Kibana spaces."""
    try:
        items = client.get("/api/spaces/space")
        return items if isinstance(items, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            space_id=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        kibana_spaces=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        space_id = module.params.get("space_id")

        if space_id is not None:
            item = fetch_single(client, space_id)
            result["kibana_spaces"] = [item] if item else []
        else:
            result["kibana_spaces"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
