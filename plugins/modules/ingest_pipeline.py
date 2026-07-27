#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ingest_pipeline
short_description: Manage Elasticsearch ingest pipelines
version_added: "0.1.0"
description:
  - Create, update, and delete Elasticsearch ingest pipeline resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  id:
    description:
      - Identifier for the ingest pipeline.
    type: str
  state:
    description:
      - Desired state of the ingest pipeline resource.
    type: str
    choices: ['present', 'absent']
    default: present
  _meta:
    description:
      - Optional metadata about the ingest pipeline.
    type: dict
  deprecated:
    description:
      - >-
        Marks this ingest pipeline as deprecated. When a deprecated ingest pipeline is referenced as the
        default pipeline or final pipeline, Elasticsearch emits a deprecation warning.
    type: bool
    default: false
  description:
    description:
      - Description of the ingest pipeline.
    type: str
  field_access_pattern:
    description:
      - Field access pattern for the pipeline.
    type: str
    choices: ["classic", "flexible"]
  on_failure:
    description:
      - >-
        Processors to run immediately after a processor failure. Each processor supports a
        processor-level on_failure configuration.
    type: list
    elements: dict
  processors:
    description:
      - >-
        Processors used to perform transformations on documents before indexing. Processors run
        sequentially.
    type: list
    elements: dict
  version:
    description:
      - Version number used to manage ingest pipelines externally.
    type: int
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create an ingest pipeline
  stevefulme1.elastic.ingest_pipeline:
    id: "my-pipeline"
    description: "My ingest pipeline"
    processors:
      - set:
          field: "my_field"
          value: "my_value"
    state: present

- name: Update an ingest pipeline
  stevefulme1.elastic.ingest_pipeline:
    id: "my-pipeline"
    description: "Updated pipeline"
    processors:
      - set:
          field: "my_field"
          value: "new_value"
    on_failure:
      - set:
          field: "error_field"
          value: "error occurred"
    state: present

- name: Delete an ingest pipeline
  stevefulme1.elastic.ingest_pipeline:
    id: "my-pipeline"
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
    """Retrieve the current state of the ingest pipeline via GET."""
    identifier = module.params.get("id")
    if identifier is None:
        return None
    try:
        response = client.get("/_ingest/pipeline/{0}".format(identifier))
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
            id=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            _meta=dict(type="dict"),
            deprecated=dict(type="bool", default=False),
            description=dict(type="str"),
            field_access_pattern=dict(type="str", choices=["classic", "flexible"]),
            on_failure=dict(type="list", elements="dict"),
            processors=dict(type="list", elements="dict"),
            version=dict(type="int"),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        mutually_exclusive=auth_mutually_exclusive(),
        required_together=auth_required_together(),
        required_one_of=auth_required_one_of(),
        required_if=[
            ["state", "present", ["id"]],
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
                        "/_ingest/pipeline/{0}".format(identifier),
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
                        "/_ingest/pipeline/{0}".format(identifier),
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
                    client.delete("/_ingest/pipeline/{0}".format(identifier))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
