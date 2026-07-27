#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: component_template
short_description: Manage Elasticsearch component templates
version_added: "0.1.0"
description:
  - Create, update, and delete Elasticsearch component template resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  name:
    description:
      - Name of the component template.
    type: str
  state:
    description:
      - Desired state of the component template resource.
    type: str
    choices: ['present', 'absent']
    default: present
  template:
    description:
      - The template definition including mappings, settings, and aliases.
    type: dict
  _meta:
    description:
      - Optional user metadata about the component template.
    type: dict
  deprecated:
    description:
      - >-
        Marks this index template as deprecated. When creating or updating a non-deprecated index...
    type: bool
  version:
    description:
      - Version number used to manage component templates externally.
    type: int
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a component template
  stevefulme1.elastic.component_template:
    name: "my_component_template"
    template:
      mappings:
        properties:
          timestamp:
            type: date
    state: present

- name: Update a component template
  stevefulme1.elastic.component_template:
    name: "my_component_template"
    template:
      mappings:
        properties:
          timestamp:
            type: date
          message:
            type: text
    _meta:
      description: "updated template"
    state: present

- name: Delete a component template
  stevefulme1.elastic.component_template:
    name: "my_component_template"
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
    """Retrieve the current state of the component template via GET."""
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/_component_template/{0}".format(name))
        if isinstance(response, dict):
            templates = response.get("component_templates", [])
            if templates:
                return templates[0]
        return None
    except ClientError as e:
        if e.status_code == 404:
            return None
        raise


def needs_update(current, desired):
    """Compare current state against desired params and return True if an update is needed."""
    if current is None:
        return True
    current_template = current.get("component_template", {})
    for key, value in desired.items():
        if value is None:
            continue
        current_value = current_template.get(key)
        if current_value != value:
            return True
    return False


def build_payload(module):
    """Build the API request payload from module params."""
    payload = {}

    if module.params.get("template") is not None:
        payload["template"] = module.params["template"]

    if module.params.get("_meta") is not None:
        payload["_meta"] = module.params["_meta"]

    if module.params.get("deprecated") is not None:
        payload["deprecated"] = module.params["deprecated"]

    if module.params.get("version") is not None:
        payload["version"] = module.params["version"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            name=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            template=dict(type="dict"),
            _meta=dict(type="dict"),
            deprecated=dict(type="bool"),
            version=dict(type="int"),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        mutually_exclusive=auth_mutually_exclusive(),
        required_together=auth_required_together(),
        required_one_of=auth_required_one_of(),
        required_if=[
            ["state", "present", ["name", "template"]],
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
                        "/_component_template/{0}".format(name),
                        data=desired,
                    )
                    result["api_response"] = response

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = desired

                if not module.check_mode:
                    response = client.put(
                        "/_component_template/{0}".format(name),
                        data=desired,
                    )
                    result["api_response"] = response

            else:
                # Resource exists and is up-to-date
                result["api_response"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    client.delete("/_component_template/{0}".format(name))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
