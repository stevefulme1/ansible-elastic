#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: slm_policy_info
short_description: >-
  Retrieve information about SLM (Snapshot Lifecycle Management) policies
version_added: "1.0.0"
description:
  - >-
    Retrieve a single SLM policy by its identifier,
    or list all SLM policy resources.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  id:
    description:
      - The unique identifier of the SLM policy to retrieve.
      - When omitted, all SLM policies are listed.
    type: str
    required: false
  page:
    description:
      - Page number for paginated results.
      - Only applies when listing resources.
    type: int
    required: false
  page_size:
    description:
      - Number of results per page.
      - Only applies when listing resources.
    type: int
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific SLM policy
  stevefulme1.elastic.slm_policy_info:
    id: "nightly-snapshots"
  register: result

- name: List all SLM policies
  stevefulme1.elastic.slm_policy_info:
  register: result
"""

RETURN = r"""
slm_policies:
  description: List of SLM policy resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    policy:
      description: The policy definition including schedule, repository, and config.
      type: dict
    version:
      description: The policy version number.
      type: int
    modified_date:
      description: The date the policy was last modified.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def fetch_single(client, identifier):
    """Retrieve a single SLM policy by identifier."""
    try:
        response = client.get("/_slm/policy/{0}".format(identifier))
        if isinstance(response, dict) and identifier in response:
            entry = response[identifier]
            entry["name"] = identifier
            return entry
        return None
    except ClientError:
        return None


def fetch_list(client, module):
    """List SLM policy resources."""
    response = client.get("/_slm/policy")
    if isinstance(response, dict):
        items = []
        for name, entry in response.items():
            entry["name"] = name
            items.append(entry)
        return items
    return response if isinstance(response, list) else []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            id=dict(type="str", required=False),
            page=dict(type="int", required=False),
            page_size=dict(type="int", required=False),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("id", "page"),
            ("id", "page_size"),
        ],
    )

    result = dict(
        changed=False,
        slm_policies=[],
    )

    try:
        client = Client(module)
        identifier = module.params.get("id")

        if identifier is not None:
            item = fetch_single(client, identifier)
            result["slm_policies"] = [item] if item else []
        else:
            result["slm_policies"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
