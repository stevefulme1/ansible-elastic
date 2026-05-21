#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_role
short_description: Manage Elasticsearch security roles
version_added: "1.0.0"
description:
  - Create, update, and delete Elasticsearch security roles.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the security role.
    type: str
    choices: ['present', 'absent']
    default: present
  name:
    description:
      - Name of the security role.
    type: str
    required: true
  cluster:
    description:
      - A list of cluster privileges.
    type: list
    elements: str
  indices:
    description:
      - A list of indices permissions entries.
      - Each entry is a dict with C(names), C(privileges), and optional
        C(field_security), C(query), and C(allow_restricted_indices) keys.
    type: list
    elements: dict
  applications:
    description:
      - A list of application privilege entries.
    type: list
    elements: dict
  run_as:
    description:
      - A list of users that the owners of this role can impersonate.
    type: list
    elements: str
  metadata:
    description:
      - Optional metadata attached to the role.
    type: dict
  description:
    description:
      - Description of the security role.
    type: str
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a security role
  stevefulme1.elastic.security_role:
    name: "my_role"
    cluster:
      - monitor
    indices:
      - names:
          - "index-*"
        privileges:
          - read
    state: present

- name: Delete a security role
  stevefulme1.elastic.security_role:
    name: "my_role"
    state: absent
"""

RETURN = r"""
role:
  description: The security role object returned by the API.
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
    """Retrieve the current state of the security role via GET."""
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/_security/role/{0}".format(name))
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

    if module.params.get("cluster") is not None:
        payload["cluster"] = module.params["cluster"]

    if module.params.get("indices") is not None:
        payload["indices"] = module.params["indices"]

    if module.params.get("applications") is not None:
        payload["applications"] = module.params["applications"]

    if module.params.get("run_as") is not None:
        payload["run_as"] = module.params["run_as"]

    if module.params.get("metadata") is not None:
        payload["metadata"] = module.params["metadata"]

    if module.params.get("description") is not None:
        payload["description"] = module.params["description"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            name=dict(type="str", required=True),
            cluster=dict(type="list", elements="str"),
            indices=dict(type="list", elements="dict"),
            applications=dict(type="list", elements="dict"),
            run_as=dict(type="list", elements="str"),
            metadata=dict(type="dict"),
            description=dict(type="str"),
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
                        "/_security/role/{0}".format(name),
                        data=desired,
                    )
                    result["role"] = desired
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    response = client.put(
                        "/_security/role/{0}".format(name),
                        data=desired,
                    )
                    result["role"] = desired
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date
                result["role"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    client.delete("/_security/role/{0}".format(name))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
