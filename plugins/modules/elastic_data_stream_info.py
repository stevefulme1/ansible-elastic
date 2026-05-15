#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module: elastic_data_stream_info."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: elastic_data_stream_info
short_description: Retrieve data stream information
description:
    - Retrieve details about data streams.
    - This is a read-only module.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    host:
        description: API host address.
        type: str
        required: true
    username:
        description: Authentication username.
        type: str
    password:
        description: Authentication password.
        type: str
        no_log: true
    api_key:
        description: API key for authentication.
        type: str
        no_log: true
    validate_certs:
        description: Whether to validate SSL certificates.
        type: bool
        default: true

    stream_name:
        description: The stream name.
        type: str
"""

EXAMPLES = r"""
- name: List all data streams
  stevefulme1.elastic.elastic_data_stream_info:
  register: result

- name: Get a specific data stream
  stevefulme1.elastic.elastic_data_stream_info:
    stream_name: "example-id"
  register: result
"""

RETURN = r"""
data_streams:
    description: List of data stream details.
    returned: always
    type: list
    elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ApiClient
    HAS_CLIENT = True
except ImportError:
    HAS_CLIENT = False


def main():
    module = AnsibleModule(
        argument_spec=dict(
            stream_name=dict(type="str"),
            name=dict(type="str"),
            host=dict(type="str", required=True),
            username=dict(type="str"),
            password=dict(type="str", no_log=True),
            api_key=dict(type="str", no_log=True),
            validate_certs=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )

    if not HAS_CLIENT:
        module.fail_json(msg="Required Python libraries not found.")

    client = ApiClient(module)
    resource_id = module.params.get("stream_name")

    if resource_id:
        result = client.get("data_stream", resource_id)
        resources = [result] if result else []
    else:
        resources = client.list("data_stream", module.params)

    module.exit_json(changed=False, data_streams=resources)


if __name__ == "__main__":
    main()
