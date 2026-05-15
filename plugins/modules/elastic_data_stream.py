#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)

"""Ansible module: elastic_data_stream."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: elastic_data_stream
short_description: Manage Elasticsearch data streams
description:
    - Manage Elasticsearch data streams in Elastic.
    - Supports create, update, and delete operations.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    state:
        description: Desired state of the resource.
        type: str
        default: present
        choices: [present, absent]
    stream_name:
        description: Unique identifier of the data stream.
        type: str
    name:
        description: Display name of the data stream.
        type: str
"""

EXAMPLES = r"""
- name: Create a data stream
  stevefulme1.elastic.elastic_data_stream:
    name: my-data-stream
    state: present

- name: Delete a data stream
  stevefulme1.elastic.elastic_data_stream:
    stream_name: "example-id"
    state: absent
"""

RETURN = r"""
data_stream:
    description: Resource details.
    returned: on success
    type: dict
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
            state=dict(type="str", default="present", choices=["present", "absent"]),
            stream_name=dict(type="str"),
            name=dict(type="str"),
            host=dict(type="str", required=True),
            username=dict(type="str"),
            password=dict(type="str", no_log=True),
            api_key=dict(type="str", no_log=True),
            validate_certs=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
        required_if=[
            ("state", "absent", ("stream_name",)),
        ],
    )

    if not HAS_CLIENT:
        module.fail_json(msg="Required Python libraries not found.")

    client = ApiClient(module)
    state = module.params["state"]
    resource_id = module.params.get("stream_name")

    if state == "present":
        if resource_id:
            result = client.update("data_stream", resource_id, module.params)
        else:
            if module.check_mode:
                module.exit_json(changed=True)
            result = client.create("data_stream", module.params)
        module.exit_json(changed=True, data_stream=result)
    else:
        if module.check_mode:
            module.exit_json(changed=True)
        client.delete("data_stream", resource_id)
        module.exit_json(changed=True)


if __name__ == "__main__":
    main()
