#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: query_rule
short_description: Manage query_rules
version_added: "1.0.0"
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
  rules:
    description:
      - >-
    type: dict
    required: true
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Update a query rule
  stevefulme1.elastic.query_rule:
    ruleset_id: "existing_id"
    state: present
    # API:
- name: Delete a query rule
  stevefulme1.elastic.query_rule:
    ruleset_id: "existing_id"
    state: absent
    # API: DELETE /_query_rules/{ruleset_id}
"""

RETURN = r"""
ruleset_id:
  description: >-
  returned: success
  type: str
rule_total_count:
  description: >-
    The number of rules associated with the ruleset.
  returned: success
  type: float
rule_criteria_types_counts:
  description: >-
    A map of criteria type (for example, exact) to the number of rules of that type. NOTE: The...
  returned: success
  type: dict
rule_type_counts:
  description: >-
    A map of rule type (for example, pinned) to the number of rules of that type.
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
    """Retrieve the current state of the query rule via GET."""

    # No single-resource GET endpoint; fall back to list + filter
    identifier = module.params.get("ruleset_id")

    search_key = "ruleset_id"
    search_value = identifier

    if search_value is None:
        return None
    try:
        items = client.get("/_query_rules")
        if isinstance(items, dict):
            items = items.get("results", items.get("data", items.get("items", [])))
        for item in items:
            if str(item.get(search_key)) == str(search_value):
                return item
            if str(item.get("ruleset_id")) == str(search_value):
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

    if module.params.get("rules") is not None:
        payload["rules"] = module.params["rules"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            rules=dict(
                type="dict",


                required=True,






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
        current = get_current_state(client, module)

        if state == "present":
            desired = build_payload(module)

            if current is None:
                # Resource does not exist — create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:

                    pass

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:

                    identifier = current.get("ruleset_id")
                    path = "".replace(
                        "{ruleset_id}", str(identifier)
                    )
                    response = client.put(
                        path,
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date

                result["ruleset_id"] = current.get("ruleset_id")

                result["rule_total_count"] = current.get("rule_total_count")

                result["rule_criteria_types_counts"] = current.get("rule_criteria_types_counts")

                result["rule_type_counts"] = current.get("rule_type_counts")

                pass

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:

                    identifier = current.get("ruleset_id")
                    path = "/_query_rules/{ruleset_id}".replace(
                        "{ruleset_id}", str(identifier)
                    )
                    client.delete(path)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
