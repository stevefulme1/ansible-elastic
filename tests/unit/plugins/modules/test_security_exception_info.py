# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.security_exception_info module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import security_exception_info
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


def set_module_args(args):
    """Prepare arguments so that they will be picked up during module creation."""
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

SAMPLE_EXCEPTION = {
    "id": "exc-uuid-123",
    "list_id": "trusted-processes",
    "name": "Trusted Processes",
    "description": "Processes excluded from detection",
    "type": "detection",
    "namespace_type": "single",
    "tags": [],
}

SAMPLE_LIST_RESPONSE = {
    "data": [
        SAMPLE_EXCEPTION,
        {
            "id": "exc-uuid-456",
            "list_id": "safe-ips",
            "name": "Safe IPs",
            "description": "Trusted IP addresses",
            "type": "detection",
            "namespace_type": "single",
            "tags": ["network"],
        },
    ],
    "total": 2,
}


class TestFetchSingle:
    """Tests for fetch_single function."""

    def test_found_by_list_id(self):
        """Return exception dict when found by list_id."""
        client = MagicMock()
        client.get.return_value = SAMPLE_EXCEPTION

        result = security_exception_info.fetch_single(
            client, list_id="trusted-processes",
        )

        client.get.assert_called_once_with(
            "/api/exception_lists",
            params={"list_id": "trusted-processes"},
        )
        assert result is not None
        assert result["list_id"] == "trusted-processes"

    def test_found_by_exception_id(self):
        """Return exception dict when found by exception_id."""
        client = MagicMock()
        client.get.return_value = SAMPLE_EXCEPTION

        result = security_exception_info.fetch_single(
            client, exception_id="exc-uuid-123",
        )

        client.get.assert_called_once_with(
            "/api/exception_lists",
            params={"id": "exc-uuid-123"},
        )
        assert result is not None

    def test_not_found(self):
        """Return None when exception list not found."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)

        result = security_exception_info.fetch_single(
            client, exception_id="nonexistent",
        )
        assert result is None

    def test_no_identifier(self):
        """Return None when no identifier provided."""
        client = MagicMock()

        result = security_exception_info.fetch_single(client)
        assert result is None


class TestFetchList:
    """Tests for fetch_list function."""

    def test_list_all(self):
        """Return all exception lists from find API."""
        client = MagicMock()
        client.get.return_value = SAMPLE_LIST_RESPONSE
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = security_exception_info.fetch_list(client, module)

        assert len(result) == 2
        assert result[0]["list_id"] == "trusted-processes"

    def test_list_with_pagination(self):
        """Pass page/per_page when set."""
        client = MagicMock()
        client.get.return_value = SAMPLE_LIST_RESPONSE
        module = MagicMock()
        module.params = {"page": 2, "page_size": 10}

        result = security_exception_info.fetch_list(client, module)

        call_params = client.get.call_args[1].get("params", {})
        assert call_params.get("page") == 2
        assert call_params.get("per_page") == 10

    def test_list_empty(self):
        """Return empty list when no exception lists exist."""
        client = MagicMock()
        client.get.return_value = {"data": [], "total": 0}
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = security_exception_info.fetch_list(client, module)
        assert result == []

    def test_list_client_error(self):
        """Return empty list on ClientError."""
        client = MagicMock()
        client.get.side_effect = ClientError("Server error", status_code=500)
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = security_exception_info.fetch_list(client, module)
        assert result == []


class TestMainSingle:
    """Tests for main() - single exception list retrieval."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception_info.Client")
    def test_get_by_list_id(self, mock_client_cls):
        """Return single exception list by list_id."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_EXCEPTION
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["list_id"] = "trusted-processes"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception_info.Client")
    def test_get_by_exception_id(self, mock_client_cls):
        """Return single exception list by exception_id."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_EXCEPTION
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["exception_id"] = "exc-uuid-123"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception_info.Client")
    def test_get_missing(self, mock_client_cls):
        """Return empty list when exception list not found."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["exception_id"] = "missing"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception_info.main()

        assert exc_info.value.code == 0


class TestMainList:
    """Tests for main() - list exception lists."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception_info.Client")
    def test_list_all(self, mock_client_cls):
        """Return all exception lists when no id specified."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_LIST_RESPONSE
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception_info.Client")
    def test_always_changed_false(self, mock_client_cls):
        """Info module always returns changed=False."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"data": [], "total": 0}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception_info.main()

        assert exc_info.value.code == 0


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception_info.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises unexpected ClientError."""
        mock_client_cls.side_effect = ClientError("Connection refused")

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception_info.main()

        assert exc_info.value.code == 1
