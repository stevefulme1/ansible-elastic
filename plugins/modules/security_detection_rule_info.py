#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_detection_rule_info
short_description: >-
  Retrieve information about Kibana Security detection rules
version_added: "1.0.0"
description:
  - >-
    Retrieve a single detection rule by its identifier,
    or list all detection rule resources.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  rule_id:
    description:
      - The internal UUID of the detection rule to retrieve.
      - When omitted, all detection rules are listed.
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
- name: Get a specific detection rule
  stevefulme1.elastic.security_detection_rule_info:
    rule_id: "example-rule-id"
  register: result

- name: List all detection rules
  stevefulme1.elastic.security_detection_rule_info:
  register: result

- name: List detection rules with pagination
  stevefulme1.elastic.security_detection_rule_info:
    page: 1
    page_size: 50
  register: result
"""

RETURN = r"""
security_detection_rules:
  description: List of detection rule resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The internal UUID of the detection rule.
      type: str
    name:
      description: The name of the detection rule.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, rule_id):
    """Retrieve a single detection rule by identifier."""
    try:
        response = client.get(
            "/api/detection_engine/rules",
            params={"id": rule_id},
        )
        if isinstance(response, dict) and response.get("id"):
            return response
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List detection rule resources with optional pagination."""
    params = {}

    page = module.params.get("page")
    page_size = module.params.get("page_size")

    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["per_page"] = page_size

    try:
        response = client.get("/api/detection_engine/rules/_find", params=params)
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
        security_detection_rules=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        identifier = module.params.get("rule_id")

        if identifier is not None:
            item = fetch_single(client, identifier)
            result["security_detection_rules"] = [item] if item else []
        else:
            result["security_detection_rules"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
