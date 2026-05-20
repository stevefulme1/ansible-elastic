#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Auto-generated
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: index_template
short_description: Manage indices
version_added: "1.0.0"
description:
  - Create, update, and delete _index_template resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Auto-generated"
options:
  state:
    description:
      - Desired state of the _index_template resource.
    type: str
    choices: ['present', 'absent']
    default: present

  _meta:
    description:
      - >-
        
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





  data_stream:
    description:
      - >-
        
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





  index_patterns:
    description:
      - >-
        
    type: str





  priority:
    description:
      - >-
        Priority to determine index template precedence when a new data stream or index is created. The...
    type: float





  template:
    description:
      - >-
        
    type: dict





  version:
    description:
      - >-
        
    type: float





extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""

- name: Create a _index_template
  stevefulme1.elastic._index_template:





















    state: present
  # API: POST /_index_template/{name}



- name: Update a _index_template
  stevefulme1.elastic._index_template:
    id: "existing_id"


    _meta: "updated__meta"



    allow_auto_create: "updated_allow_auto_create"



    composed_of: "updated_composed_of"



    data_stream: "updated_data_stream"



    deprecated: "updated_deprecated"



    ignore_missing_component_templates: "updated_ignore_missing_component_templates"



    index_patterns: "updated_index_patterns"



    priority: "updated_priority"



    template: "updated_template"



    version: "updated_version"


    state: present
  # API:  



- name: Delete a _index_template
  stevefulme1.elastic._index_template:
    id: "existing_id"
    state: absent
  # API: DELETE /_index_template/{name}

"""

RETURN = r"""

index_templates:
  description: >-
    
  returned: success
  type: list


"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of the _index_template via GET."""

    # No single-resource GET endpoint; fall back to list + filter
    identifier = module.params.get("id")

    search_key = "id"
    search_value = identifier

    if search_value is None:
        return None
    try:
        items = client.get("/_index_template")
        if isinstance(items, dict):
            items = items.get("results", items.get("data", items.get("items", [])))
        for item in items:
            if str(item.get(search_key)) == str(search_value):
                return item
            if str(item.get("id")) == str(search_value):
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

            _meta=dict(
                type="dict",





            ),

            allow_auto_create=dict(
                type="bool",





            ),

            composed_of=dict(
                type="list",





            ),

            data_stream=dict(
                type="dict",





            ),

            deprecated=dict(
                type="bool",





            ),

            ignore_missing_component_templates=dict(
                type="list",





            ),

            index_patterns=dict(
                type="str",





            ),

            priority=dict(
                type="float",





            ),

            template=dict(
                type="dict",





            ),

            version=dict(
                type="float",





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

                    response = client.POST(
                        "/_index_template/{name}",
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})


            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:

                    identifier = current.get("id")
                    path = "".replace(
                        "{id}", str(identifier)
                    )
                    response = client.put(
                        path,
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})


            else:
                # Resource exists and is up-to-date

                result["index_templates"] = current.get("index_templates")


        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:

                    identifier = current.get("id")
                    path = "/_index_template/{name}".replace(
                        "{id}", str(identifier)
                    )
                    client.delete(path)


    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
