#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: watcher
short_description: Manage Elasticsearch Watcher watches
version_added: "1.0.0"
description:
  - Create, update, and delete Elasticsearch Watcher watch resources.
  - Supports check mode and diff mode for safe operations.
author:
  - "Steve Fulmer (@stevefulme1)"
options:
  state:
    description:
      - Desired state of the watcher watch resource.
    type: str
    choices: ['present', 'absent']
    default: present
  watch_id:
    description:
      - The unique identifier for the watch.
    type: str
    required: true
  trigger:
    description:
      - The trigger that defines when the watch should execute.
      - Typically contains a schedule definition such as interval or cron.
    type: dict
  input:
    description:
      - The input that loads data into the watch execution context.
      - Commonly uses a search input to query Elasticsearch indices.
    type: dict
  condition:
    description:
      - The condition that determines whether the watch actions should execute.
      - Evaluated against the data loaded by the input.
    type: dict
  actions:
    description:
      - The actions to execute when the watch condition is met.
      - Supports logging, email, webhook, index, and other action types.
    type: dict
  transform:
    description:
      - An optional transform to apply to the watch payload before executing actions.
    type: dict
  throttle_period:
    description:
      - The minimum time between watch executions.
      - Specified as a time value string such as C(10s), C(5m), or C(1h).
    type: str
  metadata:
    description:
      - Optional metadata to attach to the watch.
    type: dict
  active:
    description:
      - Whether the watch is active and should be evaluated on its trigger schedule.
    type: bool
    default: true
extends_documentation_fragment:
  - stevefulme1.elastic.auth
"""

EXAMPLES = r"""
- name: Create a watcher watch
  stevefulme1.elastic.watcher:
    watch_id: "error_monitor"
    trigger:
      schedule:
        interval: "10s"
    input:
      search:
        request:
          indices:
            - "logs"
          body:
            query:
              match:
                status: "error"
    condition:
      compare:
        ctx.payload.hits.total:
          gt: 0
    actions:
      log_error:
        logging:
          text: "Found errors in logs"
    state: present

- name: Update a watcher watch throttle period
  stevefulme1.elastic.watcher:
    watch_id: "error_monitor"
    trigger:
      schedule:
        interval: "30s"
    input:
      search:
        request:
          indices:
            - "logs"
          body:
            query:
              match:
                status: "error"
    condition:
      compare:
        ctx.payload.hits.total:
          gt: 0
    actions:
      log_error:
        logging:
          text: "Found errors in logs"
    throttle_period: "5m"
    state: present

- name: Deactivate a watcher watch
  stevefulme1.elastic.watcher:
    watch_id: "error_monitor"
    active: false
    state: present

- name: Delete a watcher watch
  stevefulme1.elastic.watcher:
    watch_id: "error_monitor"
    state: absent
    # API: DELETE /_watcher/watch/{watch_id}
"""

RETURN = r"""
_id:
  description: The identifier of the watch.
  returned: success
  type: str
_version:
  description: The version of the watch document.
  returned: success
  type: int
created:
  description: Whether the watch was newly created.
  returned: on create
  type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
    Client,
    ClientError,
    argument_spec as auth_argument_spec,
)


def get_current_state(client, module):
    """Retrieve the current state of a watch via GET /_watcher/watch/{watch_id}."""
    watch_id = module.params.get("watch_id")
    if watch_id is None:
        return None
    try:
        response = client.get("/_watcher/watch/{0}".format(watch_id))
        if isinstance(response, dict) and response.get("found", False):
            watch = response.get("watch", {})
            watch["_id"] = response.get("_id", watch_id)
            watch["_version"] = response.get("_version")
            watch["found"] = True
            return watch
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

    if module.params.get("trigger") is not None:
        payload["trigger"] = module.params["trigger"]

    if module.params.get("input") is not None:
        payload["input"] = module.params["input"]

    if module.params.get("condition") is not None:
        payload["condition"] = module.params["condition"]

    if module.params.get("actions") is not None:
        payload["actions"] = module.params["actions"]

    if module.params.get("transform") is not None:
        payload["transform"] = module.params["transform"]

    if module.params.get("throttle_period") is not None:
        payload["throttle_period"] = module.params["throttle_period"]

    if module.params.get("metadata") is not None:
        payload["metadata"] = module.params["metadata"]

    if module.params.get("active") is not None:
        payload["active"] = module.params["active"]

    return payload


def main():
    spec = auth_argument_spec()
    spec.update(
        dict(
            state=dict(type="str", choices=["present", "absent"], default="present"),

            watch_id=dict(
                type="str",
                required=True,
            ),

            trigger=dict(
                type="dict",
            ),

            input=dict(
                type="dict",
            ),

            condition=dict(
                type="dict",
            ),

            actions=dict(
                type="dict",
            ),

            transform=dict(
                type="dict",
            ),

            throttle_period=dict(
                type="str",
            ),

            metadata=dict(
                type="dict",
            ),

            active=dict(
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
                    watch_id = module.params["watch_id"]
                    path = "/_watcher/watch/{0}".format(watch_id)
                    response = client.put(
                        path,
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            elif needs_update(current, desired):
                # Resource exists but needs updating
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = dict(current, **{k: v for k, v in desired.items() if v is not None})

                if not module.check_mode:
                    watch_id = module.params["watch_id"]
                    path = "/_watcher/watch/{0}".format(watch_id)
                    response = client.put(
                        path,
                        data=desired,
                    )
                    result.update(response if isinstance(response, dict) else {})

            else:
                # Resource exists and is up-to-date
                result["_id"] = current.get("_id")
                result["_version"] = current.get("_version")

        elif state == "absent":
            if current is not None:
                result["changed"] = True
                result["diff"]["before"] = current
                result["diff"]["after"] = {}

                if not module.check_mode:
                    watch_id = module.params["watch_id"]
                    path = "/_watcher/watch/{0}".format(watch_id)
                    client.delete(path)

    except ClientError as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
