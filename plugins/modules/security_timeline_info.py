#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_timeline_info
short_description: >-
  Retrieve information about Kibana Security SIEM timelines
version_added: "1.0.0"
description:
  - >-
    Retrieve a single timeline by its identifier,
    or list all timeline resources.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  timeline_id:
    description:
      - The savedObjectId of the timeline to retrieve.
      - When omitted, all timelines are listed.
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
- name: Get a specific timeline
  stevefulme1.elastic.security_timeline_info:
    timeline_id: "example-timeline-id"
  register: result

- name: List all timelines
  stevefulme1.elastic.security_timeline_info:
  register: result

- name: List timelines with pagination
  stevefulme1.elastic.security_timeline_info:
    page: 1
    page_size: 50
  register: result
"""

RETURN = r"""
security_timelines:
  description: List of timeline resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    savedObjectId:
      description: The unique identifier of the timeline saved object.
      type: str
    title:
      description: The title of the timeline.
      type: str
    version:
      description: The version string for optimistic concurrency control.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, timeline_id):
    """Retrieve a single timeline by identifier."""
    try:
        response = client.get(
            "/api/timelines",
            params={"id": timeline_id},
        )
        if isinstance(response, dict):
            timeline = response.get("timeline", response)
            if isinstance(timeline, list):
                for item in timeline:
                    if item.get("savedObjectId") == timeline_id:
                        return item
            elif isinstance(timeline, dict) and timeline.get("savedObjectId"):
                return timeline
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List timeline resources with optional pagination."""
    params = {}

    page = module.params.get("page")
    page_size = module.params.get("page_size")

    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["per_page"] = page_size

    try:
        response = client.get("/api/timelines", params=params)
        if isinstance(response, dict):
            return response.get("timeline", [])
        return response if isinstance(response, list) else []
    except ClientError:
        return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            timeline_id=dict(type="str", required=False),
            page=dict(type="int", required=False),
            page_size=dict(type="int", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("timeline_id", "page"),
            ("timeline_id", "page_size"),
        ],
    )

    result = dict(
        changed=False,
        security_timelines=[],
    )

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        identifier = module.params.get("timeline_id")

        if identifier is not None:
            item = fetch_single(client, identifier)
            result["security_timelines"] = [item] if item else []
        else:
            result["security_timelines"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
