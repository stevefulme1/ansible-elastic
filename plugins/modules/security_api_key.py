#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_api_key
short_description: Manage Elasticsearch API keys
version_added: "1.0.0"
description:
  - Create and delete Elasticsearch API keys.
  - API keys cannot be updated. Use C(state=present) to create a key if it does
    not already exist, and C(state=absent) to delete an existing key.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the API key.
    type: str
    choices: ['present', 'absent']
    default: present
  name:
    description:
      - Name of the API key.
    type: str
    required: true
  id:
    description:
      - The ID of the API key.
      - Required for C(state=absent) when deleting by ID.
    type: str
  expiration:
    description:
      - Expiration time for the API key (e.g. C(1d), C(30d)).
    type: str
  role_descriptors:
    description:
      - Role descriptors for the API key.
    type: dict
  metadata:
    description:
      - Optional metadata attached to the API key.
    type: dict
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create an API key
  stevefulme1.elastic.security_api_key:
    name: "my-api-key"
    expiration: "30d"
    role_descriptors:
      my_role:
        cluster:
          - monitor
    state: present
  register: result

- name: Delete an API key by ID
  stevefulme1.elastic.security_api_key:
    name: "my-api-key"
    id: "{{ result.id }}"
    state: absent
"""

RETURN = r"""
id:
  description: The ID of the API key.
  returned: on create
  type: str
api_key:
  description: The generated API key value. Only returned on creation.
  returned: on create
  type: str
name:
  description: The name of the API key.
  returned: on create
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of the API key via GET."""
    key_id = module.params.get("id")
    name = module.params.get("name")

    try:
        params = {}
        if key_id:
            params["id"] = key_id
        elif name:
            params["name"] = name

        response = client.get("/_security/api_key", params=params)
        api_keys = response.get("api_keys", [])

        # Filter out invalidated keys
        active_keys = [k for k in api_keys if not k.get("invalidated", False)]
        if active_keys:
            return active_keys[0]
        return None
    except ClientError:
        return None


def build_payload(module):
    """Build the API request payload from module params."""
    payload = {}

    payload["name"] = module.params["name"]

    if module.params.get("expiration") is not None:
        payload["expiration"] = module.params["expiration"]

    if module.params.get("role_descriptors") is not None:
        payload["role_descriptors"] = module.params["role_descriptors"]

    if module.params.get("metadata") is not None:
        payload["metadata"] = module.params["metadata"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            name=dict(type="str", required=True),
            id=dict(type="str"),
            expiration=dict(type="str"),
            role_descriptors=dict(type="dict"),
            metadata=dict(type="dict"),
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
            if current is None:
                # API key does not exist - create it
                desired = build_payload(module)
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = {"name": desired["name"]}

                if not module.check_mode:
                    response = client.post(
                        "/_security/api_key",
                        data=desired,
                    )
                    result["id"] = response.get("id")
                    result["api_key"] = response.get("api_key")
                    result["name"] = response.get("name")
            else:
                # API key already exists - no update possible
                result["id"] = current.get("id")
                result["name"] = current.get("name")

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = {"id": current.get("id"), "name": current.get("name")}
                result["diff"]["after"] = {}

                if not module.check_mode:
                    key_id = current.get("id")
                    # DELETE /_security/api_key requires a request body
                    client._request(
                        "DELETE",
                        "/_security/api_key",
                        data={"ids": [key_id]},
                    )

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
