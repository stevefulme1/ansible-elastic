#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_user_info
short_description: Retrieve information about Elasticsearch security users
version_added: "1.0.0"
description:
  - Retrieve a single security user by username, or list all security users.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  username:
    description:
      - The username of the security user to retrieve.
      - When omitted, all security users are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific security user
  stevefulme1.elastic.security_user_info:
    username: "john_doe"
  register: result

- name: List all security users
  stevefulme1.elastic.security_user_info:
  register: result
"""

RETURN = r"""
security_users:
  description: List of security user resources matching the query.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, username):
    """Retrieve a single security user by username."""
    try:
        response = client.get("/_security/user/{0}".format(username))
        if isinstance(response, dict) and username in response:
            user = response[username]
            user["username"] = username
            return user
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List all security users."""
    response = client.get("/_security/user")
    users = []
    if isinstance(response, dict):
        for user_name, user_data in response.items():
            user_data["username"] = user_name
            users.append(user_data)
    return users


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            username=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        security_users=[],
    )

    try:
        client = Client(module)
        username = module.params.get("username")

        if username is not None:
            item = fetch_single(client, username)
            result["security_users"] = [item] if item else []
        else:
            result["security_users"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
