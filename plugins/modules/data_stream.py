#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: data_stream
short_description: Manage Elasticsearch data streams
version_added: "1.0.0"
description:
  - Create and delete Elasticsearch data stream resources.
  - Data streams are created explicitly via PUT.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  name:
    description:
      - Name of the data stream.
    type: str
  state:
    description:
      - Desired state of the data stream resource.
    type: str
    choices: ['present', 'absent']
    default: present
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a data stream
  stevefulme1.elastic.data_stream:
    name: "my-data-stream"
    state: present

- name: Delete a data stream
  stevefulme1.elastic.data_stream:
    name: "my-data-stream"
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
    """Retrieve the current state of the data stream via GET."""
    name = module.params.get("name")
    if name is None:
        return None
    try:
        response = client.get("/_data_stream/{0}".format(name))
        if isinstance(response, dict):
            streams = response.get("data_streams", [])
            if streams:
                return streams[0]
        return None
    except ClientError as e:
        if e.status_code == 404:
            return None
        raise


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            name=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        mutually_exclusive=auth_mutually_exclusive(),
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
            if current is None:
                # Resource does not exist -- create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = {"name": name}

                if not module.check_mode:
                    response = client.put(
                        "/_data_stream/{0}".format(name),
                    )
                    result["api_response"] = response
            else:
                # Data stream already exists, nothing to update
                result["api_response"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    client.delete("/_data_stream/{0}".format(name))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
