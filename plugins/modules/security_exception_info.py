#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_exception_info
short_description: >-
  Retrieve information about Kibana Security exception lists
version_added: "1.0.0"
description:
  - >-
    Retrieve a single exception list by its list_id or exception_id,
    or list all exception list resources.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  exception_id:
    description:
      - The internal UUID of the exception list to retrieve.
      - When omitted along with C(list_id), all exception lists are listed.
    type: str
    required: false
  list_id:
    description:
      - The user-defined slug of the exception list to retrieve.
      - When omitted along with C(exception_id), all exception lists are listed.
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
- name: Get a specific exception list by list_id
  stevefulme1.elastic.security_exception_info:
    list_id: "trusted-processes"
  register: result

- name: Get a specific exception list by exception_id
  stevefulme1.elastic.security_exception_info:
    exception_id: "some-uuid"
  register: result

- name: List all exception lists
  stevefulme1.elastic.security_exception_info:
  register: result

- name: List exception lists with pagination
  stevefulme1.elastic.security_exception_info:
    page: 1
    page_size: 50
  register: result
"""

RETURN = r"""
security_exceptions:
  description: List of exception list resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The internal UUID of the exception list.
      type: str
    list_id:
      description: The user-defined slug identifier.
      type: str
    name:
      description: The name of the exception list.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, exception_id=None, list_id=None):
    """Retrieve a single exception list by identifier."""
    params = {}
    if list_id is not None:
        params["list_id"] = list_id
    elif exception_id is not None:
        params["id"] = exception_id
    else:
        return None

    try:
        response = client.get("/api/exception_lists", params=params)
        if isinstance(response, dict) and response.get("id"):
            return response
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List exception list resources with optional pagination."""
    params = {}

    page = module.params.get("page")
    page_size = module.params.get("page_size")

    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["per_page"] = page_size

    try:
        response = client.get("/api/exception_lists/_find", params=params)
        if isinstance(response, dict):
            return response.get("data", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            exception_id=dict(type="str", required=False),
            list_id=dict(type="str", required=False),
            page=dict(type="int", required=False),
            page_size=dict(type="int", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("exception_id", "page"),
            ("exception_id", "page_size"),
            ("list_id", "page"),
            ("list_id", "page_size"),
        ],
    )

    result = dict(
        changed=False,
        security_exceptions=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        exception_id = module.params.get("exception_id")
        list_id = module.params.get("list_id")

        if exception_id is not None or list_id is not None:
            item = fetch_single(client, exception_id=exception_id, list_id=list_id)
            result["security_exceptions"] = [item] if item else []
        else:
            result["security_exceptions"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
