#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: watcher_info
short_description: >-
  Retrieve information about Elasticsearch Watcher watches
version_added: "1.0.0"
description:
  - >-
    Retrieve a single watch by its identifier,
    or list all watches via the Watcher query API.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  id:
    description:
      - The unique identifier of the watch to retrieve.
      - When omitted, all watches are listed.
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
- name: Get a specific watch
  stevefulme1.elastic.watcher_info:
    id: "error_monitor"
  register: result

- name: List all watches
  stevefulme1.elastic.watcher_info:
  register: result

- name: List watches with pagination
  stevefulme1.elastic.watcher_info:
    page: 1
    page_size: 50
  register: result
"""

RETURN = r"""
watchers:
  description: List of watcher watch resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    _id:
      description: The identifier of the watch.
      type: str
    status:
      description: The current status of the watch.
      type: dict
    watch:
      description: The watch definition including trigger, input, condition, and actions.
      type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, identifier):
    """Retrieve a single watch by identifier via GET /_watcher/watch/{id}."""
    try:
        response = client.get("/_watcher/watch/{0}".format(identifier))
        if isinstance(response, dict) and response.get("found", False):
            watch = response.get("watch", {})
            watch["_id"] = response.get("_id", identifier)
            watch["_version"] = response.get("_version")
            watch["status"] = response.get("status", {})
            return watch
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List watches via POST /_watcher/_query/watches with optional pagination."""
    page = module.params.get("page")
    page_size = module.params.get("page_size")

    body = {}
    if page_size is not None:
        body["size"] = page_size
    else:
        body["size"] = 100

    if page is not None and page_size is not None:
        body["from"] = (page - 1) * page_size

    try:
        response = client.post("/_watcher/_query/watches", data=body)
    except ClientError:
        return []

    if isinstance(response, dict):
        watches = response.get("watches", [])
        results = []
        for entry in watches:
            watch = entry.get("watch", {})
            watch["_id"] = entry.get("_id")
            watch["status"] = entry.get("status", {})
            results.append(watch)
        return results

    return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            id=dict(type="str", required=False),
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
        watchers=[],
    )

    try:
        client = Client(module)
        identifier = module.params.get("id")

        if identifier is not None:
            item = fetch_single(client, identifier)
            result["watchers"] = [item] if item else []
        else:
            result["watchers"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
