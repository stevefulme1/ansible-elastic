#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: data_stream_info
short_description: >-
  Retrieve information about Elasticsearch data streams
version_added: "0.1.0"
description:
  - >-
    Retrieve a single data stream by name,
    or list all data streams.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  name:
    description:
      - The name of the data stream to retrieve.
      - When omitted, all data streams are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific data stream
  stevefulme1.elastic.data_stream_info:
    name: "my-data-stream"
  register: result

- name: List all data streams
  stevefulme1.elastic.data_stream_info:
  register: result
"""

RETURN = r"""
data_streams:
  description: List of data stream resources matching the query.
  returned: always
  type: list
  elements: dict
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


def fetch_single(client, name):
    """Retrieve a single data stream by name."""
    response = client.get("/_data_stream/{0}".format(name))
    if isinstance(response, dict):
        return response.get("data_streams", [])
    return []


def fetch_list(client):
    """List all data streams."""
    response = client.get("/_data_stream")
    if isinstance(response, dict):
        return response.get("data_streams", [])
    return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            name=dict(type="str", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        mutually_exclusive=auth_mutually_exclusive(),
        required_together=auth_required_together(),
        required_one_of=auth_required_one_of(),
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        data_streams=[],
    )

    try:
        client = Client(module)
        name = module.params.get("name")

        if name is not None:
            result["data_streams"] = fetch_single(client, name)
        else:
            result["data_streams"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
