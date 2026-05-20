# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.fleet_package_policy_info module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import fleet_package_policy_info
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


def set_module_args(args):
    if "_ansible_remote_tmp" not in args:
        args["_ansible_remote_tmp"] = "/tmp"
    if "_ansible_keep_remote_files" not in args:
        args["_ansible_keep_remote_files"] = False
    args_json = json.dumps({"ANSIBLE_MODULE_ARGS": args})
    basic._ANSIBLE_ARGS = to_bytes(args_json)
    basic._ANSIBLE_PROFILE = "legacy"


BASE_ARGS = {
    "api_key": "test-key",
    "api_url": "https://localhost:5601",
    "validate_certs": False,
    "request_timeout": 30,
}

SAMPLE_POLICY = {
    "id": "pkg-123",
    "name": "system-1",
    "namespace": "default",
    "policy_id": "agent-policy-123",
    "package": {"name": "system", "version": "1.0.0"},
}

SAMPLE_POLICY_LIST = [
    {"id": "pkg-123", "name": "system-1"},
    {"id": "pkg-456", "name": "nginx-1"},
]


class TestFetchSingle:
    def test_found(self):
        client = MagicMock()
        client.get.return_value = {"item": SAMPLE_POLICY}

        result = fleet_package_policy_info.fetch_single(client, "pkg-123")
        client.get.assert_called_once_with("/api/fleet/package_policies/pkg-123")
        assert result is not None
        assert result["id"] == "pkg-123"

    def test_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)

        result = fleet_package_policy_info.fetch_single(client, "nonexistent")
        assert result is None


class TestFetchList:
    def test_list_all(self):
        client = MagicMock()
        client.get.return_value = {"items": SAMPLE_POLICY_LIST}

        result = fleet_package_policy_info.fetch_list(client)
        client.get.assert_called_once_with("/api/fleet/package_policies")
        assert len(result) == 2

    def test_list_empty(self):
        client = MagicMock()
        client.get.return_value = {"items": []}

        result = fleet_package_policy_info.fetch_list(client)
        assert result == []

    def test_list_client_error(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Server error", status_code=500)

        result = fleet_package_policy_info.fetch_list(client)
        assert result == []


class TestMainSingle:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy_info.Client")
    def test_get_single(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"item": SAMPLE_POLICY}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["package_policy_id"] = "pkg-123"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            fleet_package_policy_info.main()
        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy_info.Client")
    def test_get_missing(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["package_policy_id"] = "missing"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            fleet_package_policy_info.main()
        assert exc_info.value.code == 0


class TestMainList:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy_info.Client")
    def test_list_all(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"items": SAMPLE_POLICY_LIST}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            fleet_package_policy_info.main()
        assert exc_info.value.code == 0


class TestMainError:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy_info.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        mock_client_cls.side_effect = ClientError("Connection refused")

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            fleet_package_policy_info.main()
        assert exc_info.value.code == 1
