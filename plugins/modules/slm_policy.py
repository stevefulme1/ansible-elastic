#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: slm_policy
short_description: Manage SLM (Snapshot Lifecycle Management) policies
version_added: "1.0.0"
description:
  - Create, update, and delete SLM policy resources in Elasticsearch.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the SLM policy resource.
    type: str
    choices: ['present', 'absent']
    default: present
  policy_id:
    description:
      - The unique identifier of the SLM policy.
    type: str
    required: true
  schedule:
    description:
      - >-
        Periodic or absolute schedule at which the policy creates snapshots.
        SLM applies schedule changes immediately. Uses Cron syntax.
    type: str
  name:
    description:
      - >-
        Name automatically assigned to each snapshot created by the policy.
        Date math is supported. For example C(<nightly-snap-{now/d}>).
    type: str
  repository:
    description:
      - Repository used to store snapshots created by this policy.
      - This repository must exist prior to the policy creation.
    type: str
  config:
    description:
      - >-
        Configuration for each snapshot created by the policy.
        May include C(indices), C(ignore_unavailable),
        C(include_global_state), and other snapshot configuration options.
    type: dict
  retention:
    description:
      - >-
        Retention rules used to retain and delete snapshots created by the
        policy. Supports C(expire_after), C(min_count), and C(max_count).
    type: dict
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create an SLM policy
  stevefulme1.elastic.slm_policy:
    policy_id: "nightly-snapshots"
    schedule: "0 30 1 * * ?"
    name: "<nightly-snap-{now/d}>"
    repository: "my_repository"
    config:
      indices:
        - "*"
      include_global_state: true
    retention:
      expire_after: "30d"
      min_count: 5
      max_count: 50
    state: present

- name: Delete an SLM policy
  stevefulme1.elastic.slm_policy:
    policy_id: "nightly-snapshots"
    state: absent
"""

RETURN = r"""
acknowledged:
  description: Whether the request was acknowledged by Elasticsearch.
  returned: success
  type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of the SLM policy via GET."""
    policy_id = module.params.get("policy_id")
    if policy_id is None:
        return None
    try:
        response = client.get("/_slm/policy/{0}".format(policy_id))
        # Response is keyed by policy name
        if isinstance(response, dict) and policy_id in response:
            return response[policy_id]
        return None
    except ClientError:
        return None


def needs_update(current, desired):
    """Compare current state against desired params and return True if an update is needed."""
    if current is None:
        return True
    # SLM GET returns the policy body nested under "policy"
    current_policy = current.get("policy", current)
    for key, value in desired.items():
        if value is None:
            continue
        current_value = current_policy.get(key)
        if current_value != value:
            return True
    return False


def build_payload(module):
    """Build the API request payload from module params."""
    payload = {}

    if module.params.get("schedule") is not None:
        payload["schedule"] = module.params["schedule"]

    if module.params.get("name") is not None:
        payload["name"] = module.params["name"]

    if module.params.get("repository") is not None:
        payload["repository"] = module.params["repository"]

    if module.params.get("config") is not None:
        payload["config"] = module.params["config"]

    if module.params.get("retention") is not None:
        payload["retention"] = module.params["retention"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            policy_id=dict(
                type="str",
                required=True,
            ),
            schedule=dict(
                type="str",
            ),
            name=dict(
                type="str",
            ),
            repository=dict(
                type="str",
            ),
            config=dict(
                type="dict",
            ),
            retention=dict(
                type="dict",
            ),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    state = module.params["state"]
    policy_id = module.params["policy_id"]
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
                        "/_slm/policy/{0}".format(policy_id),
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    response = client.put(
                        "/_slm/policy/{0}".format(policy_id),
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date
                pass

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    client.delete("/_slm/policy/{0}".format(policy_id))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
