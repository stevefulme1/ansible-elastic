#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: connector
short_description: Manage connector
version_added: "1.0.0"
description:
  - Create, update, and delete connector resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the connector resource.
    type: str
    choices: ['present', 'absent']
    default: present
  description:
    description:
      - >-
    type: str
  index_name:
    description:
      - >-
    type: str
  is_native:
    description:
      - >-
    type: bool
  language:
    description:
      - >-
    type: str
  name:
    description:
      - >-
    type: str
  service_type:
    description:
      - >-
    type: str
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a connector
  stevefulme1.elastic.connector:
    state: present
    # API: POST /_connector
- name: Update a connector
  stevefulme1.elastic.connector:
    id: "existing_id"
    description: "updated_description"
    index_name: "updated_index_name"
    is_native: "updated_is_native"
    language: "updated_language"
    name: "updated_name"
    service_type: "updated_service_type"
    state: present
    # API:
- name: Delete a connector
  stevefulme1.elastic.connector:
    id: "existing_id"
    state: absent
    # API: DELETE /_connector/{connector_id}
"""

RETURN = r"""
api_key_id:
  description: >-
  returned: success
  type: str
api_key_secret_id:
  description: >-
  returned: success
  type: str
configuration:
  description: >-
  returned: success
  type: dict
custom_scheduling:
  description: >-
  returned: success
  type: dict
deleted:
  description: >-
  returned: success
  type: bool
description:
  description: >-
  returned: success
  type: str
error:
  description: >-
  returned: success
  type: str
features:
  description: >-
  returned: success
  type: dict
filtering:
  description: >-
  returned: success
  type: list
id:
  description: >-
  returned: success
  type: str
index_name:
  description: >-
  returned: success
  type: str
is_native:
  description: >-
  returned: success
  type: bool
language:
  description: >-
  returned: success
  type: str
last_access_control_sync_error:
  description: >-
  returned: success
  type: str
last_access_control_sync_scheduled_at:
  description: >-
  returned: success
  type: str
last_access_control_sync_status:
  description: >-
  returned: success
  type: str
last_deleted_document_count:
  description: >-
  returned: success
  type: float
last_incremental_sync_scheduled_at:
  description: >-
  returned: success
  type: str
last_indexed_document_count:
  description: >-
  returned: success
  type: float
last_seen:
  description: >-
  returned: success
  type: str
last_sync_error:
  description: >-
  returned: success
  type: str
last_sync_scheduled_at:
  description: >-
  returned: success
  type: str
last_sync_status:
  description: >-
  returned: success
  type: str
last_synced:
  description: >-
  returned: success
  type: str
name:
  description: >-
  returned: success
  type: str
pipeline:
  description: >-
  returned: success
  type: dict
scheduling:
  description: >-
  returned: success
  type: dict
service_type:
  description: >-
  returned: success
  type: str
status:
  description: >-
  returned: success
  type: str
sync_cursor:
  description: >-
  returned: success
  type: dict
sync_now:
  description: >-
  returned: success
  type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of the connector via GET."""

    # No single-resource GET endpoint; fall back to list + filter
    identifier = module.params.get("id")

    name = module.params.get("name")
    search_key = "name"
    search_value = name if identifier is None else identifier

    if search_value is None:
        return None
    try:
        items = client.get("/_connector")
        if isinstance(items, dict):
            items = items.get("results", items.get("data", items.get("items", [])))
        for item in items:
            if str(item.get(search_key)) == str(search_value):
                return item
            if str(item.get("id")) == str(search_value):
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


def build_payload(module):
    """Build the API request payload from module params."""
    payload = {}

    if module.params.get("description") is not None:
        payload["description"] = module.params["description"]

    if module.params.get("index_name") is not None:
        payload["index_name"] = module.params["index_name"]

    if module.params.get("is_native") is not None:
        payload["is_native"] = module.params["is_native"]

    if module.params.get("language") is not None:
        payload["language"] = module.params["language"]

    if module.params.get("name") is not None:
        payload["name"] = module.params["name"]

    if module.params.get("service_type") is not None:
        payload["service_type"] = module.params["service_type"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            description=dict(
                type="str",







            ),

            index_name=dict(
                type="str",







            ),

            is_native=dict(
                type="bool",







            ),

            language=dict(
                type="str",







            ),

            name=dict(
                type="str",







            ),

            service_type=dict(
                type="str",







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
        current = get_current_state(client, module)

        if state == "present":
            desired = build_payload(module)

            if current is None:
                # Resource does not exist — create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:

                    response = client.POST(
                        "/_connector",
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
                    path = "".replace(
                        "{id}", str(identifier)
                    )
                    response = client.put(
                        path,
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date

                result["api_key_id"] = current.get("api_key_id")

                result["api_key_secret_id"] = current.get("api_key_secret_id")

                result["configuration"] = current.get("configuration")

                result["custom_scheduling"] = current.get("custom_scheduling")

                result["deleted"] = current.get("deleted")

                result["description"] = current.get("description")

                result["error"] = current.get("error")

                result["features"] = current.get("features")

                result["filtering"] = current.get("filtering")

                result["id"] = current.get("id")

                result["index_name"] = current.get("index_name")

                result["is_native"] = current.get("is_native")

                result["language"] = current.get("language")

                result["last_access_control_sync_error"] = current.get("last_access_control_sync_error")

                result["last_access_control_sync_scheduled_at"] = current.get("last_access_control_sync_scheduled_at")

                result["last_access_control_sync_status"] = current.get("last_access_control_sync_status")

                result["last_deleted_document_count"] = current.get("last_deleted_document_count")

                result["last_incremental_sync_scheduled_at"] = current.get("last_incremental_sync_scheduled_at")

                result["last_indexed_document_count"] = current.get("last_indexed_document_count")

                result["last_seen"] = current.get("last_seen")

                result["last_sync_error"] = current.get("last_sync_error")

                result["last_sync_scheduled_at"] = current.get("last_sync_scheduled_at")

                result["last_sync_status"] = current.get("last_sync_status")

                result["last_synced"] = current.get("last_synced")

                result["name"] = current.get("name")

                result["pipeline"] = current.get("pipeline")

                result["scheduling"] = current.get("scheduling")

                result["service_type"] = current.get("service_type")

                result["status"] = current.get("status")

                result["sync_cursor"] = current.get("sync_cursor")

                result["sync_now"] = current.get("sync_now")

                pass

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:

                    identifier = current.get("id")
                    path = "/_connector/{connector_id}".replace(
                        "{id}", str(identifier)
                    )
                    client.delete(path)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
