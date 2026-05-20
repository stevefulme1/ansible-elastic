#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module: elastic_index_template -- GET/PUT/DELETE /_index_template/{name}."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: elastic_index_template
short_description: Manage Elasticsearch index templates
description:
    - Create, update, or delete composable index templates.
    - Uses the Elasticsearch Index Template API (/_index_template/{name}).
    - Idempotent -- a second run with identical parameters returns changed=False.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    template_name:
        description: Name of the index template.
        type: str
        required: true
    state:
        description: Desired state of the resource.
        type: str
        default: present
        choices: [present, absent]
    index_patterns:
        description: List of index patterns the template applies to.
        type: list
        elements: str
    template:
        description: Template settings (mappings, settings, aliases).
        type: dict
    priority:
        description: Template priority (higher takes precedence).
        type: int
    composed_of:
        description: List of component template names.
        type: list
        elements: str
    host:
        description: Elasticsearch host (scheme://host:port).
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
        description: Validate SSL certificates.
        type: bool
        default: true
"""

EXAMPLES = r"""
- name: Create an index template
  stevefulme1.elastic.elastic_index_template:
    host: "https://elasticsearch:9200"
    api_key: "{{ elastic_api_key }}"
    template_name: my-template
    index_patterns:
      - "logs-*"
    template:
      settings:
        number_of_replicas: 1
    state: present

- name: Delete an index template
  stevefulme1.elastic.elastic_index_template:
    host: "https://elasticsearch:9200"
    api_key: "{{ elastic_api_key }}"
    template_name: my-template
    state: absent
"""

RETURN = r"""
index_template:
    description: The index template definition.
    returned: on success when state=present
    type: dict
"""

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ApiClient
    HAS_CLIENT = True
except ImportError:
    HAS_CLIENT = False

COMPARE_KEYS = ("index_patterns", "template", "priority", "composed_of")


def get_current_state(client, template_name):
    """GET /_index_template/{name}, return None if 404."""
    return client.get("index_template", template_name)


def needs_update(current, desired):
    """Compare current template with desired parameters, return dict of changes."""
    changes = {}
    for key in COMPARE_KEYS:
        if desired.get(key) is not None:
            if current.get(key) != desired[key]:
                changes[key] = desired[key]
    return changes


def build_desired(module):
    """Build desired-state dict from module params."""
    desired = {}
    for key in COMPARE_KEYS:
        if module.params.get(key) is not None:
            desired[key] = module.params[key]
    return desired


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type="str", default="present", choices=["present", "absent"]),
            template_name=dict(type="str", required=True),
            index_patterns=dict(type="list", elements="str"),
            template=dict(type="dict"),
            priority=dict(type="int"),
            composed_of=dict(type="list", elements="str"),
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
    template_name = module.params["template_name"]

    current = get_current_state(client, template_name)

    if state == "absent":
        if current is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        client.delete("index_template", template_name)
        module.exit_json(changed=True)
    else:
        desired = build_desired(module)
        if current:
            changes = needs_update(current, desired)
            if not changes:
                module.exit_json(changed=False, index_template=current)
            if module.check_mode:
                module.exit_json(changed=True, index_template=current,
                                 diff=dict(before=current, after=changes))
            result = client.update("index_template", template_name, desired)
            module.exit_json(changed=True, index_template=result)
        else:
            if module.check_mode:
                module.exit_json(changed=True, index_template={})
            result = client.create("index_template", desired)
            module.exit_json(changed=True, index_template=result)


if __name__ == "__main__":
    main()
