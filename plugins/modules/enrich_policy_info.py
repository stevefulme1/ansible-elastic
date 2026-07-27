#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: enrich_policy_info
short_description: >-
  Retrieve information about Elasticsearch enrich policies
version_added: "0.1.0"
description:
  - >-
    Retrieve a single enrich policy by name,
    or list all enrich policies.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  name:
    description:
      - The name of the enrich policy to retrieve.
      - When omitted, all enrich policies are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific enrich policy
  stevefulme1.elastic.enrich_policy_info:
    name: "my-enrich-policy"
  register: result

- name: List all enrich policies
  stevefulme1.elastic.enrich_policy_info:
  register: result
"""

RETURN = r"""
enrich_policies:
  description: List of enrich policy resources matching the query.
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
    """Retrieve a single enrich policy by name."""
    response = client.get("/_enrich/policy/{0}".format(name))
    if isinstance(response, dict):
        return response.get("policies", [])
    return []


def fetch_list(client):
    """List all enrich policies."""
    response = client.get("/_enrich/policy")
    if isinstance(response, dict):
        return response.get("policies", [])
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
        enrich_policies=[],
    )

    try:
        client = Client(module)
        name = module.params.get("name")

        if name is not None:
            result["enrich_policies"] = fetch_single(client, name)
        else:
            result["enrich_policies"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
