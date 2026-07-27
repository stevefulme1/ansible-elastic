#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: query_rule
short_description: Manage Elasticsearch query rulesets
version_added: "0.1.0"
description:
  - Create, update, and delete query rule resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the query rule resource.
    type: str
    choices: ['present', 'absent']
    default: present
  ruleset_id:
    description:
      - The unique identifier of the query ruleset.
    type: str
  rules:
    description:
      - >-
        The list of rules that make up the query ruleset.
    type: list
    elements: dict
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a query ruleset
  stevefulme1.elastic.query_rule:
    ruleset_id: "my_ruleset"
    rules:
      - rule_id: "rule1"
        type: "pinned"
        criteria:
          - type: "exact"
            metadata: "query_string"
            values: ["test"]
        actions:
          ids: ["id1"]
    state: present
    # API: PUT /_query_rules/{ruleset_id}
- name: Delete a query ruleset
  stevefulme1.elastic.query_rule:
    ruleset_id: "my_ruleset"
    state: absent
    # API: DELETE /_query_rules/{ruleset_id}
"""

RETURN = r"""
api_response:
  description: Raw API response from Elasticsearch.
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
    auth_mutually_exclusive,
    auth_required_one_of,
    auth_required_together,
)


def get_current_state(client, module):
    """Retrieve the current state of the query ruleset via GET."""
    ruleset_id = module.params.get("ruleset_id")
    if ruleset_id is None:
        return None
    try:
        return client.get("/_query_rules/{0}".format(ruleset_id))
    except ClientError as e:
        if "404" in str(e) or "not_found" in str(e).lower():
            return None
        raise


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

    if module.params.get("rules") is not None:
        payload["rules"] = module.params["rules"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            ruleset_id=dict(
                type="str",
            ),

            rules=dict(
                type="list",
                elements="dict",
            ),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        mutually_exclusive=auth_mutually_exclusive(),
        required_together=auth_required_together(),
        required_one_of=auth_required_one_of(),
        supports_check_mode=True,
        required_if=[
            ("state", "present", ("ruleset_id", "rules")),
            ("state", "absent", ("ruleset_id",)),
        ],
    )

    state = module.params["state"]
    result = dict(changed=False, diff=dict(before={}, after={}))

    try:
        client = Client(module)
        current = get_current_state(client, module)
        ruleset_id = module.params["ruleset_id"]

        if state == "present":
            desired = build_payload(module)

            if current is None:
                # Resource does not exist — create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    response = client.put(
                        "/_query_rules/{0}".format(ruleset_id),
                        data=desired,
                    )
                    result["api_response"] = response if isinstance(response, dict) else {}

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    response = client.put(
                        "/_query_rules/{0}".format(ruleset_id),
                        data=desired,
                    )
                    result["api_response"] = response if isinstance(response, dict) else {}

            else:
                # Resource exists and is up-to-date
                result["api_response"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    client.delete("/_query_rules/{0}".format(ruleset_id))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
