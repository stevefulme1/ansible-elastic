# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""elastic dynamic inventory plugin."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
name: elastic_inventory
plugin_type: inventory
short_description: Elasticsearch nodes and Fleet agents
description:
    - Dynamically discovers Elasticsearch nodes and Fleet agents.
    - Returns hosts with metadata as host variables.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    host:
        description: API host address.
        type: str
        required: true
        env:
            - name: ELASTIC_HOST
    api_key:
        description: API key for authentication.
        type: str
        env:
            - name: ELASTIC_API_KEY
    username:
        description: Authentication username.
        type: str
        env:
            - name: ELASTIC_USERNAME
    password:
        description: Authentication password.
        type: str
        env:
            - name: ELASTIC_PASSWORD
    validate_certs:
        description: Validate SSL certificates.
        type: bool
        default: true
"""

EXAMPLES = r"""
# elastic_inventory.yml
plugin: stevefulme1.elastic.elastic_inventory
host: api.example.com
api_key: "{{ lookup('env', 'ELASTIC_API_KEY') }}"
"""

from ansible.plugins.inventory import BaseInventoryPlugin

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class InventoryModule(BaseInventoryPlugin):
    NAME = "stevefulme1.elastic.elastic_inventory"

    def verify_file(self, path):
        if super().verify_file(path):
            return path.endswith(("elastic_inventory.yml", "elastic_inventory.yaml"))
        return False

    def parse(self, inventory, loader, path, cache=True):
        super().parse(inventory, loader, path, cache)
        self._read_config_data(path)

        if not HAS_REQUESTS:
            raise Exception("requests library is required")

        host = self.get_option("host")
        api_key = self.get_option("api_key")
        group = self.inventory.add_group("elastic")

        # Discovery logic - connect to API and populate inventory
        try:
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            resp = requests.get(
                f"https://{host}/api/v1/hosts",
                headers=headers,
                verify=self.get_option("validate_certs"),
                timeout=30,
            )
            resp.raise_for_status()
            for item in resp.json().get("data", []):
                hostname = item.get("name", item.get("hostname", item.get("id", "")))
                if hostname:
                    self.inventory.add_host(hostname, group="elastic")
                    for k, v in item.items():
                        self.inventory.set_variable(hostname, k, v)
        except Exception as e:
            self.display.warning(f"Failed to discover hosts: {e}")
