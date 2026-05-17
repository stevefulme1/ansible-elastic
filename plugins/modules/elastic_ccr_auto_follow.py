#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""elastic_ccr_auto_follow module."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: elastic_ccr_auto_follow
short_description: Manage Elasticsearch CCR auto-follow patterns
description:
    - Manage Elasticsearch cross-cluster replication auto-follow patterns.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    state:
        description: Desired state of the resource.
        type: str
        default: present
        choices: [present, absent]
    host:
        description: API host address.
        type: str
        required: true
    pattern_name:
        description: Unique identifier of the auto-follow pattern.
        type: str
    name:
        description: Display name.
        type: str
    username:
        description: Authentication username.
        type: str
    password:
        description: Authentication password.
        type: str
    api_key:
        description: API key for authentication.
        type: str
    validate_certs:
        description: Validate SSL certificates.
        type: bool
        default: true
"""

EXAMPLES = r"""
- name: Create a CCR auto-follow pattern
  stevefulme1.elastic.elastic_ccr_auto_follow:
    host: api.example.com
    name: my-auto-follow
    state: present

- name: Delete a CCR auto-follow pattern
  stevefulme1.elastic.elastic_ccr_auto_follow:
    host: api.example.com
    pattern_name: "example-id"
    state: absent
"""

RETURN = r"""
ccr_auto_follow:
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
            pattern_name=dict(type="str"),
            name=dict(type="str"),
            host=dict(type="str", required=True),
            username=dict(type="str"),
            password=dict(type="str", no_log=True),
            api_key=dict(type="str", no_log=True),
            validate_certs=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
        required_if=[("state", "absent", ("pattern_name",))],
    )

    if not HAS_CLIENT:
        module.fail_json(msg="Required Python libraries not found.")

    client = ApiClient(module)
    state = module.params["state"]
    resource_id = module.params.get("pattern_name")

    if state == "present":
        if resource_id:
            result = client.update("ccr_auto_follow", resource_id, module.params)
        else:
            if module.check_mode:
                module.exit_json(changed=True)
            result = client.create("ccr_auto_follow", module.params)
        module.exit_json(changed=True, ccr_auto_follow=result)
    else:
        if module.check_mode:
            module.exit_json(changed=True)
        client.delete("ccr_auto_follow", resource_id)
        module.exit_json(changed=True)


if __name__ == "__main__":
    main()
