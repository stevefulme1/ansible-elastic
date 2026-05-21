#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_alerting_rule_info
short_description: >-
  Retrieve information about Kibana alerting rule resources
version_added: "1.0.0"
description:
  - >-
    Retrieve a single Kibana alerting rule by its identifier,
    or list all alerting rule resources.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  rule_id:
    description:
      - The unique identifier of the alerting rule to retrieve.
      - When omitted, all alerting rules are listed.
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
- name: Get a specific alerting rule
  stevefulme1.elastic.kibana_alerting_rule_info:
    rule_id: "example-rule-id"
  register: result

- name: List all alerting rules
  stevefulme1.elastic.kibana_alerting_rule_info:
  register: result

- name: List alerting rules with pagination
  stevefulme1.elastic.kibana_alerting_rule_info:
    page: 1
    page_size: 50
  register: result
"""

RETURN = r"""
kibana_alerting_rules:
  description: List of alerting rule resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the alerting rule.
      type: str
    name:
      description: The name of the alerting rule.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, rule_id):
    """Retrieve a single alerting rule by identifier."""
    try:
        response = client.get("/api/alerting/rule/{0}".format(rule_id))
        if isinstance(response, dict) and response.get("id"):
            return response
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List alerting rule resources with optional pagination."""
    params = {}

    page = module.params.get("page")
    page_size = module.params.get("page_size")

    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["per_page"] = page_size

    try:
        response = client.get("/api/alerting/rules/_find", params=params)
        if isinstance(response, dict):
            return response.get("data", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            rule_id=dict(type="str", required=False),
            page=dict(type="int", required=False),
            page_size=dict(type="int", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("rule_id", "page"),
            ("rule_id", "page_size"),
        ],
    )

    result = dict(
        changed=False,
        kibana_alerting_rules=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        identifier = module.params.get("rule_id")

        if identifier is not None:
            item = fetch_single(client, identifier)
            result["kibana_alerting_rules"] = [item] if item else []
        else:
            result["kibana_alerting_rules"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
