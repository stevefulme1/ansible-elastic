#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_data_view
short_description: Manage Kibana data views
version_added: "1.0.0"
description:
  - Create, update, and delete Kibana data view resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the data view.
    type: str
    choices: ['present', 'absent']
    default: present
  data_view_id:
    description:
      - The unique identifier for the data view.
      - Required when updating or deleting a data view.
      - If omitted during creation, Kibana generates an identifier automatically.
    type: str
  title:
    description:
      - The index pattern string, for example C(logs-*).
      - Required when creating a data view.
    type: str
  time_field_name:
    description:
      - The name of the timestamp field used for time-based visualizations.
    type: str
  name:
    description:
      - A human-readable name for the data view.
    type: str
  source_filters:
    description:
      - List of field names to exclude from the data view.
    type: list
    elements: dict
  field_formats:
    description:
      - Dictionary of field format overrides keyed by field name.
    type: dict
  runtime_field_map:
    description:
      - Dictionary of runtime fields keyed by field name.
    type: dict
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Kibana data view
  stevefulme1.elastic.kibana_data_view:
    title: "logs-*"
    time_field_name: "@timestamp"
    name: "My Logs"
    state: present
  register: result

- name: Update a Kibana data view
  stevefulme1.elastic.kibana_data_view:
    data_view_id: "{{ result.data_view.id }}"
    title: "logs-*"
    name: "My Logs Updated"
    state: present

- name: Delete a Kibana data view
  stevefulme1.elastic.kibana_data_view:
    data_view_id: "my-data-view-id"
    state: absent
"""

RETURN = r"""
data_view:
  description: The data view object returned by the API after create or update.
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of a Kibana data view via GET."""
    data_view_id = module.params.get("data_view_id")
    if data_view_id is None:
        # Without an ID, try to find by title in the list
        title = module.params.get("title")
        if title is None:
            return None
        try:
            response = client.get("/api/data_views")
            items = response.get("data_view", []) if isinstance(response, dict) else []
            for item in items:
                if item.get("title") == title:
                    return item
            return None
        except ClientError:
            return None
    try:
        response = client.get("/api/data_views/data_view/{0}".format(data_view_id))
        if isinstance(response, dict):
            return response.get("data_view", response)
        return response
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
    """Build the data view payload from module params."""
    payload = {}

    param_map = {
        "title": "title",
        "time_field_name": "timeFieldName",
        "name": "name",
        "source_filters": "sourceFilters",
        "field_formats": "fieldFormats",
        "runtime_field_map": "runtimeFieldMap",
    }

    for param_name, api_key in param_map.items():
        value = module.params.get(param_name)
        if value is not None:
            payload[api_key] = value

    data_view_id = module.params.get("data_view_id")
    if data_view_id is not None:
        payload["id"] = data_view_id

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            data_view_id=dict(type="str"),
            title=dict(type="str"),
            time_field_name=dict(type="str"),
            name=dict(type="str"),
            source_filters=dict(type="list", elements="dict"),
            field_formats=dict(type="dict"),
            runtime_field_map=dict(type="dict"),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        required_if=[
            ("state", "absent", ["data_view_id"]),
        ],
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
                    response = client.post(
                        "/api/data_views/data_view",
                        data={"data_view": desired},
                    )
                    if isinstance(response, dict):
                        result["data_view"] = response.get("data_view", response)
                    else:
                        result["data_view"] = desired

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    dv_id = current.get("id", module.params.get("data_view_id"))
                    response = client.post(
                        "/api/data_views/data_view/{0}".format(dv_id),
                        data={"data_view": desired},
                    )
                    if isinstance(response, dict):
                        result["data_view"] = response.get("data_view", response)
                    else:
                        result["data_view"] = desired

            else:
                # Resource exists and is up-to-date
                result["data_view"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    dv_id = module.params["data_view_id"]
                    client.delete("/api/data_views/data_view/{0}".format(dv_id))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
