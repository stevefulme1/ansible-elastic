#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: fleet_package_policy
short_description: Manage Fleet package policies
version_added: "1.0.0"
description:
  - Create, update, and delete Fleet package policy resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the package policy.
    type: str
    choices: ['present', 'absent']
    default: present
  package_policy_id:
    description:
      - The unique identifier for the package policy.
      - Required when updating or deleting a package policy.
    type: str
  name:
    description:
      - The display name for the package policy.
      - Required when creating a package policy.
    type: str
    required: true
  namespace:
    description:
      - The namespace for the package policy.
    type: str
    default: default
  policy_id:
    description:
      - The agent policy ID this package policy belongs to.
      - Required when creating a package policy.
    type: str
  package:
    description:
      - The package definition including name and version.
    type: dict
  inputs:
    description:
      - List of input configurations for the package policy.
    type: list
    elements: dict
  description:
    description:
      - A description of the package policy.
    type: str
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Fleet package policy
  stevefulme1.elastic.fleet_package_policy:
    name: "system-1"
    namespace: "default"
    policy_id: "my-agent-policy-id"
    package:
      name: "system"
      version: "1.0.0"
    state: present
  register: result

- name: Update a Fleet package policy
  stevefulme1.elastic.fleet_package_policy:
    package_policy_id: "{{ result.package_policy.id }}"
    name: "system-1-updated"
    namespace: "default"
    policy_id: "my-agent-policy-id"
    package:
      name: "system"
      version: "1.0.0"
    state: present

- name: Delete a Fleet package policy
  stevefulme1.elastic.fleet_package_policy:
    package_policy_id: "my-package-policy-id"
    name: "unused"
    state: absent
"""

RETURN = r"""
package_policy:
  description: The package policy object returned by the API after create or update.
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
    """Retrieve the current state of a Fleet package policy via GET."""
    package_policy_id = module.params.get("package_policy_id")
    if package_policy_id is not None:
        try:
            response = client.get("/api/fleet/package_policies/{0}".format(package_policy_id))
            return response.get("item", response)
        except ClientError:
            return None
    # Try to find by name in the list
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/api/fleet/package_policies")
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

    if module.params.get("namespace") is not None:
        payload["namespace"] = module.params["namespace"]

    if module.params.get("policy_id") is not None:
        payload["policy_id"] = module.params["policy_id"]

    if module.params.get("package") is not None:
        payload["package"] = module.params["package"]

    if module.params.get("inputs") is not None:
        payload["inputs"] = module.params["inputs"]

    if module.params.get("description") is not None:
        payload["description"] = module.params["description"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            package_policy_id=dict(type="str"),
            name=dict(type="str", required=True),
            namespace=dict(type="str", default="default"),
            policy_id=dict(type="str"),
            package=dict(type="dict"),
            inputs=dict(type="list", elements="dict"),
            description=dict(type="str"),
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
                    response = client.post("/api/fleet/package_policies", data=desired)
                    item = response.get("item", response) if isinstance(response, dict) else desired
                    result["package_policy"] = item

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    pkg_id = current.get("id", module.params.get("package_policy_id"))
                    response = client.put(
                        "/api/fleet/package_policies/{0}".format(pkg_id),
                        data=desired,
                    )
                    item = response.get("item", response) if isinstance(response, dict) else desired
                    result["package_policy"] = item

            else:
                # Resource exists and is up-to-date
                result["package_policy"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    pkg_id = current.get("id", module.params.get("package_policy_id"))
                    client.delete("/api/fleet/package_policies/{0}".format(pkg_id))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
