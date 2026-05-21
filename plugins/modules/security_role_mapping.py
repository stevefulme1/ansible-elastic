#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_role_mapping
short_description: Manage Elasticsearch security role mappings
version_added: "1.0.0"
description:
  - Create, update, and delete Elasticsearch security role mappings.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the security role mapping.
    type: str
    choices: ['present', 'absent']
    default: present
  name:
    description:
      - Name of the security role mapping.
    type: str
    required: true
  roles:
    description:
      - A list of roles that are granted to the users matching the role mapping rules.
    type: list
    elements: str
  enabled:
    description:
      - Whether the role mapping is enabled.
    type: bool
    default: true
  rules:
    description:
      - The rules that determine which users should be matched by the mapping.
      - Required when creating a new role mapping.
    type: dict
  metadata:
    description:
      - Optional metadata attached to the role mapping.
    type: dict
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a security role mapping
  stevefulme1.elastic.security_role_mapping:
    name: "my_mapping"
    roles:
      - admin
    enabled: true
    rules:
      field:
        username: "*"
    state: present

- name: Delete a security role mapping
  stevefulme1.elastic.security_role_mapping:
    name: "my_mapping"
    state: absent
"""

RETURN = r"""
role_mapping:
  description: The security role mapping object returned by the API.
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
    """Retrieve the current state of the security role mapping via GET."""
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/_security/role_mapping/{0}".format(name))
        if isinstance(response, dict) and name in response:
            return response[name]
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

    if module.params.get("roles") is not None:
        payload["roles"] = module.params["roles"]

    if module.params.get("enabled") is not None:
        payload["enabled"] = module.params["enabled"]

    if module.params.get("rules") is not None:
        payload["rules"] = module.params["rules"]

    if module.params.get("metadata") is not None:
        payload["metadata"] = module.params["metadata"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            name=dict(type="str", required=True),
            roles=dict(type="list", elements="str"),
            enabled=dict(type="bool", default=True),
            rules=dict(type="dict"),
            metadata=dict(type="dict"),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    state = module.params["state"]
    name = module.params["name"]
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
                result["diff"]["after"] = desired

                if not module.check_mode:
                    response = client.put(
                        "/_security/role_mapping/{0}".format(name),
                        data=desired,
                    )
                    result["role_mapping"] = desired
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    response = client.put(
                        "/_security/role_mapping/{0}".format(name),
                        data=desired,
                    )
                    result["role_mapping"] = desired
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date
                result["role_mapping"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    client.delete("/_security/role_mapping/{0}".format(name))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
