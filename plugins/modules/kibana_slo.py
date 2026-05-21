#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_slo
short_description: Manage Kibana SLO resources
version_added: "1.0.0"
description:
  - Create, update, and delete Kibana Service Level Objective (SLO) resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the SLO resource.
    type: str
    choices: ['present', 'absent']
    default: present
  slo_id:
    description:
      - The unique identifier of the SLO.
      - Required when updating or deleting an existing SLO.
    type: str
  name:
    description:
      - The name of the SLO.
    type: str
  description:
    description:
      - A description of the SLO.
    type: str
  indicator:
    description:
      - The indicator configuration that defines how the SLO is measured.
      - Contains the type and params for the SLI, such as KQL custom indicator.
      - Required when creating a new SLO.
    type: dict
  time_window:
    description:
      - The time window for the SLO evaluation.
      - Contains C(duration) and C(type) (rolling or calendar).
      - Required when creating a new SLO.
    type: dict
  budgeting_method:
    description:
      - The method used for error budget calculation.
    type: str
    choices: ['occurrences', 'timeslices']
  objective:
    description:
      - The SLO target objective.
      - Contains a C(target) value between 0 and 1, e.g. C(0.99) for 99%.
      - Required when creating a new SLO.
    type: dict
  tags:
    description:
      - A list of tags to categorize the SLO.
    type: list
    elements: str
    default: []
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Kibana SLO
  stevefulme1.elastic.kibana_slo:
    name: "Availability SLO"
    description: "99% availability for web services"
    indicator:
      type: "sli.kql.custom"
      params:
        index: "logs-*"
        good: "status: 200"
        total: "*"
        timestampField: "@timestamp"
    time_window:
      duration: "30d"
      type: "rolling"
    budgeting_method: "occurrences"
    objective:
      target: 0.99
    tags:
      - production
      - web
    state: present

- name: Update an SLO objective
  stevefulme1.elastic.kibana_slo:
    slo_id: "existing-slo-id"
    name: "Availability SLO"
    description: "99.9% availability for web services"
    indicator:
      type: "sli.kql.custom"
      params:
        index: "logs-*"
        good: "status: 200"
        total: "*"
        timestampField: "@timestamp"
    time_window:
      duration: "30d"
      type: "rolling"
    budgeting_method: "occurrences"
    objective:
      target: 0.999
    state: present

- name: Delete an SLO
  stevefulme1.elastic.kibana_slo:
    slo_id: "existing-slo-id"
    state: absent
"""

RETURN = r"""
id:
  description: The identifier of the SLO.
  returned: success
  type: str
name:
  description: The name of the SLO.
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
    """Retrieve the current state of an SLO via GET /api/observability/slos/{id}."""
    slo_id = module.params.get("slo_id")
    if slo_id is None:
        # Try to find by name in the list
        name = module.params.get("name")
        if name is None:
            return None
        try:
            response = client.get("/api/observability/slos")
            items = response.get("results", [])
            for item in items:
                if item.get("name") == name:
                    return item
            return None
        except ClientError:
            return None

    try:
        response = client.get("/api/observability/slos/{0}".format(slo_id))
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


def build_payload(module):
    """Build the API request payload from module params."""
    payload = {}

    if module.params.get("name") is not None:
        payload["name"] = module.params["name"]

    if module.params.get("description") is not None:
        payload["description"] = module.params["description"]

    if module.params.get("indicator") is not None:
        payload["indicator"] = module.params["indicator"]

    if module.params.get("time_window") is not None:
        payload["timeWindow"] = module.params["time_window"]

    if module.params.get("budgeting_method") is not None:
        payload["budgetingMethod"] = module.params["budgeting_method"]

    if module.params.get("objective") is not None:
        payload["objective"] = module.params["objective"]

    if module.params.get("tags") is not None:
        payload["tags"] = module.params["tags"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            slo_id=dict(
                type="str",
            ),

            name=dict(
                type="str",
            ),

            description=dict(
                type="str",
            ),

            indicator=dict(
                type="dict",
            ),

            time_window=dict(
                type="dict",
            ),

            budgeting_method=dict(
                type="str",
                choices=["occurrences", "timeslices"],
            ),

            objective=dict(
                type="dict",
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
                        "/api/observability/slos",
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    slo_id = current.get("id")
                    path = "/api/observability/slos/{0}".format(slo_id)
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
                    slo_id = module.params.get("slo_id") or current.get("id")
                    path = "/api/observability/slos/{0}".format(slo_id)
                    client.delete(path)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
