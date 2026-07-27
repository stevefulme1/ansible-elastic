#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: index_template
short_description: Manage Elasticsearch index templates
version_added: "0.1.0"
description:
  - Create, update, and delete index template resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the index template resource.
    type: str
    choices: ['present', 'absent']
    default: present
  name:
    description:
      - Name of the index template.
    type: str
  _meta:
    description:
      - Optional user metadata about the index template. May have any contents.
    type: dict
  allow_auto_create:
    description:
      - >-
        This setting overrides the value of the action.auto_create_index cluster setting. If set to true...
    type: bool
  composed_of:
    description:
      - >-
        An ordered list of component template names. Component templates are merged in the order...
    type: list
    elements: str
  data_stream:
    description:
      - If this object is included, the template is used to create data streams and their backing indices.
    type: dict
  deprecated:
    description:
      - >-
        Marks this index template as deprecated. When creating or updating a non-deprecated index...
    type: bool
  ignore_missing_component_templates:
    description:
      - >-
        The configuration option ignore_missing_component_templates can be used when an index template...
    type: list
    elements: str
  index_patterns:
    description:
      - Array of wildcard expressions used to match the names of data streams and indices during creation.
    type: list
    elements: str
  priority:
    description:
      - >-
        Priority to determine index template precedence when a new data stream or index is created. The...
    type: int
  template:
    description:
      - Template to be applied, including settings, mappings, and aliases configuration.
    type: dict
  version:
    description:
      - Version number used to manage index templates externally.
    type: int
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create an index template
  stevefulme1.elastic.index_template:
    name: "my_template"
    index_patterns:
      - "logs-*"
    state: present
    # API: PUT /_index_template/{name}
- name: Update an index template
  stevefulme1.elastic.index_template:
    name: "my_template"
    index_patterns:
      - "logs-*"
    priority: 100
    composed_of:
      - "component1"
    state: present
    # API: PUT /_index_template/{name}
- name: Delete an index template
  stevefulme1.elastic.index_template:
    name: "my_template"
    state: absent
    # API: DELETE /_index_template/{name}
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
    """Retrieve the current state of the index template via GET."""
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/_index_template/{0}".format(name))
        if isinstance(response, dict):
            templates = response.get("index_templates", [])
            if templates:
                return templates[0].get("index_template", templates[0])
        return response
    except ClientError as e:
        if e.status_code == 404:
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

    if module.params.get("_meta") is not None:
        payload["_meta"] = module.params["_meta"]

    if module.params.get("allow_auto_create") is not None:
        payload["allow_auto_create"] = module.params["allow_auto_create"]

    if module.params.get("composed_of") is not None:
        payload["composed_of"] = module.params["composed_of"]

    if module.params.get("data_stream") is not None:
        payload["data_stream"] = module.params["data_stream"]

    if module.params.get("deprecated") is not None:
        payload["deprecated"] = module.params["deprecated"]

    if module.params.get("ignore_missing_component_templates") is not None:
        payload["ignore_missing_component_templates"] = module.params["ignore_missing_component_templates"]

    if module.params.get("index_patterns") is not None:
        payload["index_patterns"] = module.params["index_patterns"]

    if module.params.get("priority") is not None:
        payload["priority"] = module.params["priority"]

    if module.params.get("template") is not None:
        payload["template"] = module.params["template"]

    if module.params.get("version") is not None:
        payload["version"] = module.params["version"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            name=dict(
                type="str",
            ),

            _meta=dict(
                type="dict",
            ),

            allow_auto_create=dict(
                type="bool",
            ),

            composed_of=dict(
                type="list",
                elements="str",
            ),

            data_stream=dict(
                type="dict",
            ),

            deprecated=dict(
                type="bool",
            ),

            ignore_missing_component_templates=dict(
                type="list",
                elements="str",
            ),

            index_patterns=dict(
                type="list",
                elements="str",
            ),

            priority=dict(
                type="int",
            ),

            template=dict(
                type="dict",
            ),

            version=dict(
                type="int",
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
            ("state", "present", ("name",)),
            ("state", "absent", ("name",)),
        ],
    )

    state = module.params["state"]
    result = dict(changed=False, diff=dict(before={}, after={}))

    try:
        client = Client(module)
        current = get_current_state(client, module)
        name = module.params["name"]

        if state == "present":
            desired = build_payload(module)

            if current is None:
                # Resource does not exist — create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    response = client.put(
                        "/_index_template/{0}".format(name),
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
                        "/_index_template/{0}".format(name),
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
                    client.delete("/_index_template/{0}".format(name))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
