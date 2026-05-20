#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_case
short_description: Manage Kibana cases
version_added: "1.0.0"
description:
  - Create, update, and delete Kibana case resources.
  - Supports check mode and diff mode for safe operations.
  - Update requires the C(version) from the existing case for optimistic concurrency control.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the case resource.
    type: str
    choices: ['present', 'absent']
    default: present
  case_id:
    description:
      - The unique identifier of the case.
      - Required when updating or deleting an existing case.
    type: str
  title:
    description:
      - The title of the case.
    type: str
    required: true
  description:
    description:
      - The description of the case.
      - Required when creating a new case.
    type: str
  tags:
    description:
      - List of tags associated with the case.
    type: list
    elements: str
  severity:
    description:
      - The severity level of the case.
    type: str
    choices: ['low', 'medium', 'high', 'critical']
    default: medium
  connector:
    description:
      - The connector configuration for the case.
      - >-
        Defaults to C({"id": "none", "name": "none", "type": ".none", "fields": null})
        when creating a new case.
    type: dict
  settings:
    description:
      - The settings for the case.
      - 'Defaults to C({"syncAlerts": true}) when creating a new case.'
    type: dict
  owner:
    description:
      - The owner of the case.
    type: str
    default: cases
  status:
    description:
      - The status of the case.
    type: str
    choices: ['open', 'in-progress', 'closed']
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a case
  stevefulme1.elastic.kibana_case:
    title: "Server Down"
    description: "Production server unresponsive"
    tags:
      - incident
    severity: medium
    state: present

- name: Update a case
  stevefulme1.elastic.kibana_case:
    case_id: "existing_id"
    title: "Server Down - Resolved"
    description: "Production server recovered"
    status: closed
    state: present

- name: Delete a case
  stevefulme1.elastic.kibana_case:
    case_id: "existing_id"
    title: "unused"
    state: absent
"""

RETURN = r"""
id:
  description: The unique identifier of the case.
  returned: success
  type: str
title:
  description: The title of the case.
  returned: success
  type: str
version:
  description: The version of the case (used for optimistic concurrency).
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
    """Retrieve the current state of the case via GET."""
    identifier = module.params.get("case_id")

    if identifier is None:
        return None
    try:
        response = client.get("/api/cases/{0}".format(identifier))
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


def build_payload(module, for_create=True):
    """Build the API request payload from module params."""
    payload = {}

    if module.params.get("title") is not None:
        payload["title"] = module.params["title"]

    if module.params.get("description") is not None:
        payload["description"] = module.params["description"]

    if module.params.get("tags") is not None:
        payload["tags"] = module.params["tags"]

    if module.params.get("severity") is not None:
        payload["severity"] = module.params["severity"]

    if module.params.get("status") is not None:
        payload["status"] = module.params["status"]

    if module.params.get("connector") is not None:
        payload["connector"] = module.params["connector"]
    elif for_create:
        payload["connector"] = {
            "id": "none",
            "name": "none",
            "type": ".none",
            "fields": None,
        }

    if module.params.get("settings") is not None:
        payload["settings"] = module.params["settings"]
    elif for_create:
        payload["settings"] = {"syncAlerts": True}

    if module.params.get("owner") is not None:
        payload["owner"] = module.params["owner"]
    elif for_create:
        payload["owner"] = "cases"

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            case_id=dict(type="str"),
            title=dict(type="str", required=True),
            description=dict(type="str"),
            tags=dict(type="list", elements="str"),
            severity=dict(
                type="str",
                choices=["low", "medium", "high", "critical"],
                default="medium",
            ),
            connector=dict(type="dict"),
            settings=dict(type="dict"),
            owner=dict(type="str", default="cases"),
            status=dict(
                type="str",
                choices=["open", "in-progress", "closed"],
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
            if current is None:
                # Resource does not exist -- create it
                desired = build_payload(module, for_create=True)
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    response = client.post(
                        "/api/cases",
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            else:
                desired = build_payload(module, for_create=False)
                if needs_update(current, desired):
                    # Resource exists but needs updating
                    result["changed"] = True
                    result["diff"]["before"] = current
                    result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                    if not module.check_mode:
                        identifier = current.get("id")
                        version = current.get("version")
                        update_body = dict(desired)
                        update_body["id"] = identifier
                        update_body["version"] = version
                        response = client.patch(
                            "/api/cases",
                            data={"cases": [update_body]},
                        )
                        if isinstance(response, list) and len(response) > 0:
                            result.update(response[0])
                        elif isinstance(response, dict):
                            result.update(response)

                else:
                    # Resource exists and is up-to-date
                    pass

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    identifier = current.get("id")
                    client._request(
                        "DELETE",
                        "/api/cases",
                        data={"ids": [identifier]},
                    )

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
