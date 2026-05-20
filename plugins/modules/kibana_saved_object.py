#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_saved_object
short_description: Manage Kibana saved objects
version_added: "1.0.0"
description:
  - Create, update, and delete Kibana saved object resources.
  - Supports check mode and diff mode for safe operations.
  - Saved objects include dashboards, visualizations, index patterns, searches, and lenses.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the saved object resource.
    type: str
    choices: ['present', 'absent']
    default: present
  object_type:
    description:
      - The type of the saved object.
      - Common types include C(dashboard), C(visualization), C(index-pattern), C(search), C(lens).
    type: str
    required: true
  object_id:
    description:
      - The unique identifier of the saved object.
    type: str
    required: true
  attributes:
    description:
      - The attributes of the saved object.
      - Required when creating a new saved object.
    type: dict
  references:
    description:
      - A list of references to other saved objects.
    type: list
    elements: dict
    default: []
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Kibana index pattern
  stevefulme1.elastic.kibana_saved_object:
    object_type: "index-pattern"
    object_id: "my-index-pattern"
    attributes:
      title: "logs-*"
      timeFieldName: "@timestamp"
    state: present

- name: Create a Kibana dashboard
  stevefulme1.elastic.kibana_saved_object:
    object_type: "dashboard"
    object_id: "my-dashboard"
    attributes:
      title: "My Dashboard"
      description: "A test dashboard"
      panelsJSON: "[]"
    references: []
    state: present

- name: Update a saved object
  stevefulme1.elastic.kibana_saved_object:
    object_type: "index-pattern"
    object_id: "my-index-pattern"
    attributes:
      title: "logs-*"
      timeFieldName: "@timestamp"
    state: present

- name: Delete a saved object
  stevefulme1.elastic.kibana_saved_object:
    object_type: "index-pattern"
    object_id: "my-index-pattern"
    state: absent
"""

RETURN = r"""
id:
  description: The identifier of the saved object.
  returned: success
  type: str
type:
  description: The type of the saved object.
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
    """Retrieve the current state of a saved object via GET /api/saved_objects/{type}/{id}."""
    object_type = module.params.get("object_type")
    object_id = module.params.get("object_id")
    if object_type is None or object_id is None:
        return None
    try:
        response = client.get("/api/saved_objects/{0}/{1}".format(object_type, object_id))
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

    if module.params.get("attributes") is not None:
        payload["attributes"] = module.params["attributes"]

    if module.params.get("references") is not None:
        payload["references"] = module.params["references"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            object_type=dict(
                type="str",
                required=True,
            ),

            object_id=dict(
                type="str",
                required=True,
            ),

            attributes=dict(
                type="dict",
            ),

            references=dict(
                type="list",
                elements="dict",
                default=[],
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
            desired = build_payload(module)

            if current is None:
                # Resource does not exist - create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    object_type = module.params["object_type"]
                    object_id = module.params["object_id"]
                    path = "/api/saved_objects/{0}/{1}".format(object_type, object_id)
                    response = client.post(
                        path,
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    object_type = module.params["object_type"]
                    object_id = module.params["object_id"]
                    path = "/api/saved_objects/{0}/{1}".format(object_type, object_id)
                    response = client.put(
                        path,
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date
                result["id"] = current.get("id")
                result["type"] = current.get("type")

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    object_type = module.params["object_type"]
                    object_id = module.params["object_id"]
                    path = "/api/saved_objects/{0}/{1}".format(object_type, object_id)
                    client.delete(path)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
