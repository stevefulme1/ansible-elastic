#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ilm_policy
short_description: Manage ILM (Index Lifecycle Management) policies
version_added: "1.0.0"
description:
  - Create, update, and delete ILM policy resources in Elasticsearch.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the ILM policy resource.
    type: str
    choices: ['present', 'absent']
    default: present
  policy_id:
    description:
      - The unique identifier of the ILM policy.
    type: str
    required: true
  phases:
    description:
      - >-
        The lifecycle phases and their actions. Keys may include C(hot), C(warm),
        C(cold), C(frozen), and C(delete). Each phase is a dict defining the
        C(min_age) and C(actions) for that phase.
    type: dict
  _meta:
    description:
      - Optional user metadata to attach to the ILM policy.
    type: dict
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create an ILM policy with hot and delete phases
  stevefulme1.elastic.ilm_policy:
    policy_id: "my_lifecycle_policy"
    phases:
      hot:
        actions:
          rollover:
            max_primary_shard_size: "50gb"
      delete:
        min_age: "30d"
        actions:
          delete: {}
    state: present

- name: Delete an ILM policy
  stevefulme1.elastic.ilm_policy:
    policy_id: "my_lifecycle_policy"
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
    """Retrieve the current state of the ILM policy via GET."""
    policy_id = module.params.get("policy_id")
    if policy_id is None:
        return None
    try:
        response = client.get("/_ilm/policy/{0}".format(policy_id))
        # Response is keyed by policy name
        if isinstance(response, dict) and policy_id in response:
            entry = response[policy_id]
            return entry.get("policy", entry)
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
    policy = {}

    if module.params.get("phases") is not None:
        policy["phases"] = module.params["phases"]

    if module.params.get("_meta") is not None:
        policy["_meta"] = module.params["_meta"]

    return policy


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            policy_id=dict(
                type="str",
                required=True,
            ),
            phases=dict(
                type="dict",
            ),
            _meta=dict(
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
                        "/_ilm/policy/{0}".format(policy_id),
                        data={"policy": desired},
                    )
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    response = client.put(
                        "/_ilm/policy/{0}".format(policy_id),
                        data={"policy": desired},
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
                    client.delete("/_ilm/policy/{0}".format(policy_id))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
