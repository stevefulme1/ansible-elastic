#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module: elastic_ilm_policy -- GET/PUT/DELETE /_ilm/policy/{name}."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: elastic_ilm_policy
short_description: Manage Elasticsearch ILM policies
description:
    - Create, update, or delete Index Lifecycle Management policies.
    - Uses the Elasticsearch ILM API (/_ilm/policy/{name}).
    - Idempotent -- a second run with identical parameters returns changed=False.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    policy_name:
        description: Name of the ILM policy.
        type: str
        required: true
    state:
        description: Desired state of the resource.
        type: str
        default: present
        choices: [present, absent]
    policy:
        description:
            - The ILM policy definition containing phases.
            - Required when state=present.
        type: dict
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
        description: Whether to validate SSL certificates.
        type: bool
        default: true
"""

EXAMPLES = r"""
- name: Create an ILM policy
  stevefulme1.elastic.elastic_ilm_policy:
    host: "https://elasticsearch:9200"
    api_key: "{{ elastic_api_key }}"
    policy_name: my-lifecycle-policy
    policy:
      phases:
        hot:
          actions:
            rollover:
              max_size: 50gb
              max_age: 30d
        delete:
          min_age: 90d
          actions:
            delete: {}
    state: present

- name: Delete an ILM policy
  stevefulme1.elastic.elastic_ilm_policy:
    host: "https://elasticsearch:9200"
    api_key: "{{ elastic_api_key }}"
    policy_name: my-lifecycle-policy
    state: absent
"""

RETURN = r"""
ilm_policy:
    description: The ILM policy definition as returned by the API.
    returned: on success when state=present
    type: dict
"""

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ApiClient
    HAS_CLIENT = True
except ImportError:
    HAS_CLIENT = False


def get_current_state(client, policy_name):
    """GET /_ilm/policy/{name}, return None if 404."""
    return client.get("ilm_policy", policy_name)


def needs_update(current, desired_policy):
    """Compare current policy phases with desired, return True if different."""
    if not desired_policy:
        return False
    current_policy = current.get("policy", {})
    current_phases = current_policy.get("phases", {})
    desired_phases = desired_policy.get("phases", {})
    return current_phases != desired_phases


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type="str", default="present", choices=["present", "absent"]),
            policy_name=dict(type="str", required=True),
            policy=dict(type="dict"),
            host=dict(type="str", required=True),
            username=dict(type="str"),
            password=dict(type="str", no_log=True),
            api_key=dict(type="str", no_log=True),
            validate_certs=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
        required_if=[
            ("state", "present", ("policy",)),
        ],
    )

    if not HAS_CLIENT:
        module.fail_json(msg="Required Python libraries not found.")

    client = ApiClient(module)
    state = module.params["state"]
    policy_name = module.params["policy_name"]
    desired_policy = module.params.get("policy")

    current = get_current_state(client, policy_name)

    if state == "absent":
        if current is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        client.delete("ilm_policy", policy_name)
        module.exit_json(changed=True)
    else:
        if current:
            if not needs_update(current, desired_policy):
                module.exit_json(changed=False, ilm_policy=current)
            if module.check_mode:
                module.exit_json(changed=True, ilm_policy=current,
                                 diff=dict(before=current, after=desired_policy))
            result = client.update("ilm_policy", policy_name, {"policy": desired_policy})
            module.exit_json(changed=True, ilm_policy=result)
        else:
            if module.check_mode:
                module.exit_json(changed=True, ilm_policy={})
            result = client.create("ilm_policy", {"policy": desired_policy})
            module.exit_json(changed=True, ilm_policy=result)


if __name__ == "__main__":
    main()
