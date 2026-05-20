#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_alerting_rule
short_description: Manage Kibana alerting rules
version_added: "1.0.0"
description:
  - Create, update, and delete Kibana alerting rule resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the alerting rule resource.
    type: str
    choices: ['present', 'absent']
    default: present
  rule_id:
    description:
      - The unique identifier of the alerting rule.
      - Required when updating or deleting an existing rule.
    type: str
  name:
    description:
      - The name of the alerting rule.
    type: str
  rule_type_id:
    description:
      - The type of the alerting rule, such as C(.es-query) or C(.index-threshold).
      - Required when creating a new rule.
    type: str
  consumer:
    description:
      - The application or feature that owns the rule, such as C(alerts) or C(siem).
      - Required when creating a new rule.
    type: str
  schedule:
    description:
      - The schedule for how often the rule should run.
      - 'Specified as a dict with an C(interval) key, e.g. C({"interval": "1m"}).'
    type: dict
  actions:
    description:
      - A list of actions to execute when the rule condition is met.
    type: list
    elements: dict
    default: []
  params:
    description:
      - The parameters for the rule type, such as query, threshold, and index settings.
      - Required when creating a new rule.
    type: dict
  tags:
    description:
      - A list of tags to categorize the alerting rule.
    type: list
    elements: str
    default: []
  enabled:
    description:
      - Whether the alerting rule is enabled and actively evaluating.
    type: bool
    default: true
  throttle:
    description:
      - The throttle interval to limit how often actions are executed.
      - Specified as a time value string such as C(1m), C(5m), or C(1h).
    type: str
  notify_when:
    description:
      - Defines when notifications should be sent.
      - Common values include C(onActionGroupChange), C(onActiveAlert), C(onThrottleInterval).
    type: str
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Kibana alerting rule
  stevefulme1.elastic.kibana_alerting_rule:
    name: "CPU Alert"
    rule_type_id: ".es-query"
    consumer: "alerts"
    schedule:
      interval: "1m"
    params:
      index:
        - "metrics-*"
      timeField: "@timestamp"
      esQuery: '{"query": {"match_all": {}}}'
      threshold:
        - 1000
      thresholdComparator: ">"
    tags:
      - production
    enabled: true
    state: present

- name: Update an alerting rule schedule
  stevefulme1.elastic.kibana_alerting_rule:
    rule_id: "existing-rule-id"
    name: "CPU Alert"
    schedule:
      interval: "5m"
    params:
      index:
        - "metrics-*"
      timeField: "@timestamp"
      esQuery: '{"query": {"match_all": {}}}'
      threshold:
        - 1000
      thresholdComparator: ">"
    state: present

- name: Delete a Kibana alerting rule
  stevefulme1.elastic.kibana_alerting_rule:
    rule_id: "existing-rule-id"
    state: absent
"""

RETURN = r"""
id:
  description: The identifier of the alerting rule.
  returned: success
  type: str
name:
  description: The name of the alerting rule.
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
    """Retrieve the current state of an alerting rule via GET /api/alerting/rule/{id}."""
    rule_id = module.params.get("rule_id")
    if rule_id is None:
        # Try to find by name in the list
        name = module.params.get("name")
        if name is None:
            return None
        try:
            response = client.get("/api/alerting/rules/_find")
            items = response.get("data", [])
            for item in items:
                if item.get("name") == name:
                    return item
            return None
        except ClientError:
            return None

    try:
        response = client.get("/api/alerting/rule/{0}".format(rule_id))
        if isinstance(response, dict) and response.get("id"):
            return response
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


def build_payload(module, for_update=False):
    """Build the API request payload from module params."""
    payload = {}

    if module.params.get("name") is not None:
        payload["name"] = module.params["name"]

    if module.params.get("rule_type_id") is not None and not for_update:
        payload["rule_type_id"] = module.params["rule_type_id"]

    if module.params.get("consumer") is not None and not for_update:
        payload["consumer"] = module.params["consumer"]

    if module.params.get("schedule") is not None:
        payload["schedule"] = module.params["schedule"]

    if module.params.get("actions") is not None:
        payload["actions"] = module.params["actions"]

    if module.params.get("params") is not None:
        payload["params"] = module.params["params"]

    if module.params.get("tags") is not None:
        payload["tags"] = module.params["tags"]

    if module.params.get("enabled") is not None and not for_update:
        payload["enabled"] = module.params["enabled"]

    if module.params.get("throttle") is not None:
        payload["throttle"] = module.params["throttle"]

    if module.params.get("notify_when") is not None:
        payload["notify_when"] = module.params["notify_when"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            rule_id=dict(
                type="str",
            ),

            name=dict(
                type="str",
            ),

            rule_type_id=dict(
                type="str",
            ),

            consumer=dict(
                type="str",
            ),

            schedule=dict(
                type="dict",
            ),

            actions=dict(
                type="list",
                elements="dict",
                default=[],
            ),

            params=dict(
                type="dict",
            ),

            tags=dict(
                type="list",
                elements="str",
                default=[],
            ),

            enabled=dict(
                type="bool",
                default=True,
            ),

            throttle=dict(
                type="str",
            ),

            notify_when=dict(
                type="str",
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
            desired = build_payload(module, for_update=(current is not None))

            if current is None:
                # Resource does not exist - create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    create_payload = build_payload(module, for_update=False)
                    response = client.post(
                        "/api/alerting/rule",
                        data=create_payload,
                    )
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    rule_id = current.get("id")
                    path = "/api/alerting/rule/{0}".format(rule_id)
                    response = client.put(
                        path,
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date
                result["id"] = current.get("id")
                result["name"] = current.get("name")

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    rule_id = module.params.get("rule_id") or current.get("id")
                    path = "/api/alerting/rule/{0}".format(rule_id)
                    client.delete(path)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
