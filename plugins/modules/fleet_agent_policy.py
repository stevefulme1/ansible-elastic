#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: fleet_agent_policy
short_description: Manage Fleet agent policies
version_added: "1.0.0"
description:
  - Create, update, and delete Fleet agent policy resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the agent policy.
    type: str
    choices: ['present', 'absent']
    default: present
  policy_id:
    description:
      - The unique identifier for the agent policy.
      - Required when updating or deleting an agent policy.
    type: str
  name:
    description:
      - The display name for the agent policy.
      - Required when creating an agent policy.
    type: str
    required: true
  namespace:
    description:
      - The namespace for the agent policy.
    type: str
    default: default
  description:
    description:
      - A description of the agent policy.
    type: str
  monitoring_enabled:
    description:
      - List of monitoring output types to enable.
    type: list
    elements: str
  is_managed:
    description:
      - Whether the policy is managed by an external orchestrator.
    type: bool
  inactivity_timeout:
    description:
      - Inactivity timeout in seconds.
    type: int
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Fleet agent policy
  stevefulme1.elastic.fleet_agent_policy:
    name: "My Agent Policy"
    namespace: "default"
    description: "Policy for web servers"
    monitoring_enabled:
      - logs
      - metrics
    state: present
  register: result

- name: Update a Fleet agent policy
  stevefulme1.elastic.fleet_agent_policy:
    policy_id: "{{ result.policy.id }}"
    name: "My Agent Policy Updated"
    namespace: "default"
    state: present

- name: Delete a Fleet agent policy
  stevefulme1.elastic.fleet_agent_policy:
    policy_id: "my-policy-id"
    name: "unused"
    state: absent
"""

RETURN = r"""
policy:
  description: The agent policy object returned by the API after create or update.
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
    """Retrieve the current state of a Fleet agent policy via GET."""
    policy_id = module.params.get("policy_id")
    if policy_id is not None:
        try:
            response = client.get("/api/fleet/agent_policies/{0}".format(policy_id))
            return response.get("item", response)
        except ClientError:
            return None
    # Try to find by name in the list
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/api/fleet/agent_policies")
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

    if module.params.get("description") is not None:
        payload["description"] = module.params["description"]

    if module.params.get("monitoring_enabled") is not None:
        payload["monitoring_enabled"] = module.params["monitoring_enabled"]

    if module.params.get("is_managed") is not None:
        payload["is_managed"] = module.params["is_managed"]

    if module.params.get("inactivity_timeout") is not None:
        payload["inactivity_timeout"] = module.params["inactivity_timeout"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            policy_id=dict(type="str"),
            name=dict(type="str", required=True),
            namespace=dict(type="str", default="default"),
            description=dict(type="str"),
            monitoring_enabled=dict(type="list", elements="str"),
            is_managed=dict(type="bool"),
            inactivity_timeout=dict(type="int"),
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
                    response = client.post("/api/fleet/agent_policies", data=desired)
                    item = response.get("item", response) if isinstance(response, dict) else desired
                    result["policy"] = item

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    pol_id = current.get("id", module.params.get("policy_id"))
                    response = client.put(
                        "/api/fleet/agent_policies/{0}".format(pol_id),
                        data=desired,
                    )
                    item = response.get("item", response) if isinstance(response, dict) else desired
                    result["policy"] = item

            else:
                # Resource exists and is up-to-date
                result["policy"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    pol_id = current.get("id", module.params.get("policy_id"))
                    client.post(
                        "/api/fleet/agent_policies/delete",
                        data={"agentPolicyId": pol_id},
                    )

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
