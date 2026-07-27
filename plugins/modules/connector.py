#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: connector
short_description: Manage Elasticsearch connectors
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
  connector_id:
    description:
      - The unique identifier of the connector.
      - Required for update and delete operations.
    type: str
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
    name: "my_connector"
    service_type: "elastic_connectors"
    state: present
    # API: POST /_connector
- name: Update a connector
  stevefulme1.elastic.connector:
    connector_id: "existing_id"
    description: "updated_description"
    index_name: "updated_index_name"
    name: "updated_name"
    state: present
    # API: PUT /_connector/{connector_id}
- name: Delete a connector
  stevefulme1.elastic.connector:
    connector_id: "existing_id"
    state: absent
    # API: DELETE /_connector/{connector_id}
"""

RETURN = r"""
api_response:
  description: Raw API response from Elasticsearch.
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
    auth_mutually_exclusive,
    auth_required_one_of,
    auth_required_together,
)


def get_current_state(client, module):
    """Retrieve the current state of the connector via GET."""
    connector_id = module.params.get("connector_id")

    if connector_id is not None:
        try:
            return client.get("/_connector/{0}".format(connector_id))
        except ClientError as e:
            if "404" in str(e) or "not_found" in str(e).lower():
                return None
            raise

    # Fall back to list + filter by name
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/_connector")
        if isinstance(response, dict):
            items = response.get("results", [])
        else:
            items = response if isinstance(response, list) else []
        for item in items:
            if str(item.get("name")) == str(name):
                return item
        return None
    except ClientError as e:
        if "404" in str(e) or "not_found" in str(e).lower():
            return None
        raise


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

            connector_id=dict(
                type="str",
            ),

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
        mutually_exclusive=auth_mutually_exclusive(),
        required_together=auth_required_together(),
        required_one_of=auth_required_one_of(),
        supports_check_mode=True,
        required_if=[
            ("state", "absent", ("connector_id",)),
        ],
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
                    response = client.post(
                        "/_connector",
                        data=desired,
                    )
                    result["api_response"] = response if isinstance(response, dict) else {}

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    identifier = module.params.get("connector_id") or current.get("id")
                    response = client.put(
                        "/_connector/{0}".format(identifier),
                        data=desired,
                    )
                    result["api_response"] = response if isinstance(response, dict) else {}

            else:
                # Resource exists and is up-to-date
                result["api_response"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    identifier = module.params.get("connector_id") or current.get("id")
                    client.delete("/_connector/{0}".format(identifier))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
