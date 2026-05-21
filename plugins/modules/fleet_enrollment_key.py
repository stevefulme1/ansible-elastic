#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: fleet_enrollment_key
short_description: Manage Fleet enrollment API keys
version_added: "1.0.0"
description:
  - Create and delete Fleet enrollment API key resources.
  - Enrollment keys cannot be updated; only create and delete are supported.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the enrollment key.
    type: str
    choices: ['present', 'absent']
    default: present
  key_id:
    description:
      - The unique identifier for the enrollment key.
      - Required when deleting an enrollment key.
    type: str
  name:
    description:
      - The display name for the enrollment key.
    type: str
  policy_id:
    description:
      - The agent policy ID this enrollment key belongs to.
      - Required when creating an enrollment key.
    type: str
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Fleet enrollment key
  stevefulme1.elastic.fleet_enrollment_key:
    name: "My Enrollment Key"
    policy_id: "my-agent-policy-id"
    state: present
  register: result

- name: Delete a Fleet enrollment key
  stevefulme1.elastic.fleet_enrollment_key:
    key_id: "my-key-id"
    state: absent
"""

RETURN = r"""
enrollment_key:
  description: The enrollment key object returned by the API after create.
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
    """Retrieve the current state of a Fleet enrollment key via GET."""
    key_id = module.params.get("key_id")
    if key_id is not None:
        try:
            response = client.get("/api/fleet/enrollment_api_keys/{0}".format(key_id))
            return response.get("item", response)
        except ClientError:
            return None
    # Try to find by name in the list
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/api/fleet/enrollment_api_keys")
        items = response.get("items", []) if isinstance(response, dict) else response
        for item in items:
            if item.get("name") == name:
                return item
        return None
    except ClientError:
        return None


def build_payload(module):
    """Build the API request payload from module params."""
    payload = {}

    if module.params.get("name") is not None:
        payload["name"] = module.params["name"]

    if module.params.get("policy_id") is not None:
        payload["policy_id"] = module.params["policy_id"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            key_id=dict(type="str"),
            name=dict(type="str"),
            policy_id=dict(type="str"),
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
            if current is not None:
                # Enrollment keys cannot be updated; already exists
                result["enrollment_key"] = current
            else:
                # Resource does not exist - create it
                desired = build_payload(module)
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    response = client.post("/api/fleet/enrollment_api_keys", data=desired)
                    item = response.get("item", response) if isinstance(response, dict) else desired
                    result["enrollment_key"] = item

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    k_id = current.get("id", module.params.get("key_id"))
                    client.delete("/api/fleet/enrollment_api_keys/{0}".format(k_id))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
