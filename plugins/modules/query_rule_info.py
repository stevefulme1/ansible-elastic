#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: query_rule_info
short_description: >-
  Retrieve information about Elasticsearch query rulesets
version_added: "1.0.0"
description:
  - >-
    Retrieve a single query ruleset by its identifier,
    or list all query ruleset resources.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  ruleset_id:
    description:
      - The unique identifier of the query ruleset to retrieve.
      - When omitted, all query ruleset resources are listed.
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
- name: Get a specific query ruleset
  stevefulme1.elastic.query_rule_info:
    ruleset_id: "example_id"
  register: result
- name: List all query ruleset resources
  stevefulme1.elastic.query_rule_info:
  register: result
- name: List query ruleset resources with pagination
  stevefulme1.elastic.query_rule_info:
    from: 0
    size: 50
  register: result
"""

RETURN = r"""
query_rules:
  description: List of query ruleset resources matching the query.
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
      type: int
    rule_criteria_types_counts:
      description: >-
        A map of criteria type (for example, exact) to the number of rules of that type.
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
    auth_mutually_exclusive,
    auth_required_one_of,
    auth_required_together,
)


def fetch_single(client, ruleset_id):
    """Retrieve a single query ruleset by identifier."""
    return client.get("/_query_rules/{0}".format(ruleset_id))


def fetch_list(client, module):
    """List query ruleset resources with optional pagination."""
    params = {}

    from_param = module.params.get("from")
    size_param = module.params.get("size")

    if from_param is not None:
        params["from"] = from_param
    if size_param is not None:
        params["size"] = size_param

    response = client.get("/_query_rules", params=params)
    if isinstance(response, dict):
        return response.get("results", [])
    return response if isinstance(response, list) else []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            ruleset_id=dict(type="str", required=False),
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
        query_rules=[],
    )

    try:
        client = Client(module)
        ruleset_id = module.params.get("ruleset_id")

        if ruleset_id is not None:
            item = fetch_single(client, ruleset_id)
            result["query_rules"] = [item] if item else []
        else:
            result["query_rules"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
