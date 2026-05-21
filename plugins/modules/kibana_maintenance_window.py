#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_maintenance_window
short_description: Manage Kibana maintenance windows
version_added: "1.0.0"
description:
  - Create, update, and delete Kibana maintenance window resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the maintenance window resource.
    type: str
    choices: ['present', 'absent']
    default: present
  window_id:
    description:
      - The unique identifier of the maintenance window.
      - Required when updating or deleting an existing maintenance window.
    type: str
  title:
    description:
      - The title of the maintenance window.
    type: str
    required: true
  duration:
    description:
      - The duration of the maintenance window in milliseconds.
    type: int
    required: true
  r_rule:
    description:
      - The recurrence rule for the maintenance window.
      - Must include C(dtstart), C(tzid), and C(freq) keys.
    type: dict
    required: true
  category_ids:
    description:
      - List of category identifiers for the maintenance window.
    type: list
    elements: str
  enabled:
    description:
      - Whether the maintenance window is enabled.
    type: bool
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a maintenance window
  stevefulme1.elastic.kibana_maintenance_window:
    title: "Planned Maintenance"
    duration: 3600000
    r_rule:
      dtstart: "2024-03-01T00:00:00.000Z"
      tzid: "UTC"
      freq: 0
    category_ids:
      - observability
    state: present

- name: Update a maintenance window
  stevefulme1.elastic.kibana_maintenance_window:
    window_id: "existing_id"
    title: "Updated Maintenance"
    duration: 7200000
    r_rule:
      dtstart: "2024-03-01T00:00:00.000Z"
      tzid: "UTC"
      freq: 0
    state: present

- name: Delete a maintenance window
  stevefulme1.elastic.kibana_maintenance_window:
    window_id: "existing_id"
    title: "unused"
    duration: 0
    r_rule:
      dtstart: "2024-01-01T00:00:00.000Z"
      tzid: "UTC"
      freq: 0
    state: absent
"""

RETURN = r"""
id:
  description: The unique identifier of the maintenance window.
  returned: success
  type: str
title:
  description: The title of the maintenance window.
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
    """Retrieve the current state of the maintenance window via GET."""
    identifier = module.params.get("window_id")

    if identifier is None:
        return None
    try:
        response = client.get("/api/maintenance_window/{0}".format(identifier))
        if isinstance(response, dict) and response.get("id"):
            return response
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


def build_payload(module):
    """Build the API request payload from module params."""
    payload = {}

    if module.params.get("title") is not None:
        payload["title"] = module.params["title"]

    if module.params.get("duration") is not None:
        payload["duration"] = module.params["duration"]

    if module.params.get("r_rule") is not None:
        payload["rRule"] = module.params["r_rule"]

    if module.params.get("category_ids") is not None:
        payload["category_ids"] = module.params["category_ids"]

    if module.params.get("enabled") is not None:
        payload["enabled"] = module.params["enabled"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            window_id=dict(type="str"),
            title=dict(type="str", required=True),
            duration=dict(type="int", required=True),
            r_rule=dict(type="dict", required=True),
            category_ids=dict(
                type="list",
                elements="str",
            ),
            enabled=dict(type="bool"),
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
            desired = build_payload(module)

            if current is None:
                # Resource does not exist -- create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    response = client.post(
                        "/api/maintenance_window",
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    identifier = current.get("id")
                    response = client.post(
                        "/api/maintenance_window/{0}".format(identifier),
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date
                pass

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    identifier = current.get("id")
                    client.delete("/api/maintenance_window/{0}".format(identifier))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
