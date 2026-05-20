#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: fleet_server_host
short_description: Manage Fleet server hosts
version_added: "1.0.0"
description:
  - Create, update, and delete Fleet server host resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the Fleet server host.
    type: str
    choices: ['present', 'absent']
    default: present
  host_id:
    description:
      - The unique identifier for the Fleet server host.
      - Required when updating or deleting a Fleet server host.
    type: str
  name:
    description:
      - The display name for the Fleet server host.
      - Required when creating a Fleet server host.
    type: str
    required: true
  host_urls:
    description:
      - List of Fleet server host URLs.
    type: list
    elements: str
  is_default:
    description:
      - Whether this Fleet server host is the default.
    type: bool
  is_preconfigured:
    description:
      - Whether this Fleet server host is preconfigured.
    type: bool
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Fleet server host
  stevefulme1.elastic.fleet_server_host:
    name: "Fleet Server"
    host_urls:
      - "https://fleet:8220"
    is_default: false
    state: present
  register: result

- name: Update a Fleet server host
  stevefulme1.elastic.fleet_server_host:
    host_id: "{{ result.server_host.id }}"
    name: "Fleet Server Updated"
    host_urls:
      - "https://fleet:8220"
    state: present

- name: Delete a Fleet server host
  stevefulme1.elastic.fleet_server_host:
    host_id: "my-host-id"
    name: "unused"
    state: absent
"""

RETURN = r"""
server_host:
  description: The Fleet server host object returned by the API after create or update.
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
    """Retrieve the current state of a Fleet server host via GET."""
    host_id = module.params.get("host_id")
    if host_id is not None:
        try:
            response = client.get("/api/fleet/fleet_server_hosts/{0}".format(host_id))
            return response.get("item", response)
        except ClientError:
            return None
    # Try to find by name in the list
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/api/fleet/fleet_server_hosts")
        items = response.get("items", []) if isinstance(response, dict) else response
        for item in items:
            if item.get("name") == name:
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

    if module.params.get("name") is not None:
        payload["name"] = module.params["name"]

    if module.params.get("host_urls") is not None:
        payload["host_urls"] = module.params["host_urls"]

    if module.params.get("is_default") is not None:
        payload["is_default"] = module.params["is_default"]

    if module.params.get("is_preconfigured") is not None:
        payload["is_preconfigured"] = module.params["is_preconfigured"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            host_id=dict(type="str"),
            name=dict(type="str", required=True),
            host_urls=dict(type="list", elements="str"),
            is_default=dict(type="bool"),
            is_preconfigured=dict(type="bool"),
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
                    response = client.post("/api/fleet/fleet_server_hosts", data=desired)
                    item = response.get("item", response) if isinstance(response, dict) else desired
                    result["server_host"] = item

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    h_id = current.get("id", module.params.get("host_id"))
                    response = client.put(
                        "/api/fleet/fleet_server_hosts/{0}".format(h_id),
                        data=desired,
                    )
                    item = response.get("item", response) if isinstance(response, dict) else desired
                    result["server_host"] = item

            else:
                # Resource exists and is up-to-date
                result["server_host"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    h_id = current.get("id", module.params.get("host_id"))
                    client.delete("/api/fleet/fleet_server_hosts/{0}".format(h_id))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
