#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Auto-generated
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: query_rule_info
short_description: Retrieve information about _query_rule resources
version_added: "1.0.0"
description:
  - Retrieve a single _query_rule by its identifier, or list all _query_rule resources.
  - This module always reports C(changed=False).
author:
  - "Auto-generated"
options:
  ruleset_id:
    description:
      - The unique identifier of the _query_rule to retrieve.
      - When omitted, all _query_rule resources are listed.
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
- name: Get a specific _query_rule
  stevefulme1.elastic._query_rule_info:
    ruleset_id: "example_id"
  register: result

- name: List all _query_rule resources
  stevefulme1.elastic._query_rule_info:
  register: result



- name: List _query_rule resources with pagination
  stevefulme1.elastic._query_rule_info:
    page: 1
    page_size: 50
  register: result
"""

RETURN = r"""
_query_rules:
  description: List of _query_rule resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:

    ruleset_id:
      description: >-
        
      type: str


    rule_total_count:
      description: >-
        The number of rules associated with the ruleset.
      type: float


    rule_criteria_types_counts:
      description: >-
        A map of criteria type (for example, exact) to the number of rules of that type. NOTE: The...
      type: dict


    rule_type_counts:
      description: >-
        A map of rule type (for example, pinned) to the number of rules of that type.
      type: dict


"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, identifier):
    """Retrieve a single _query_rule by identifier."""

    # No single-resource GET endpoint; filter from list
    items = client.get("/_query_rules")
    if isinstance(items, dict):
        items = items.get("results", items.get("data", items.get("items", [])))
    for item in items:
        if str(item.get("ruleset_id")) == str(identifier):
            return item
    return None



def fetch_list(client, module):
    """List _query_rule resources with optional filtering and pagination."""

    params = {}







    page = module.params.get("page")
    page_size = module.params.get("page_size")

    if page is not None or page_size is not None:
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        response = client.get("/_query_rules", params=params)
        if isinstance(response, dict):
            return response.get("results", response.get("data", response.get("items", [])))
        return response if isinstance(response, list) else []
    else:
        return client.get_paginated("/_query_rules", params=params)



def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            ruleset_id=dict(type="str", required=False),




            page=dict(type="int", required=False),
            page_size=dict(type="int", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("ruleset_id", "page"),
            ("ruleset_id", "page_size"),
        ],
    )

    result = dict(
        changed=False,
        _query_rules=[],
    )

    try:
        client = Client(module)
        identifier = module.params.get("ruleset_id")

        if identifier is not None:
            item = fetch_single(client, identifier)
            result["_query_rules"] = [item] if item else []
        else:
            result["_query_rules"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
