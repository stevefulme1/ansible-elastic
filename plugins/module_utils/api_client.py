# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import base64
import json
import time

from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.module_utils.six.moves.urllib.parse import urlencode


class ClientError(Exception):
    """Exception raised by the API client."""

    def __init__(self, message, status_code=None, response_body=None):
        super(ClientError, self).__init__(message)
        self.status_code = status_code
        self.response_body = response_body


def argument_spec():
    """Return the shared authentication argument spec for all modules."""
    return dict(
        api_url=dict(
            type="str",
            required=True,
        ),
        api_key=dict(type="str", no_log=True),
        api_username=dict(type="str"),
        api_password=dict(type="str", no_log=True),
        validate_certs=dict(type="bool", default=True),
        request_timeout=dict(type="int", default=30),
    )


def auth_mutually_exclusive():
    """Return mutually exclusive auth parameter groups."""
    return [
        ("api_key", "api_username"),
        ("api_key", "api_password"),
    ]


def auth_required_together():
    """Return auth parameters that must be specified together."""
    return [
        ("api_username", "api_password"),
    ]


def auth_required_one_of():
    """Return auth parameter groups where at least one is required."""
    return [
        ("api_key", "api_username"),
    ]


class Client:
    """HTTP client for the Elastic Stack API with auth, retry, and Kibana support."""

    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2
    RETRY_STATUS_CODES = (429, 500, 502, 503, 504)

    def __init__(self, module):
        self.module = module
        self.base_url = module.params["api_url"].rstrip("/")
        self.validate_certs = module.params["validate_certs"]
        self.timeout = module.params["request_timeout"]
        self.headers = self._build_auth_headers()

    def _build_auth_headers(self):
        """Construct authentication headers for Elasticsearch or Kibana."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        api_key = self.module.params.get("api_key")
        api_username = self.module.params.get("api_username")

        if api_key:
            headers["Authorization"] = "ApiKey {0}".format(api_key)
        elif api_username:
            api_password = self.module.params.get("api_password") or ""
            credentials = base64.b64encode(
                "{0}:{1}".format(api_username, api_password).encode("utf-8")
            ).decode("utf-8")
            headers["Authorization"] = "Basic {0}".format(credentials)

        return headers

    def _build_url(self, path, params=None):
        """Build the full URL from a path and optional query parameters."""
        url = "{0}/{1}".format(self.base_url, path.lstrip("/"))

        if params:
            url = "{0}?{1}".format(url, urlencode(params, doseq=True))
        return url

    def _request(self, method, path, data=None, params=None, extra_headers=None):
        """Execute an HTTP request with retry and backoff on rate limits."""
        url = self._build_url(path, params)
        body = json.dumps(data).encode("utf-8") if data is not None else None

        request_headers = dict(self.headers)
        if extra_headers:
            request_headers.update(extra_headers)

        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = open_url(
                    url,
                    method=method,
                    headers=request_headers,
                    data=body,
                    validate_certs=self.validate_certs,
                    timeout=self.timeout,
                    force_basic_auth=True,
                )
                response_body = response.read()
                if response_body:
                    return json.loads(response_body)
                return {}

            except HTTPError as e:
                status = e.code
                response_body = ""
                try:
                    response_body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    pass

                if status in self.RETRY_STATUS_CODES and attempt < self.MAX_RETRIES:
                    retry_after = None
                    if status == 429:
                        retry_after_header = e.headers.get("Retry-After")
                        if retry_after_header:
                            try:
                                retry_after = int(retry_after_header)
                            except ValueError:
                                pass
                    wait_time = retry_after or (self.RETRY_BACKOFF_BASE ** (attempt + 1))
                    time.sleep(wait_time)
                    last_error = e
                    continue

                msg = "API request failed: {0} {1} returned {2}".format(
                    method, url, status
                )
                if response_body:
                    try:
                        detail = json.loads(response_body)
                        msg = "{0}: {1}".format(
                            msg,
                            detail.get("message", detail.get("error", response_body)),
                        )
                    except (ValueError, TypeError):
                        msg = "{0}: {1}".format(msg, response_body)

                raise ClientError(msg, status_code=status, response_body=response_body)

            except URLError as e:
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_BACKOFF_BASE ** (attempt + 1))
                    last_error = e
                    continue
                raise ClientError(
                    "Failed to connect to {0}: {1}".format(url, str(e))
                )

        raise ClientError(
            "Max retries ({0}) exceeded for {1} {2}: {3}".format(
                self.MAX_RETRIES, method, path, str(last_error)
            )
        )

    def get(self, path, params=None):
        """Perform a GET request."""
        return self._request("GET", path, params=params)

    def post(self, path, data=None, params=None, extra_headers=None):
        """Perform a POST request."""
        return self._request("POST", path, data=data, params=params, extra_headers=extra_headers)

    def put(self, path, data=None, params=None):
        """Perform a PUT request."""
        return self._request("PUT", path, data=data, params=params)

    def patch(self, path, data=None, params=None):
        """Perform a PATCH request."""
        return self._request("PATCH", path, data=data, params=params)

    def delete(self, path, data=None, params=None):
        """Perform a DELETE request."""
        return self._request("DELETE", path, data=data, params=params)
