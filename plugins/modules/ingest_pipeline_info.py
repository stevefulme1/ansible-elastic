#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ingest_pipeline_info
short_description: >-
  Retrieve information about Elasticsearch ingest pipelines
version_added: "0.1.0"
description:
  - >-
    Retrieve a single ingest pipeline by its identifier,
    or list all ingest pipelines.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  id:
    description:
      - The identifier of the ingest pipeline to retrieve.
      - When omitted, all ingest pipelines are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific ingest pipeline
  stevefulme1.elastic.ingest_pipeline_info:
    id: "my-pipeline"
  register: result

- name: List all ingest pipelines
  stevefulme1.elastic.ingest_pipeline_info:
  register: result
"""

RETURN = r"""
ingest_pipelines:
  description: List of ingest pipeline resources matching the query.
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


def fetch_single(client, identifier):
    """Retrieve a single ingest pipeline by identifier."""
    response = client.get("/_ingest/pipeline/{0}".format(identifier))
    # ES returns a dict keyed by pipeline ID
    if isinstance(response, dict) and identifier in response:
        pipeline = response[identifier]
        pipeline["id"] = identifier
        return [pipeline]
    return []


def fetch_list(client):
    """List all ingest pipelines."""
    response = client.get("/_ingest/pipeline")
    # ES returns a dict keyed by pipeline ID
    if isinstance(response, dict):
        pipelines = []
        for pid, pdata in response.items():
            if isinstance(pdata, dict):
                pdata["id"] = pid
                pipelines.append(pdata)
        return pipelines
    return []


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            id=dict(type="str", required=False),
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
        ingest_pipelines=[],
    )

    try:
        client = Client(module)
        identifier = module.params.get("id")

        if identifier is not None:
            result["ingest_pipelines"] = fetch_single(client, identifier)
        else:
            result["ingest_pipelines"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
