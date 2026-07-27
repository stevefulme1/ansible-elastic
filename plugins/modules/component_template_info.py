#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: component_template_info
short_description: >-
  Retrieve information about Elasticsearch component templates
version_added: "0.1.0"
description:
  - >-
    Retrieve a single component template by name,
    or list all component templates.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  name:
    description:
      - The name of the component template to retrieve.
      - When omitted, all component templates are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific component template
  stevefulme1.elastic.component_template_info:
    name: "my_component_template"
  register: result

- name: List all component templates
  stevefulme1.elastic.component_template_info:
  register: result
"""

RETURN = r"""
component_templates:
  description: List of component template resources matching the query.
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
    """Retrieve a single component template by name."""
    response = client.get("/_component_template/{0}".format(name))
    if isinstance(response, dict):
        return response.get("component_templates", [])
    return []


def fetch_list(client):
    """List all component templates."""
    response = client.get("/_component_template")
    if isinstance(response, dict):
        return response.get("component_templates", [])
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
        component_templates=[],
    )

    try:
        client = Client(module)
        name = module.params.get("name")

        if name is not None:
            result["component_templates"] = fetch_single(client, name)
        else:
            result["component_templates"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
