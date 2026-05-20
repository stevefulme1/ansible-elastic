#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module: kibana_space -- GET/POST/PUT/DELETE /api/spaces/space/{id}."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_space
short_description: Manage Kibana spaces for multi-tenancy
description:
    - Create, update, or delete Kibana spaces.
    - Uses the Kibana Spaces API (/api/spaces/space/{id}).
    - Idempotent -- a second run with identical parameters returns changed=False.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    space_id:
        description: Unique identifier for the space.
        type: str
        required: true
    state:
        description: Desired state of the resource.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Display name of the space.
        type: str
    description:
        description: Description of the space.
        type: str
    color:
        description: Hex color code for the space avatar.
        type: str
    disabled_features:
        description: List of feature IDs to disable in this space.
        type: list
        elements: str
    host:
        description: Kibana host (scheme://host:port).
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
"""

EXAMPLES = r"""
- name: Create a Kibana space
  stevefulme1.elastic.kibana_space:
    host: "https://kibana:5601"
    api_key: "{{ kibana_api_key }}"
    space_id: engineering
    name: Engineering
    description: Engineering team workspace
    state: present

- name: Delete a Kibana space
  stevefulme1.elastic.kibana_space:
    host: "https://kibana:5601"
    api_key: "{{ kibana_api_key }}"
    space_id: engineering
    state: absent
"""

RETURN = r"""
space:
    description: The space object.
    returned: on success when state=present
    type: dict
"""

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ApiClient
    HAS_CLIENT = True
except ImportError:
    HAS_CLIENT = False

COMPARE_KEYS = ("name", "description", "color", "disabledFeatures")


def get_current_state(client, space_id):
    """GET /api/spaces/space/{id}, return None if 404."""
    return client.get("space", space_id)


def needs_update(current, desired):
    """Compare current space with desired parameters, return dict of changes."""
    changes = {}
    for key in COMPARE_KEYS:
        if desired.get(key) is not None:
            if current.get(key) != desired[key]:
                changes[key] = desired[key]
    return changes


def build_desired(module):
    """Build desired-state dict from module params."""
    desired = {"id": module.params["space_id"]}
    if module.params.get("name") is not None:
        desired["name"] = module.params["name"]
    if module.params.get("description") is not None:
        desired["description"] = module.params["description"]
    if module.params.get("color") is not None:
        desired["color"] = module.params["color"]
    if module.params.get("disabled_features") is not None:
        desired["disabledFeatures"] = module.params["disabled_features"]
    return desired


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type="str", default="present", choices=["present", "absent"]),
            space_id=dict(type="str", required=True),
            name=dict(type="str"),
            description=dict(type="str"),
            color=dict(type="str"),
            disabled_features=dict(type="list", elements="str"),
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
    state = module.params["state"]
    space_id = module.params["space_id"]

    current = get_current_state(client, space_id)

    if state == "absent":
        if current is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        client.delete("space", space_id)
        module.exit_json(changed=True)
    else:
        desired = build_desired(module)
        if current:
            changes = needs_update(current, desired)
            if not changes:
                module.exit_json(changed=False, space=current)
            if module.check_mode:
                module.exit_json(changed=True, space=current,
                                 diff=dict(before=current, after=changes))
            result = client.update("space", space_id, desired)
            module.exit_json(changed=True, space=result)
        else:
            if module.check_mode:
                module.exit_json(changed=True, space={})
            result = client.create("space", desired)
            module.exit_json(changed=True, space=result)


if __name__ == "__main__":
    main()
