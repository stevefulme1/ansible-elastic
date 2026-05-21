#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_connector
short_description: Manage Kibana connectors (actions)
version_added: "1.0.0"
description:
  - Create, update, and delete Kibana connector (action) resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the connector.
    type: str
    choices: ['present', 'absent']
    default: present
  connector_id:
    description:
      - The unique identifier for the connector.
      - Required when updating or deleting a connector.
    type: str
  name:
    description:
      - The display name for the connector.
      - Required when creating a connector.
    type: str
    required: true
  connector_type_id:
    description:
      - The connector type identifier, for example C(.slack), C(.email), or C(.webhook).
      - Required when creating a connector.
    type: str
  config:
    description:
      - The connector configuration object.
      - Contents vary by connector type.
    type: dict
  secrets:
    description:
      - The connector secrets object.
      - Contents vary by connector type.
      - Values are write-only and never returned by the API.
    type: dict
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Kibana webhook connector
  stevefulme1.elastic.kibana_connector:
    name: "My Webhook"
    connector_type_id: ".webhook"
    config:
      url: "https://example.com/hook"
      method: "post"
    secrets:
      user: "admin"
      password: "secret"
    state: present
  register: result

- name: Update a Kibana connector
  stevefulme1.elastic.kibana_connector:
    connector_id: "{{ result.connector.id }}"
    name: "My Webhook Updated"
    config:
      url: "https://example.com/hook-v2"
      method: "post"
    state: present

- name: Delete a Kibana connector
  stevefulme1.elastic.kibana_connector:
    connector_id: "my-connector-id"
    name: "unused"
    state: absent
"""

RETURN = r"""
connector:
  description: The connector object returned by the API after create or update.
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
    """Retrieve the current state of a Kibana connector via GET."""
    connector_id = module.params.get("connector_id")
    if connector_id is None:
        # Try to find by name in the list
        name = module.params.get("name")
        if name is None:
            return None
        try:
            items = client.get("/api/actions/connectors")
            if isinstance(items, list):
                for item in items:
                    if item.get("name") == name:
                        return item
            return None
        except ClientError:
            return None
    try:
        return client.get("/api/actions/connector/{0}".format(connector_id))
    except ClientError:
        return None


def needs_update(current, desired):
    """Compare current state against desired params and return True if an update is needed."""
    if current is None:
        return True
    for key, value in desired.items():
        if value is None:
            continue
        # Secrets are never returned by the API, so skip comparison
        if key == "secrets":
            continue
        current_value = current.get(key)
        if current_value != value:
            return True
    return False


def build_create_payload(module):
    """Build the API request payload for creating a connector."""
    payload = {}

    if module.params.get("name") is not None:
        payload["name"] = module.params["name"]

    if module.params.get("connector_type_id") is not None:
        payload["connector_type_id"] = module.params["connector_type_id"]

    if module.params.get("config") is not None:
        payload["config"] = module.params["config"]

    if module.params.get("secrets") is not None:
        payload["secrets"] = module.params["secrets"]

    return payload


def build_update_payload(module):
    """Build the API request payload for updating a connector."""
    payload = {}

    if module.params.get("name") is not None:
        payload["name"] = module.params["name"]

    if module.params.get("config") is not None:
        payload["config"] = module.params["config"]

    if module.params.get("secrets") is not None:
        payload["secrets"] = module.params["secrets"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            connector_id=dict(type="str"),
            name=dict(type="str", required=True),
            connector_type_id=dict(type="str"),
            config=dict(type="dict"),
            secrets=dict(type="dict", no_log=True),
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
            if current is None:
                # Resource does not exist - create it
                desired = build_create_payload(module)
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    response = client.post("/api/actions/connector", data=desired)
                    result["connector"] = response if isinstance(response, dict) else desired

            else:
                desired = build_update_payload(module)
                if needs_update(current, desired):
                    # Resource exists but needs updating
                    result["changed"] = True
                    result["diff"]["before"] = current
                    result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                    if not module.check_mode:
                        conn_id = current.get("id", module.params.get("connector_id"))
                        response = client.put(
                            "/api/actions/connector/{0}".format(conn_id),
                            data=desired,
                        )
                        result["connector"] = response if isinstance(response, dict) else desired

                else:
                    # Resource exists and is up-to-date
                    result["connector"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    conn_id = current.get("id", module.params.get("connector_id"))
                    client.delete("/api/actions/connector/{0}".format(conn_id))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
