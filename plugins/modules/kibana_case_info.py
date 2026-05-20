#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_case_info
short_description: >-
  Retrieve information about Kibana case resources
version_added: "1.0.0"
description:
  - >-
    Retrieve a single Kibana case by its identifier,
    or list all case resources.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  case_id:
    description:
      - The unique identifier of the case to retrieve.
      - When omitted, all case resources are listed.
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
- name: Get a specific case
  stevefulme1.elastic.kibana_case_info:
    case_id: "example_id"
  register: result

- name: List all cases
  stevefulme1.elastic.kibana_case_info:
  register: result

- name: List cases with pagination
  stevefulme1.elastic.kibana_case_info:
    page: 1
    page_size: 50
  register: result
"""

RETURN = r"""
kibana_cases:
  description: List of case resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the case.
      type: str
    title:
      description: The title of the case.
      type: str
    description:
      description: The description of the case.
      type: str
    status:
      description: The status of the case.
      type: str
    severity:
      description: The severity of the case.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, identifier):
    """Retrieve a single case by identifier."""
    try:
        response = client.get("/api/cases/{0}".format(identifier))
        if isinstance(response, dict) and response.get("id"):
            return response
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List case resources with optional pagination."""
    params = {}

    page = module.params.get("page")
    page_size = module.params.get("page_size")

    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["perPage"] = page_size

    try:
        response = client.get("/api/cases/_find", params=params)
        if isinstance(response, dict):
            return response.get("cases", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            case_id=dict(type="str", required=False),
            page=dict(type="int", required=False),
            page_size=dict(type="int", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("case_id", "page"),
            ("case_id", "page_size"),
        ],
    )

    result = dict(
        changed=False,
        kibana_cases=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        identifier = module.params.get("case_id")

        if identifier is not None:
            item = fetch_single(client, identifier)
            result["kibana_cases"] = [item] if item else []
        else:
            result["kibana_cases"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
