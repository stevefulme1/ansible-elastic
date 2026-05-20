#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kibana_space
short_description: Manage Kibana spaces
version_added: "1.0.0"
description:
  - Create, update, and delete Kibana space resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the Kibana space.
    type: str
    choices: ['present', 'absent']
    default: present
  space_id:
    description:
      - The unique identifier for the space.
      - Required when creating, updating, or deleting a space.
    type: str
    required: true
  name:
    description:
      - The display name for the space.
      - Required when creating a space.
    type: str
  description:
    description:
      - A description for the space.
    type: str
  color:
    description:
      - The hexadecimal color code used in the space avatar.
      - Must be a six-digit hex value prefixed with C(#), for example C(#aabbcc).
    type: str
  disabled_features:
    description:
      - List of feature identifiers to disable in the space.
    type: list
    elements: str
  initials:
    description:
      - One or two characters to show in the space avatar.
      - Defaults to the first two characters of the space name.
    type: str
  image_url:
    description:
      - The data-URL encoded image to display as the space avatar.
    type: str
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a Kibana space
  stevefulme1.elastic.kibana_space:
    space_id: "marketing"
    name: "Marketing"
    description: "Marketing team space"
    color: "#aabbcc"
    initials: "MK"
    state: present

- name: Update a Kibana space
  stevefulme1.elastic.kibana_space:
    space_id: "marketing"
    name: "Marketing Updated"
    description: "Updated marketing space"
    state: present

- name: Delete a Kibana space
  stevefulme1.elastic.kibana_space:
    space_id: "marketing"
    state: absent
"""

RETURN = r"""
space:
  description: The space object returned by the API after create or update.
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of a Kibana space via GET."""
    space_id = module.params.get("space_id")
    if space_id is None:
        return None
    try:
        return client.get("/api/spaces/space/{0}".format(space_id))
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

    param_map = {
        "space_id": "id",
        "name": "name",
        "description": "description",
        "color": "color",
        "disabled_features": "disabledFeatures",
        "initials": "initials",
        "image_url": "imageUrl",
    }

    for param_name, api_key in param_map.items():
        value = module.params.get(param_name)
        if value is not None:
            payload[api_key] = value

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),
            space_id=dict(type="str", required=True),
            name=dict(type="str"),
            description=dict(type="str"),
            color=dict(type="str"),
            disabled_features=dict(type="list", elements="str"),
            initials=dict(type="str"),
            image_url=dict(type="str"),
        )
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    state = module.params["state"]
    result = dict(changed=False, diff=dict(before={}, after={}))

    try:
        client = Client(module)
        client.headers["kbn-xsrf"] = "true"
        current = get_current_state(client, module)

        if state == "present":
            desired = build_payload(module)

            if current is None:
                # Resource does not exist - create it
                result["changed"] = True
                result["diff"]["before"] = {}
                result["diff"]["after"] = desired

                if not module.check_mode:
                    response = client.post("/api/spaces/space", data=desired)
                    result["space"] = response if isinstance(response, dict) else desired

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    space_id = module.params["space_id"]
                    response = client.put(
                        "/api/spaces/space/{0}".format(space_id),
                        data=desired,
                    )
                    result["space"] = response if isinstance(response, dict) else desired

            else:
                # Resource exists and is up-to-date
                result["space"] = current

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    space_id = module.params["space_id"]
                    client.delete("/api/spaces/space/{0}".format(space_id))

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
