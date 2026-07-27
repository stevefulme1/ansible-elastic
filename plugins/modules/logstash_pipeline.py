#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: logstash_pipeline
short_description: Manage Logstash pipelines via Elasticsearch
version_added: "0.1.0"
description:
  - Create, update, and delete Logstash pipeline resources via the Elasticsearch API.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  id:
    description:
      - Identifier for the Logstash pipeline.
    type: str
  state:
    description:
      - Desired state of the Logstash pipeline resource.
    type: str
    choices: ['present', 'absent']
    default: present
  description:
    description:
      - A description of the pipeline. This description is not used by Elasticsearch or Logstash.
    type: str
  last_modified:
    description:
      - Date the pipeline was last updated, in ISO 8601 format.
    type: str
  pipeline:
    description:
      - The configuration for the pipeline.
    type: str
  pipeline_metadata:
    description:
      - Optional metadata about the pipeline, used by monitoring.
    type: dict
  pipeline_settings:
    description:
      - Settings for the pipeline, such as queue type and batch size.
    type: dict
  username:
    description:
      - The user who last updated the pipeline.
    type: str
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Logstash pipeline
  stevefulme1.elastic.logstash_pipeline:
    id: "my-logstash-pipeline"
    description: "My Logstash pipeline"
    pipeline: 'input { stdin {} } output { stdout {} }'
    pipeline_settings:
      pipeline.batch.size: 125
    state: present

- name: Update a Logstash pipeline
  stevefulme1.elastic.logstash_pipeline:
    id: "my-logstash-pipeline"
    description: "Updated pipeline"
    pipeline: 'input { stdin {} } filter { mutate { add_field => { "foo" => "bar" } } } output { stdout {} }'
    state: present

- name: Delete a Logstash pipeline
  stevefulme1.elastic.logstash_pipeline:
    id: "my-logstash-pipeline"
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
    """Retrieve the current state of the Logstash pipeline via GET."""
    identifier = module.params.get("id")
    if identifier is None:
        return None
    try:
        response = client.get("/_logstash/pipeline/{0}".format(identifier))
        # ES returns a dict keyed by pipeline ID
        if isinstance(response, dict) and identifier in response:
            pipeline = response[identifier]
            pipeline["id"] = identifier
            return pipeline
        return None
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
            id=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            description=dict(type="str"),
            last_modified=dict(type="str"),
            pipeline=dict(type="str"),
            pipeline_metadata=dict(type="dict"),
            pipeline_settings=dict(type="dict"),
            username=dict(type="str"),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        mutually_exclusive=auth_mutually_exclusive(),
        required_together=auth_required_together(),
        required_one_of=auth_required_one_of(),
        required_if=[
            ["state", "present", ["id", "pipeline"]],
            ["state", "absent", ["id"]],
        ],
        supports_check_mode=True,
    )

    state = module.params["state"]
    identifier = module.params["id"]
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
                        "/_logstash/pipeline/{0}".format(identifier),
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
                        "/_logstash/pipeline/{0}".format(identifier),
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
                    client.delete("/_logstash/pipeline/{0}".format(identifier))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
