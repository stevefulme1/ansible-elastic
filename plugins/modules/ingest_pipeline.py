#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Auto-generated
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ingest_pipeline
short_description: Manage ingest
version_added: "1.0.0"
description:
  - Create, update, and delete _ingest_pipeline resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Auto-generated"
options:
  state:
    description:
      - Desired state of the _ingest_pipeline resource.
    type: str
    choices: ['present', 'absent']
    default: present

  _meta:
    description:
      - >-
        
    type: dict





  deprecated:
    description:
      - >-
        Marks this ingest pipeline as deprecated. When a deprecated ingest pipeline is referenced as the...
    type: bool



    default: false



  description:
    description:
      - >-
        Description of the ingest pipeline.
    type: str





  field_access_pattern:
    description:
      - >-
        
    type: str


    choices: ["classic", "flexible"]




  on_failure:
    description:
      - >-
        Processors to run immediately after a processor failure. Each processor supports a...
    type: list





  processors:
    description:
      - >-
        Processors used to perform transformations on documents before indexing. Processors run...
    type: list





  version:
    description:
      - >-
        
    type: float





extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""


- name: Update a _ingest_pipeline
  stevefulme1.elastic._ingest_pipeline:
    id: "existing_id"


    _meta: "updated__meta"



    deprecated: "updated_deprecated"



    description: "updated_description"



    field_access_pattern: "updated_field_access_pattern"



    on_failure: "updated_on_failure"



    processors: "updated_processors"



    version: "updated_version"


    state: present
  # API:  



- name: Delete a _ingest_pipeline
  stevefulme1.elastic._ingest_pipeline:
    id: "existing_id"
    state: absent
  # API: DELETE /_ingest/pipeline/{id}

"""

RETURN = r"""

acknowledged:
  description: >-
    For a successful response, this value is always true. On failure, an exception is returned instead.
  returned: success
  type: bool


"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of the _ingest_pipeline via GET."""

    # No single-resource GET endpoint; fall back to list + filter
    identifier = module.params.get("id")

    search_key = "id"
    search_value = identifier

    if search_value is None:
        return None
    try:
        items = client.get("/_ingest/pipeline")
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

    if module.params.get("deprecated") is not None:
        payload["deprecated"] = module.params["deprecated"]

    if module.params.get("description") is not None:
        payload["description"] = module.params["description"]

    if module.params.get("field_access_pattern") is not None:
        payload["field_access_pattern"] = module.params["field_access_pattern"]

    if module.params.get("on_failure") is not None:
        payload["on_failure"] = module.params["on_failure"]

    if module.params.get("processors") is not None:
        payload["processors"] = module.params["processors"]

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

            deprecated=dict(
                type="bool",



                default=False,



            ),

            description=dict(
                type="str",





            ),

            field_access_pattern=dict(
                type="str",


                choices=['classic', 'flexible'],




            ),

            on_failure=dict(
                type="list",





            ),

            processors=dict(
                type="list",





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

                result["acknowledged"] = current.get("acknowledged")


        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:

                    identifier = current.get("id")
                    path = "/_ingest/pipeline/{id}".replace(
                        "{id}", str(identifier)
                    )
                    client.delete(path)


    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
