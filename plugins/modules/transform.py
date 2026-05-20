#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Auto-generated
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: transform
short_description: Manage transform
version_added: "1.0.0"
description:
  - Create, update, and delete _transform resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Auto-generated"
options:
  state:
    description:
      - Desired state of the _transform resource.
    type: str
    choices: ['present', 'absent']
    default: present

  dest:
    description:
      - >-
        
    type: dict

    required: true





  source:
    description:
      - >-
        
    type: dict

    required: true





  _meta:
    description:
      - >-
        
    type: dict





  description:
    description:
      - >-
        Free text description of the transform.
    type: str





  frequency:
    description:
      - >-
        
    type: str





  latest:
    description:
      - >-
        
    type: dict





  pivot:
    description:
      - >-
        
    type: dict





  retention_policy:
    description:
      - >-
        
    type: dict





  settings:
    description:
      - >-
        The source of the data for the transform.
    type: dict





  sync:
    description:
      - >-
        
    type: dict





extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""


- name: Update a _transform
  stevefulme1.elastic._transform:
    id: "existing_id"






    _meta: "updated__meta"



    description: "updated_description"



    frequency: "updated_frequency"



    latest: "updated_latest"



    pivot: "updated_pivot"



    retention_policy: "updated_retention_policy"



    settings: "updated_settings"



    sync: "updated_sync"


    state: present
  # API:  



- name: Delete a _transform
  stevefulme1.elastic._transform:
    id: "existing_id"
    state: absent
  # API: DELETE /_transform/{transform_id}

"""

RETURN = r"""

count:
  description: >-
    
  returned: success
  type: float


transforms:
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
    """Retrieve the current state of the _transform via GET."""

    # No single-resource GET endpoint; fall back to list + filter
    identifier = module.params.get("id")

    search_key = "id"
    search_value = identifier

    if search_value is None:
        return None
    try:
        items = client.get("/_transform")
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

    if module.params.get("dest") is not None:
        payload["dest"] = module.params["dest"]

    if module.params.get("source") is not None:
        payload["source"] = module.params["source"]

    if module.params.get("_meta") is not None:
        payload["_meta"] = module.params["_meta"]

    if module.params.get("description") is not None:
        payload["description"] = module.params["description"]

    if module.params.get("frequency") is not None:
        payload["frequency"] = module.params["frequency"]

    if module.params.get("latest") is not None:
        payload["latest"] = module.params["latest"]

    if module.params.get("pivot") is not None:
        payload["pivot"] = module.params["pivot"]

    if module.params.get("retention_policy") is not None:
        payload["retention_policy"] = module.params["retention_policy"]

    if module.params.get("settings") is not None:
        payload["settings"] = module.params["settings"]

    if module.params.get("sync") is not None:
        payload["sync"] = module.params["sync"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            dest=dict(
                type="dict",

                required=True,





            ),

            source=dict(
                type="dict",

                required=True,





            ),

            _meta=dict(
                type="dict",





            ),

            description=dict(
                type="str",





            ),

            frequency=dict(
                type="str",





            ),

            latest=dict(
                type="dict",





            ),

            pivot=dict(
                type="dict",





            ),

            retention_policy=dict(
                type="dict",





            ),

            settings=dict(
                type="dict",





            ),

            sync=dict(
                type="dict",





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

                result["count"] = current.get("count")

                result["transforms"] = current.get("transforms")


        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:

                    identifier = current.get("id")
                    path = "/_transform/{transform_id}".replace(
                        "{id}", str(identifier)
                    )
                    client.delete(path)


    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
