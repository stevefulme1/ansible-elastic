#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_user
short_description: Manage Elasticsearch security users
version_added: "1.0.0"
description:
  - Create, update, and delete Elasticsearch security users.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the security user.
    type: str
    choices: ['present', 'absent']
    default: present
  username:
    description:
      - Username of the security user.
    type: str
    required: true
  password:
    description:
      - Password for the user.
      - Required when creating a new user.
    type: str
  roles:
    description:
      - A list of roles assigned to the user.
      - Required when creating a new user.
    type: list
    elements: str
  full_name:
    description:
      - Full name of the user.
    type: str
  email:
    description:
      - Email address of the user.
    type: str
  metadata:
    description:
      - Optional metadata attached to the user.
    type: dict
  enabled:
    description:
      - Whether the user account is enabled.
    type: bool
    default: true
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a security user
  stevefulme1.elastic.security_user:
    username: "john_doe"
    password: "s3cret!"
    roles:
      - admin
    full_name: "John Doe"
    email: "john@example.com"
    state: present

- name: Disable a security user
  stevefulme1.elastic.security_user:
    username: "john_doe"
    enabled: false
    state: present

- name: Delete a security user
  stevefulme1.elastic.security_user:
    username: "john_doe"
    state: absent
"""

RETURN = r"""
user:
  description: The security user object returned by the API.
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
    """Retrieve the current state of the security user via GET."""
    username = module.params.get("username")
    if username is None:
        return None
    try:
        response = client.get("/_security/user/{0}".format(username))
        if isinstance(response, dict) and username in response:
            return response[username]
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
        # password is never returned by GET, so skip comparison
        if key == "password":
            continue
        current_value = current.get(key)
        if current_value != value:
            return True
    return False


def build_payload(module):
    """Build the API request payload from module params."""
    payload = {}

    if module.params.get("password") is not None:
        payload["password"] = module.params["password"]

    if module.params.get("roles") is not None:
        payload["roles"] = module.params["roles"]

    if module.params.get("full_name") is not None:
        payload["full_name"] = module.params["full_name"]

    if module.params.get("email") is not None:
        payload["email"] = module.params["email"]

    if module.params.get("metadata") is not None:
        payload["metadata"] = module.params["metadata"]

    if module.params.get("enabled") is not None:
        payload["enabled"] = module.params["enabled"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            username=dict(type="str", required=True),
            password=dict(type="str", no_log=True),
            roles=dict(type="list", elements="str"),
            full_name=dict(type="str"),
            email=dict(type="str"),
            metadata=dict(type="dict"),
            enabled=dict(type="bool", default=True),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    state = module.params["state"]
    username = module.params["username"]
    result = dict(changed=False, diff=dict(before={}, after={}))

    try:
        client = Client(module)
        current = get_current_state(client, module)

        if state == "present":
            desired = build_payload(module)

            if current is None:
                # Resource does not exist - create it
                result["changed"] = True
                result["diff"]["before"] = {}
                # Do not leak password into diff
                safe_desired = {k: v for k, v in desired.items() if k != "password"}
                result["diff"]["after"] = safe_desired

                if not module.check_mode:
                    response = client.put(
                        "/_security/user/{0}".format(username),
                        data=desired,
                    )
                    result["user"] = safe_desired
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                safe_desired = {k: v for k, v in desired.items() if k != "password"}
                result["diff"]["after"] = dict(current, **{k: v for k, v in safe_desired.items() if v is not None})

                if not module.check_mode:
                    response = client.put(
                        "/_security/user/{0}".format(username),
                        data=desired,
                    )
                    result["user"] = dict(current, **{k: v for k, v in safe_desired.items() if v is not None})
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date
                result["user"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    client.delete("/_security/user/{0}".format(username))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
