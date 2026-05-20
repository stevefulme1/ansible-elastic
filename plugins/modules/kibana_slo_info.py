#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_slo_info
short_description: >-
  Retrieve information about Kibana SLO resources
version_added: "1.0.0"
description:
  - >-
    Retrieve a single Kibana SLO by its identifier,
    or list all SLO resources.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  slo_id:
    description:
      - The unique identifier of the SLO to retrieve.
      - When omitted, all SLOs are listed.
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
- name: Get a specific SLO
  stevefulme1.elastic.kibana_slo_info:
    slo_id: "example-slo-id"
  register: result

- name: List all SLOs
  stevefulme1.elastic.kibana_slo_info:
  register: result

- name: List SLOs with pagination
  stevefulme1.elastic.kibana_slo_info:
    page: 1
    page_size: 50
  register: result
"""

RETURN = r"""
kibana_slos:
  description: List of SLO resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The unique identifier of the SLO.
      type: str
    name:
      description: The name of the SLO.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, slo_id):
    """Retrieve a single SLO by identifier."""
    try:
        response = client.get("/api/observability/slos/{0}".format(slo_id))
        if isinstance(response, dict) and response.get("id"):
            return response
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List SLO resources with optional pagination."""
    params = {}

    page = module.params.get("page")
    page_size = module.params.get("page_size")

    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["perPage"] = page_size

    try:
        response = client.get("/api/observability/slos", params=params)
        if isinstance(response, dict):
            return response.get("results", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            slo_id=dict(type="str", required=False),
            page=dict(type="int", required=False),
            page_size=dict(type="int", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("slo_id", "page"),
            ("slo_id", "page_size"),
        ],
    )

    result = dict(
        changed=False,
        kibana_slos=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        identifier = module.params.get("slo_id")

        if identifier is not None:
            item = fetch_single(client, identifier)
            result["kibana_slos"] = [item] if item else []
        else:
            result["kibana_slos"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
