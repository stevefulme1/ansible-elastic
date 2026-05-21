#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: security_exception
short_description: Manage Kibana Security exception lists
version_added: "1.0.0"
description:
  - Create, update, and delete Kibana Security exception list resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the exception list resource.
    type: str
    choices: ['present', 'absent']
    default: present
  exception_id:
    description:
      - The internal UUID of the exception list assigned by Elastic.
      - Required when deleting an existing exception list.
    type: str
  list_id:
    description:
      - A user-defined slug identifier for the exception list.
      - Used to look up existing exception lists.
    type: str
  name:
    description:
      - The name of the exception list.
    type: str
  description:
    description:
      - A description of the exception list.
    type: str
  type:
    description:
      - The type of exception list.
    type: str
    choices: ['detection', 'endpoint', 'rule_default']
  namespace_type:
    description:
      - The namespace type for the exception list.
    type: str
    choices: ['single', 'agnostic']
    default: "single"
  tags:
    description:
      - A list of tags to categorize the exception list.
    type: list
    elements: str
    default: []
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create an exception list
  stevefulme1.elastic.security_exception:
    name: "Trusted Processes"
    description: "Processes excluded from detection"
    type: "detection"
    namespace_type: "single"
    list_id: "trusted-processes"
    tags: []
    state: present

- name: Update an exception list
  stevefulme1.elastic.security_exception:
    exception_id: "existing-uuid"
    list_id: "trusted-processes"
    name: "Trusted Processes - Updated"
    description: "Updated list of processes excluded from detection"
    type: "detection"
    state: present

- name: Delete an exception list
  stevefulme1.elastic.security_exception:
    exception_id: "existing-uuid"
    state: absent
"""

RETURN = r"""
id:
  description: The internal UUID of the exception list.
  returned: success
  type: str
list_id:
  description: The user-defined slug identifier of the exception list.
  returned: success
  type: str
name:
  description: The name of the exception list.
  returned: success
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of an exception list."""
    exception_id = module.params.get("exception_id")
    list_id = module.params.get("list_id")

    # Try by list_id first (user-defined slug)
    if list_id is not None:
        try:
            response = client.get(
                "/api/exception_lists",
                params={"list_id": list_id},
            )
            if isinstance(response, dict) and response.get("id"):
                return response
        except ClientError:
            pass

    # Try by exception_id (internal UUID)
    if exception_id is not None:
        try:
            response = client.get(
                "/api/exception_lists",
                params={"id": exception_id},
            )
            if isinstance(response, dict) and response.get("id"):
                return response
        except ClientError:
            pass

    # Try to find by name in the list
    name = module.params.get("name")
    if name is not None:
        try:
            response = client.get("/api/exception_lists/_find")
            items = response.get("data", [])
            for item in items:
                if item.get("name") == name:
                    return item
            return None
        except ClientError:
            return None

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

    if module.params.get("description") is not None:
        payload["description"] = module.params["description"]

    if module.params.get("type") is not None:
        payload["type"] = module.params["type"]

    if module.params.get("namespace_type") is not None:
        payload["namespace_type"] = module.params["namespace_type"]

    if module.params.get("list_id") is not None:
        payload["list_id"] = module.params["list_id"]

    if module.params.get("tags") is not None:
        payload["tags"] = module.params["tags"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            exception_id=dict(
                type="str",
            ),

            list_id=dict(
                type="str",
            ),

            name=dict(
                type="str",
            ),

            description=dict(
                type="str",
            ),

            type=dict(
                type="str",
                choices=["detection", "endpoint", "rule_default"],
            ),

            namespace_type=dict(
                type="str",
                choices=["single", "agnostic"],
                default="single",
            ),

            tags=dict(
                type="list",
                elements="str",
                default=[],
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
                    response = client.post(
                        "/api/exception_lists",
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    update_payload = build_payload(module)
                    update_payload["id"] = current.get("id")
                    if current.get("list_id"):
                        update_payload["list_id"] = current["list_id"]
                    response = client.put(
                        "/api/exception_lists",
                        data=update_payload,
                    )
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date
                result["id"] = current.get("id")
                result["list_id"] = current.get("list_id")
                result["name"] = current.get("name")

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    exc_id = module.params.get("exception_id") or current.get("id")
                    client.delete(
                        "/api/exception_lists",
                        params={"id": exc_id},
                    )

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
