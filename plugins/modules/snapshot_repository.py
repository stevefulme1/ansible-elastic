#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: snapshot_repository
short_description: Manage snapshot repositories
version_added: "1.0.0"
description:
  - Create, update, and delete snapshot repository resources in Elasticsearch.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the snapshot repository resource.
    type: str
    choices: ['present', 'absent']
    default: present
  repository:
    description:
      - The unique name of the snapshot repository.
    type: str
    required: true
  type:
    description:
      - >-
        The repository type. Required when creating a new repository.
        Common types include C(fs) for shared filesystem, C(url) for
        read-only URL, C(s3) for AWS S3, C(gcs) for Google Cloud Storage,
        C(azure) for Azure Blob Storage, and C(source) for source-only.
    type: str
    choices: ['fs', 'url', 'source', 's3', 'gcs', 'azure']
  settings:
    description:
      - >-
        Repository-specific settings. The required settings depend on the
        repository type. For C(fs), C(location) is required. For C(s3),
        C(bucket) is required.
    type: dict
  verify:
    description:
      - >-
        Whether to verify the repository after creation or update.
        When set to C(true), Elasticsearch verifies that all nodes can
        connect to the repository.
    type: bool
    default: true
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a filesystem snapshot repository
  stevefulme1.elastic.snapshot_repository:
    repository: "my_backup_repo"
    type: "fs"
    settings:
      location: "/mount/backups/my_backup_repo"
      compress: true
    state: present

- name: Create an S3 snapshot repository
  stevefulme1.elastic.snapshot_repository:
    repository: "s3_backup_repo"
    type: "s3"
    settings:
      bucket: "my-elasticsearch-backups"
      region: "us-east-1"
    state: present

- name: Delete a snapshot repository
  stevefulme1.elastic.snapshot_repository:
    repository: "my_backup_repo"
    state: absent
"""

RETURN = r"""
acknowledged:
  description: Whether the request was acknowledged by Elasticsearch.
  returned: success
  type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of the snapshot repository via GET."""
    repository = module.params.get("repository")
    if repository is None:
        return None
    try:
        response = client.get("/_snapshot/{0}".format(repository))
        # Response is keyed by repository name
        if isinstance(response, dict) and repository in response:
            return response[repository]
        return None
    except ClientError:
        return None


def needs_update(current, desired):
    """Compare current state against desired params and return True if an update is needed."""
    if current is None:
        return True
    for key, value in desired.items():
        if value is None:
            continue
        current_value = current.get(key)
        if current_value != value:
            return True
    return False


def build_payload(module):
    """Build the API request payload from module params."""
    payload = {}

    if module.params.get("type") is not None:
        payload["type"] = module.params["type"]

    if module.params.get("settings") is not None:
        payload["settings"] = module.params["settings"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            repository=dict(
                type="str",
                required=True,
            ),
            type=dict(
                type="str",
                choices=["fs", "url", "source", "s3", "gcs", "azure"],
            ),
            settings=dict(
                type="dict",
            ),
            verify=dict(
                type="bool",
                default=True,
            ),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    state = module.params["state"]
    repository = module.params["repository"]
    verify = module.params["verify"]
    result = dict(changed=False, diff=dict(before={}, after={}))

    try:
        client = Client(module)
        current = get_current_state(client, module)

        if state == "present":
            desired = build_payload(module)

            if current is None:
                # Resource does not exist - create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    params = {}
                    if not verify:
                        params["verify"] = "false"
                    response = client.put(
                        "/_snapshot/{0}".format(repository),
                        data=desired,
                        params=params if params else None,
                    )
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    params = {}
                    if not verify:
                        params["verify"] = "false"
                    response = client.put(
                        "/_snapshot/{0}".format(repository),
                        data=desired,
                        params=params if params else None,
                    )
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date
                pass

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    client.delete("/_snapshot/{0}".format(repository))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
