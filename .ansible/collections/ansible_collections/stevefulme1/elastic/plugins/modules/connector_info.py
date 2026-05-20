#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: connector_info
short_description: >-
  Retrieve information about connector resources
version_added: "1.0.0"
description:
  - >-
    Retrieve a single connector by its identifier,
    or list all connector resources.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  id:
    description:
      - The unique identifier of the connector to retrieve.
      - When omitted, all connector resources are listed.
    type: str
    required: false
  name:
    description:
      - Filter results by name.
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
- name: Get a specific connector
  stevefulme1.elastic.connector_info:
    id: "example_id"
  register: result
- name: List all connector resources
  stevefulme1.elastic.connector_info:
  register: result
- name: List connector resources filtered by name
  stevefulme1.elastic.connector_info:
    name: "my_connector"
  register: result
- name: List connector resources with pagination
  stevefulme1.elastic.connector_info:
    page: 1
    page_size: 50
  register: result
"""

RETURN = r"""
connectors:
  description: List of connector resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    api_key_id:
      description: >-
      type: str
    api_key_secret_id:
      description: >-
      type: str
    configuration:
      description: >-
      type: dict
    custom_scheduling:
      description: >-
      type: dict
    deleted:
      description: >-
      type: bool
    description:
      description: >-
      type: str
    error:
      description: >-
      type: str
    features:
      description: >-
      type: dict
    filtering:
      description: >-
      type: list
    id:
      description: >-
      type: str
    index_name:
      description: >-
      type: str
    is_native:
      description: >-
      type: bool
    language:
      description: >-
      type: str
    last_access_control_sync_error:
      description: >-
      type: str
    last_access_control_sync_scheduled_at:
      description: >-
      type: str
    last_access_control_sync_status:
      description: >-
      type: str
    last_deleted_document_count:
      description: >-
      type: float
    last_incremental_sync_scheduled_at:
      description: >-
      type: str
    last_indexed_document_count:
      description: >-
      type: float
    last_seen:
      description: >-
      type: str
    last_sync_error:
      description: >-
      type: str
    last_sync_scheduled_at:
      description: >-
      type: str
    last_sync_status:
      description: >-
      type: str
    last_synced:
      description: >-
      type: str
    name:
      description: >-
      type: str
    pipeline:
      description: >-
      type: dict
    scheduling:
      description: >-
      type: dict
    service_type:
      description: >-
      type: str
    status:
      description: >-
      type: str
    sync_cursor:
      description: >-
      type: dict
    sync_now:
      description: >-
      type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, identifier):
    """Retrieve a single connector by identifier."""

    # No single-resource GET endpoint; filter from list
    items = client.get("/_connector")
    if isinstance(items, dict):
        items = items.get("results", items.get("data", items.get("items", [])))
    for item in items:
        if str(item.get("id")) == str(identifier):
            return item
    return None


def fetch_list(client, module):
    """List connector resources with optional filtering and pagination."""

    params = {}

    name_filter = module.params.get("name")
    if name_filter is not None:
        params["name"] = name_filter

    page = module.params.get("page")
    page_size = module.params.get("page_size")

    if page is not None or page_size is not None:
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        response = client.get("/_connector", params=params)
        if isinstance(response, dict):
            return response.get("results", response.get("data", response.get("items", [])))
        return response if isinstance(response, list) else []
    else:
        return client.get_paginated("/_connector", params=params)


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            id=dict(type="str", required=False),

            name=dict(type="str", required=False),














            page=dict(type="int", required=False),
            page_size=dict(type="int", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("id", "page"),
            ("id", "page_size"),
        ],
    )

    result = dict(
        changed=False,
        connectors=[],
    )

    try:
        client = Client(module)
        identifier = module.params.get("id")

        if identifier is not None:
            item = fetch_single(client, identifier)
            result["connectors"] = [item] if item else []
        else:
            result["connectors"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
