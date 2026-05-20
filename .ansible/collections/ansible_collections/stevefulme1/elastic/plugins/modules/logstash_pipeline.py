#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: logstash_pipeline
short_description: Manage logstash
version_added: "1.0.0"
description:
  - Create, update, and delete logstash pipeline resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the logstash pipeline resource.
    type: str
    choices: ['present', 'absent']
    default: present
  description:
    description:
      - >-
        A description of the pipeline. This description is not used by Elasticsearch or Logstash.
    type: str
    required: true
  last_modified:
    description:
      - >-
    type: str
    required: true
  pipeline:
    description:
      - >-
        The configuration for the pipeline.
    type: str
    required: true
  pipeline_metadata:
    description:
      - >-
    type: dict
    required: true
  pipeline_settings:
    description:
      - >-
    type: dict
    required: true
  username:
    description:
      - >-
        The user who last updated the pipeline.
    type: str
    required: true
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Update a logstash pipeline
  stevefulme1.elastic.logstash_pipeline:
    id: "existing_id"
    state: present
    # API:
- name: Delete a logstash pipeline
  stevefulme1.elastic.logstash_pipeline:
    id: "existing_id"
    state: absent
    # API: DELETE /_logstash/pipeline/{id}
"""

RETURN = r"""

"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of the logstash pipeline via GET."""

    # No single-resource GET endpoint; fall back to list + filter
    identifier = module.params.get("id")

    search_key = "id"
    search_value = identifier

    if search_value is None:
        return None
    try:
        items = client.get("/_logstash/pipeline")
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

    if module.params.get("description") is not None:
        payload["description"] = module.params["description"]

    if module.params.get("last_modified") is not None:
        payload["last_modified"] = module.params["last_modified"]

    if module.params.get("pipeline") is not None:
        payload["pipeline"] = module.params["pipeline"]

    if module.params.get("pipeline_metadata") is not None:
        payload["pipeline_metadata"] = module.params["pipeline_metadata"]

    if module.params.get("pipeline_settings") is not None:
        payload["pipeline_settings"] = module.params["pipeline_settings"]

    if module.params.get("username") is not None:
        payload["username"] = module.params["username"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            description=dict(
                type="str",


                required=True,






            ),

            last_modified=dict(
                type="str",


                required=True,






            ),

            pipeline=dict(
                type="str",


                required=True,






            ),

            pipeline_metadata=dict(
                type="dict",


                required=True,






            ),

            pipeline_settings=dict(
                type="dict",


                required=True,






            ),

            username=dict(
                type="str",


                required=True,






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

                pass

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:

                    identifier = current.get("id")
                    path = "/_logstash/pipeline/{id}".replace(
                        "{id}", str(identifier)
                    )
                    client.delete(path)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
