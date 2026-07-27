#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: snapshot_repository_info
short_description: Retrieve information about Elasticsearch snapshot repositories
version_added: "0.2.0"
description:
  - Retrieve a single snapshot repository by name, or list all repositories.
  - This module always reports C(changed=False).
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  repository:
    description:
      - The name of the snapshot repository to retrieve.
      - When omitted, all snapshot repositories are listed.
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Get a specific snapshot repository
  stevefulme1.elastic.snapshot_repository_info:
    repository: "my_backup_repo"
  register: result

- name: List all snapshot repositories
  stevefulme1.elastic.snapshot_repository_info:
  register: result
"""

RETURN = r"""
snapshot_repositories:
  description: List of snapshot repository resources matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    type:
      description: The repository type (fs, s3, gcs, azure, url, source).
      type: str
    settings:
      description: Repository-specific settings.
      type: dict
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
    """Retrieve a single snapshot repository by name."""
    try:
        response = client.get("/_snapshot/{0}".format(identifier))
        if isinstance(response, dict) and identifier in response:
            entry = response[identifier]
            entry["name"] = identifier
            return entry
        return None
    except ClientError as e:
        if e.status_code == 404:
            return None
        raise


def fetch_list(client):
    """List all snapshot repositories."""
    response = client.get("/_snapshot")
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
            repository=dict(type="str", required=False),
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
        snapshot_repositories=[],
    )

    try:
        client = Client(module)
        identifier = module.params.get("repository")

        if identifier is not None:
            item = fetch_single(client, identifier)
            result["snapshot_repositories"] = [item] if item else []
        else:
            result["snapshot_repositories"] = fetch_list(client)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
