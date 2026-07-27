#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: synonym_info
short_description: >-
  Retrieve information about Elasticsearch synonym sets
version_added: "1.0.0"
description:
  - >-
    Retrieve a single synonym set by its identifier,
    or list all synonym set resources.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  id:
    description:
      - The unique identifier of the synonym set to retrieve.
      - When omitted, all synonym set resources are listed.
    type: str
    required: false
  from:
    description:
      - Starting offset for paginated results.
      - Only applies when listing resources.
    type: int
    required: false
  size:
    description:
      - Number of results to return.
      - Only applies when listing resources.
    type: int
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific synonym set
  stevefulme1.elastic.synonym_info:
    id: "example_id"
  register: result
- name: List all synonym set resources
  stevefulme1.elastic.synonym_info:
  register: result
- name: List synonym set resources with pagination
  stevefulme1.elastic.synonym_info:
    from: 0
    size: 50
  register: result
"""

RETURN = r"""
synonyms:
  description: List of synonym set resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    synonyms_set:
      description: >-
        The identifier of the synonym set.
      type: str
    count:
      description: >-
        Number of synonym rules that the synonym set contains.
      type: int
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


def fetch_single(client, identifier):
    """Retrieve a single synonym set by identifier."""
    return client.get("/_synonyms/{0}".format(identifier))


def fetch_list(client, module):
    """List synonym set resources with optional pagination."""
    params = {}

    from_param = module.params.get("from")
    size_param = module.params.get("size")

    if from_param is not None:
        params["from"] = from_param
    if size_param is not None:
        params["size"] = size_param

    response = client.get("/_synonyms", params=params)
    if isinstance(response, dict):
        return response.get("results", [])
    return response if isinstance(response, list) else []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            id=dict(type="str", required=False),
            **{"from": dict(type="int", required=False)},
            size=dict(type="int", required=False),
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
        synonyms=[],
    )

    try:
        client = Client(module)
        identifier = module.params.get("id")

        if identifier is not None:
            item = fetch_single(client, identifier)
            result["synonyms"] = [item] if item else []
        else:
            result["synonyms"] = fetch_list(client, module)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
