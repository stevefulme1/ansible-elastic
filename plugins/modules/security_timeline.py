#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_timeline
short_description: Manage Kibana Security SIEM timelines
version_added: "1.0.0"
description:
  - Create, update, and delete Kibana Security SIEM timeline resources.
  - Supports check mode and diff mode for safe operations.
  - >-
    Update operations require the version field from the existing timeline
    for optimistic concurrency control.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the timeline resource.
    type: str
    choices: ['present', 'absent']
    default: present
  timeline_id:
    description:
      - The unique identifier of the timeline (savedObjectId).
      - Required when updating or deleting an existing timeline.
    type: str
  title:
    description:
      - The title of the timeline.
    type: str
  description:
    description:
      - A description of the timeline.
    type: str
  timeline_type:
    description:
      - The type of the timeline.
    type: str
    choices: ['default', 'template']
    default: "default"
  columns:
    description:
      - A list of column configurations for the timeline display.
    type: list
    elements: dict
    default: []
  data_providers:
    description:
      - A list of data provider configurations that supply data to the timeline.
    type: list
    elements: dict
    default: []
  kql_mode:
    description:
      - The KQL mode for the timeline query bar.
    type: str
    choices: ['filter', 'search']
    default: "filter"
  sort:
    description:
      - Sort configuration for the timeline.
    type: dict
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a timeline
  stevefulme1.elastic.security_timeline:
    title: "Investigation"
    description: "Security investigation timeline"
    timeline_type: "default"
    kql_mode: "filter"
    columns: []
    data_providers: []
    state: present

- name: Update a timeline
  stevefulme1.elastic.security_timeline:
    timeline_id: "existing-timeline-id"
    title: "Investigation - Updated"
    description: "Updated security investigation timeline"
    state: present

- name: Delete a timeline
  stevefulme1.elastic.security_timeline:
    timeline_id: "existing-timeline-id"
    state: absent
"""

RETURN = r"""
timeline_id:
  description: The savedObjectId of the timeline.
  returned: success
  type: str
title:
  description: The title of the timeline.
  returned: success
  type: str
version:
  description: The version string for optimistic concurrency control.
  returned: success
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of a timeline."""
    timeline_id = module.params.get("timeline_id")
    if timeline_id is not None:
        try:
            response = client.get(
                "/api/timelines",
                params={"id": timeline_id},
            )
            # Single GET returns the timeline object directly or nested
            if isinstance(response, dict):
                # Could be nested in "timeline" key or direct
                timeline = response.get("timeline", response)
                if isinstance(timeline, list):
                    # If it's a list, search for the matching one
                    for item in timeline:
                        if item.get("savedObjectId") == timeline_id:
                            return item
                elif timeline.get("savedObjectId"):
                    return timeline
            return None
        except ClientError:
            return None

    # Try to find by title in the list
    title = module.params.get("title")
    if title is None:
        return None
    try:
        response = client.get("/api/timelines")
        items = response.get("timeline", [])
        for item in items:
            if item.get("title") == title:
                return item
        return None
    except ClientError:
        return None


def needs_update(current, desired):
    """Compare current state against desired params and return True if an update is needed."""
    if current is None:
        return True
    for key, value in desired.items():
        if value is None:
            continue
        current_value = current.get(key)
        if current_value != value:
            return True
    return False


def build_timeline_body(module):
    """Build the timeline body dict from module params."""
    body = {}

    if module.params.get("title") is not None:
        body["title"] = module.params["title"]

    if module.params.get("description") is not None:
        body["description"] = module.params["description"]

    if module.params.get("timeline_type") is not None:
        body["timelineType"] = module.params["timeline_type"]

    if module.params.get("columns") is not None:
        body["columns"] = module.params["columns"]

    if module.params.get("data_providers") is not None:
        body["dataProviders"] = module.params["data_providers"]

    if module.params.get("kql_mode") is not None:
        body["kqlMode"] = module.params["kql_mode"]

    if module.params.get("sort") is not None:
        body["sort"] = module.params["sort"]

    return body


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            timeline_id=dict(
                type="str",
            ),

            title=dict(
                type="str",
            ),

            description=dict(
                type="str",
            ),

            timeline_type=dict(
                type="str",
                choices=["default", "template"],
                default="default",
            ),

            columns=dict(
                type="list",
                elements="dict",
                default=[],
            ),

            data_providers=dict(
                type="list",
                elements="dict",
                default=[],
            ),

            kql_mode=dict(
                type="str",
                choices=["filter", "search"],
                default="filter",
            ),

            sort=dict(
                type="dict",
            ),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    state = module.params["state"]
    result = dict(changed=False, diff=dict(before={}, after={}))

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        current = get_current_state(client, module)

        if state == "present":
            desired = build_timeline_body(module)

            if current is None:
                # Resource does not exist - create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    create_payload = {
                        "timeline": build_timeline_body(module),
                    }
                    # Create uses POST /api/timeline (singular)
                    response = client.post(
                        "/api/timeline",
                        data=create_payload,
                    )
                    if isinstance(response, dict):
                        timeline_data = response.get("data", response.get("timeline", response))
                        if isinstance(timeline_data, dict):
                            result["timeline_id"] = timeline_data.get("savedObjectId")
                            result["title"] = timeline_data.get("title")
                            result["version"] = timeline_data.get("version")
                        result.update({k: v for k, v in response.items() if k not in result})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    update_body = build_timeline_body(module)
                    update_payload = {
                        "timeline": update_body,
                        "timelineId": current.get("savedObjectId"),
                        "version": current.get("version"),
                    }
                    # Update uses PATCH /api/timeline
                    response = client.patch(
                        "/api/timeline",
                        data=update_payload,
                    )
                    if isinstance(response, dict):
                        timeline_data = response.get("data", response.get("timeline", response))
                        if isinstance(timeline_data, dict):
                            result["timeline_id"] = timeline_data.get("savedObjectId")
                            result["title"] = timeline_data.get("title")
                            result["version"] = timeline_data.get("version")
                        result.update({k: v for k, v in response.items() if k not in result})

            else:
                # Resource exists and is up-to-date
                result["timeline_id"] = current.get("savedObjectId")
                result["title"] = current.get("title")
                result["version"] = current.get("version")

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    saved_object_id = module.params.get("timeline_id") or current.get("savedObjectId")
                    # DELETE /api/timelines uses request body with savedObjectIds
                    client._request(
                        "DELETE",
                        "/api/timelines",
                        data={"savedObjectIds": [saved_object_id]},
                    )

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
