# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment:
    """Documentation fragment for stevefulme1.elastic authentication."""

    DOCUMENTATION = r"""
options:
  api_url:
    description:
      - The base URL of the Elastic Stack API (Elasticsearch or Kibana).
      - For Elasticsearch, typically C(https://localhost:9200).
      - For Kibana, typically C(https://localhost:5601).
      - For Elastic Cloud, use the deployment endpoint URL.
    type: str
    required: true
  api_key:
    description:
      - An Elasticsearch or Kibana API key for authentication.
      - The key should be the base64-encoded C(id:api_key) value.
      - Mutually exclusive with I(api_username) and I(api_password).
    type: str
  api_username:
    description:
      - Username for HTTP Basic authentication.
      - Must be used together with I(api_password).
      - Mutually exclusive with I(api_key).
    type: str
  api_password:
    description:
      - Password for HTTP Basic authentication.
      - Must be used together with I(api_username).
      - Mutually exclusive with I(api_key).
    type: str
  validate_certs:
    description:
      - Whether to validate SSL/TLS certificates when connecting to the API.
    type: bool
    default: true
  request_timeout:
    description:
      - Timeout in seconds for API requests.
    type: int
    default: 30
"""
