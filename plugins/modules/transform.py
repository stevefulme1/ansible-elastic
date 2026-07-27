#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: transform
short_description: Manage Elasticsearch transforms
version_added: "0.1.0"
description:
  - Create, update, and delete transform resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the transform resource.
    type: str
    choices: ['present', 'absent']
    default: present
  id:
    description:
      - The unique identifier of the transform.
    type: str
  dest:
    description:
      - >-
        The destination for the transform.
    type: dict
  source:
    description:
      - >-
        The source of the data for the transform.
    type: dict
  _meta:
    description:
      - Optional metadata about the transform. May have any contents.
    type: dict
  description:
    description:
      - >-
        Free text description of the transform.
    type: str
  frequency:
    description:
      - The interval between checks for changes in the source indices. Defaults to C(1m).
    type: str
  latest:
    description:
      - The latest function configuration for the transform. Mutually exclusive with C(pivot).
    type: dict
  pivot:
    description:
      - The pivot function configuration defining group_by and aggregations. Mutually exclusive with C(latest).
    type: dict
  retention_policy:
    description:
      - Defines a retention policy for the transform to delete old data from the destination index.
    type: dict
  settings:
    description:
      - >-
        Defines optional transform settings.
    type: dict
  sync:
    description:
      - Defines the properties transforms require to run continuously (continuous transforms).
    type: dict
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a transform
  stevefulme1.elastic.transform:
    id: "my_transform"
    dest:
      index: "dest_index"
    source:
      index:
        - "source_index"
    pivot:
      group_by:
        customer_id:
          terms:
            field: "customer_id"
      aggregations:
        max_price:
          max:
            field: "price"
    state: present
    # API: PUT /_transform/{id}
- name: Update a transform
  stevefulme1.elastic.transform:
    id: "my_transform"
    description: "updated_description"
    state: present
    # API: POST /_transform/{id}/_update
- name: Delete a transform
  stevefulme1.elastic.transform:
    id: "my_transform"
    state: absent
    # API: DELETE /_transform/{id}
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
    """Retrieve the current state of the transform via GET."""
    identifier = module.params.get("id")
    if identifier is None:
        return None
    try:
        response = client.get("/_transform/{0}".format(identifier))
        if isinstance(response, dict):
            transforms = response.get("transforms", [])
            if transforms:
                return transforms[0]
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

            id=dict(
                type="str",
            ),

            dest=dict(
                type="dict",
            ),

            source=dict(
                type="dict",
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
        mutually_exclusive=auth_mutually_exclusive(),
        required_together=auth_required_together(),
        required_one_of=auth_required_one_of(),
        supports_check_mode=True,
        required_if=[
            ("state", "present", ("id",)),
            ("state", "absent", ("id",)),
        ],
    )

    state = module.params["state"]
    result = dict(changed=False, diff=dict(before={}, after={}))

    try:
        client = Client(module)
        current = get_current_state(client, module)
        identifier = module.params["id"]

        if state == "present":
            desired = build_payload(module)

            if current is None:
                # Resource does not exist — create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    response = client.put(
                        "/_transform/{0}".format(identifier),
                        data=desired,
                    )
                    result["api_response"] = response if isinstance(response, dict) else {}

            elif needs_update(current, desired):
                # Resource exists but needs updating — use POST _update
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    response = client.post(
                        "/_transform/{0}/_update".format(identifier),
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
                    client.delete("/_transform/{0}".format(identifier))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
