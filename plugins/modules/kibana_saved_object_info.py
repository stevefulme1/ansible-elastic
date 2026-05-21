#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_saved_object_info
short_description: >-
  Retrieve information about Kibana saved object resources
version_added: "1.0.0"
description:
  - >-
    Retrieve a single Kibana saved object by its type and identifier,
    or list all saved objects of a given type.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  object_type:
    description:
      - The type of the saved object to retrieve or list.
      - Common types include C(dashboard), C(visualization), C(index-pattern), C(search), C(lens).
    type: str
    required: true
  object_id:
    description:
      - The unique identifier of the saved object to retrieve.
      - When omitted, all saved objects of the given type are listed.
    type: str
    required: false
  page:
    description:
      - Page number for paginated results.
      - Only applies when listing resources.
    type: int
    required: false
  page_size:
    description:
      - Number of results per page.
      - Only applies when listing resources.
    type: int
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific saved object
  stevefulme1.elastic.kibana_saved_object_info:
    object_type: "index-pattern"
    object_id: "my-index-pattern"
  register: result

- name: List all index patterns
  stevefulme1.elastic.kibana_saved_object_info:
    object_type: "index-pattern"
  register: result

- name: List dashboards with pagination
  stevefulme1.elastic.kibana_saved_object_info:
    object_type: "dashboard"
    page: 1
    page_size: 50
  register: result
"""

RETURN = r"""
kibana_saved_objects:
  description: List of saved object resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the saved object.
      type: str
    type:
      description: The type of the saved object.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, object_type, object_id):
    """Retrieve a single saved object by type and identifier."""
    try:
        response = client.get("/api/saved_objects/{0}/{1}".format(object_type, object_id))
        if isinstance(response, dict) and response.get("id"):
            return response
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List saved object resources with optional pagination."""
    object_type = module.params["object_type"]
    params = {"type": object_type}

    page = module.params.get("page")
    page_size = module.params.get("page_size")

    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["per_page"] = page_size

    try:
        response = client.get("/api/saved_objects/_find", params=params)
        if isinstance(response, dict):
            return response.get("saved_objects", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            object_type=dict(type="str", required=True),
            object_id=dict(type="str", required=False),
            page=dict(type="int", required=False),
            page_size=dict(type="int", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("object_id", "page"),
            ("object_id", "page_size"),
        ],
    )

    result = dict(
        changed=False,
        kibana_saved_objects=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        object_type = module.params["object_type"]
        object_id = module.params.get("object_id")

        if object_id is not None:
            item = fetch_single(client, object_type, object_id)
            result["kibana_saved_objects"] = [item] if item else []
        else:
            result["kibana_saved_objects"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
