#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: fleet_output
short_description: Manage Fleet outputs
version_added: "1.0.0"
description:
  - Create, update, and delete Fleet output resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the output.
    type: str
    choices: ['present', 'absent']
    default: present
  output_id:
    description:
      - The unique identifier for the output.
      - Required when updating or deleting an output.
    type: str
  name:
    description:
      - The display name for the output.
      - Required when creating an output.
    type: str
    required: true
  type:
    description:
      - The output type.
    type: str
    choices: ['elasticsearch', 'logstash', 'kafka']
  hosts:
    description:
      - List of host URLs for the output.
    type: list
    elements: str
  is_default:
    description:
      - Whether this output is the default output.
    type: bool
  is_default_monitoring:
    description:
      - Whether this output is the default monitoring output.
    type: bool
  config_yaml:
    description:
      - Additional YAML configuration for the output.
    type: str
  ssl:
    description:
      - SSL configuration for the output.
    type: dict
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Fleet output
  stevefulme1.elastic.fleet_output:
    name: "My ES Output"
    type: "elasticsearch"
    hosts:
      - "https://es:9200"
    is_default: false
    is_default_monitoring: false
    state: present
  register: result

- name: Update a Fleet output
  stevefulme1.elastic.fleet_output:
    output_id: "{{ result.output.id }}"
    name: "My ES Output Updated"
    type: "elasticsearch"
    hosts:
      - "https://es:9200"
    state: present

- name: Delete a Fleet output
  stevefulme1.elastic.fleet_output:
    output_id: "my-output-id"
    name: "unused"
    state: absent
"""

RETURN = r"""
output:
  description: The output object returned by the API after create or update.
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
    """Retrieve the current state of a Fleet output via GET."""
    output_id = module.params.get("output_id")
    if output_id is not None:
        try:
            response = client.get("/api/fleet/outputs/{0}".format(output_id))
            return response.get("item", response)
        except ClientError:
            return None
    # Try to find by name in the list
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/api/fleet/outputs")
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

    if module.params.get("type") is not None:
        payload["type"] = module.params["type"]

    if module.params.get("hosts") is not None:
        payload["hosts"] = module.params["hosts"]

    if module.params.get("is_default") is not None:
        payload["is_default"] = module.params["is_default"]

    if module.params.get("is_default_monitoring") is not None:
        payload["is_default_monitoring"] = module.params["is_default_monitoring"]

    if module.params.get("config_yaml") is not None:
        payload["config_yaml"] = module.params["config_yaml"]

    if module.params.get("ssl") is not None:
        payload["ssl"] = module.params["ssl"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            output_id=dict(type="str"),
            name=dict(type="str", required=True),
            type=dict(type="str", choices=["elasticsearch", "logstash", "kafka"]),
            hosts=dict(type="list", elements="str"),
            is_default=dict(type="bool"),
            is_default_monitoring=dict(type="bool"),
            config_yaml=dict(type="str"),
            ssl=dict(type="dict"),
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
                    response = client.post("/api/fleet/outputs", data=desired)
                    item = response.get("item", response) if isinstance(response, dict) else desired
                    result["output"] = item

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    out_id = current.get("id", module.params.get("output_id"))
                    response = client.put(
                        "/api/fleet/outputs/{0}".format(out_id),
                        data=desired,
                    )
                    item = response.get("item", response) if isinstance(response, dict) else desired
                    result["output"] = item

            else:
                # Resource exists and is up-to-date
                result["output"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    out_id = current.get("id", module.params.get("output_id"))
                    client.delete("/api/fleet/outputs/{0}".format(out_id))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
