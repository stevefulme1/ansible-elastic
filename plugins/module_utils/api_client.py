# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# Apache-2.0 (see LICENSE)

"""Shared API client for elastic collection."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

IMPORT_ERRORS = []
try:
    import requests
    HAS_REQUESTS = True
except ImportError as e:
    HAS_REQUESTS = False
    IMPORT_ERRORS.append(e)


class ApiClient:
    """REST API client for Elastic."""

    _CONNECTION_KEYS = frozenset([
        "host", "username", "password", "api_key",
        "validate_certs", "timeout", "state",
    ])

    def __init__(self, module):
        self.module = module
        self.host = module.params["host"]
        self.validate_certs = module.params.get("validate_certs", True)
        self.session = requests.Session()
        self.session.verify = self.validate_certs
        self._authenticate()

    def _filter_params(self, params):
        """Remove connection/auth keys so credentials never reach the API body."""
        return {k: v for k, v in params.items() if k not in self._CONNECTION_KEYS}

    def _authenticate(self):
        api_key = self.module.params.get("api_key")
        username = self.module.params.get("username")
        password = self.module.params.get("password")

        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
        elif username and password:
            self.session.auth = (username, password)

    def _url(self, endpoint):
        return f"https://{self.host}/api/v1/{endpoint}"

    def get(self, resource_type, resource_id):
        resp = self.session.get(self._url(f"{resource_type}s/{resource_id}"), timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def list(self, resource_type, params=None):
        resp = self.session.get(self._url(f"{resource_type}s"), params=params or {}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        return data.get("data", data.get("items", []))

    def create(self, resource_type, params):
        resp = self.session.post(self._url(f"{resource_type}s"), json=self._filter_params(params), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def update(self, resource_type, resource_id, params):
        resp = self.session.put(
            self._url(f"{resource_type}s/{resource_id}"), json=self._filter_params(params), timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def delete(self, resource_type, resource_id):
        resp = self.session.delete(self._url(f"{resource_type}s/{resource_id}"), timeout=30)
        if resp.status_code == 404:
            return
        resp.raise_for_status()
