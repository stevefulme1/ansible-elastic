#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: enrich_policy
short_description: Manage Elasticsearch enrich policies
version_added: "1.0.0"
description:
  - Create and delete Elasticsearch enrich policy resources.
  - Enrich policies are immutable. Changes require delete and recreate.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  name:
    description:
      - Name of the enrich policy.
    type: str
  state:
    description:
      - Desired state of the enrich policy resource.
    type: str
    choices: ['present', 'absent']
    default: present
  execute:
    description:
      - Whether to execute the enrich policy after creation.
    type: bool
    default: false
  geo_match:
    description:
      - Geo-match enrich policy definition.
    type: dict
  match:
    description:
      - Match enrich policy definition.
    type: dict
  range:
    description:
      - Range enrich policy definition.
    type: dict
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create an enrich policy
  stevefulme1.elastic.enrich_policy:
    name: "my-enrich-policy"
    match:
      indices: "my-index"
      match_field: "email"
      enrich_fields:
        - "first_name"
        - "last_name"
    state: present

- name: Create and execute an enrich policy
  stevefulme1.elastic.enrich_policy:
    name: "my-enrich-policy"
    match:
      indices: "my-index"
      match_field: "email"
      enrich_fields:
        - "first_name"
        - "last_name"
    execute: true
    state: present

- name: Delete an enrich policy
  stevefulme1.elastic.enrich_policy:
    name: "my-enrich-policy"
    state: absent
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
    """Retrieve the current state of the enrich policy via GET."""
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/_enrich/policy/{0}".format(name))
        if isinstance(response, dict):
            policies = response.get("policies", [])
            if policies:
                return policies[0]
        return None
    except ClientError as e:
        if e.status_code == 404:
            return None
        raise


def needs_update(current, desired):
    """Compare current state against desired params and return True if an update is needed."""
    if current is None:
        return True
    current_config = current.get("config", {})
    for key, value in desired.items():
        if value is None:
            continue
        current_value = current_config.get(key)
        if current_value != value:
            return True
    return False


def build_payload(module):
    """Build the API request payload from module params."""
    payload = {}

    if module.params.get("geo_match") is not None:
        payload["geo_match"] = module.params["geo_match"]

    if module.params.get("match") is not None:
        payload["match"] = module.params["match"]

    if module.params.get("range") is not None:
        payload["range"] = module.params["range"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            name=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            execute=dict(type="bool", default=False),
            geo_match=dict(type="dict"),
            match=dict(type="dict"),
            range=dict(type="dict"),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        mutually_exclusive=auth_mutually_exclusive() + [
            ("geo_match", "match", "range"),
        ],
        required_together=auth_required_together(),
        required_one_of=auth_required_one_of(),
        required_if=[
            ["state", "present", ["name"]],
            ["state", "absent", ["name"]],
        ],
        supports_check_mode=True,
    )

    state = module.params["state"]
    name = module.params["name"]
    result = dict(changed=False, diff=dict(before={}, after={}))

    try:
        client = Client(module)
        current = get_current_state(client, module)

        if state == "present":
            desired = build_payload(module)

            if current is None:
                # Resource does not exist -- create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    response = client.put(
                        "/_enrich/policy/{0}".format(name),
                        data=desired,
                    )
                    result["api_response"] = response

                    if module.params.get("execute"):
                        client.post("/_enrich/policy/{0}/_execute".format(name))

            elif needs_update(current, desired):
                # Enrich policies are immutable -- delete and recreate
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = desired

                if not module.check_mode:
                    client.delete("/_enrich/policy/{0}".format(name))
                    response = client.put(
                        "/_enrich/policy/{0}".format(name),
                        data=desired,
                    )
                    result["api_response"] = response

                    if module.params.get("execute"):
                        client.post("/_enrich/policy/{0}/_execute".format(name))

            else:
                # Resource exists and is up-to-date
                result["api_response"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    client.delete("/_enrich/policy/{0}".format(name))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
