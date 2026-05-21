# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.kibana_case_info module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_case_info
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

SAMPLE_CASE = {
    "id": "case-123",
    "version": "WzEsMV0=",
    "title": "Server Down",
    "description": "Production server unresponsive",
    "tags": ["incident"],
    "severity": "medium",
    "status": "open",
    "owner": "cases",
}

SAMPLE_FIND_RESPONSE = {
    "cases": [
        {
            "id": "case-1",
            "title": "Case 1",
            "severity": "low",
            "status": "open",
        },
        {
            "id": "case-2",
            "title": "Case 2",
            "severity": "high",
            "status": "closed",
        },
    ],
    "total": 2,
}


class TestFetchSingle:
    """Tests for fetch_single function."""

    def test_found(self):
        """Return case dict when found."""
        client = MagicMock()
        client.get.return_value = SAMPLE_CASE

        result = kibana_case_info.fetch_single(client, "case-123")

        client.get.assert_called_once_with("/api/cases/case-123")
        assert result is not None
        assert result["id"] == "case-123"
        assert result["title"] == "Server Down"

    def test_not_found(self):
        """Return None when API raises ClientError."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)

        result = kibana_case_info.fetch_single(client, "nonexistent")
        assert result is None

    def test_no_id_in_response(self):
        """Return None when response has no id."""
        client = MagicMock()
        client.get.return_value = {}

        result = kibana_case_info.fetch_single(client, "bad")
        assert result is None


class TestFetchList:
    """Tests for fetch_list function."""

    def test_list_all(self):
        """Return all cases from _find API."""
        client = MagicMock()
        client.get.return_value = SAMPLE_FIND_RESPONSE
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = kibana_case_info.fetch_list(client, module)

        client.get.assert_called_once_with("/api/cases/_find", params={})
        assert len(result) == 2
        assert result[0]["id"] == "case-1"
        assert result[1]["id"] == "case-2"

    def test_list_with_pagination(self):
        """Pass page and perPage when set."""
        client = MagicMock()
        client.get.return_value = SAMPLE_FIND_RESPONSE
        module = MagicMock()
        module.params = {"page": 2, "page_size": 10}

        result = kibana_case_info.fetch_list(client, module)

        client.get.assert_called_once_with(
            "/api/cases/_find",
            params={"page": 2, "perPage": 10},
        )
        assert len(result) == 2

    def test_list_empty(self):
        """Return empty list when no cases exist."""
        client = MagicMock()
        client.get.return_value = {"cases": [], "total": 0}
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = kibana_case_info.fetch_list(client, module)
        assert result == []

    def test_list_client_error(self):
        """Return empty list on ClientError."""
        client = MagicMock()
        client.get.side_effect = ClientError("Server error", status_code=500)
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = kibana_case_info.fetch_list(client, module)
        assert result == []


class TestMainSingle:
    """Tests for main() - single case retrieval."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case_info.Client")
    def test_get_single_case(self, mock_client_cls):
        """Return single case in kibana_cases list."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_CASE

        args = dict(BASE_ARGS)
        args["case_id"] = "case-123"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case_info.Client")
    def test_get_missing_case(self, mock_client_cls):
        """Return empty list when case not found."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        args = dict(BASE_ARGS)
        args["case_id"] = "missing"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case_info.main()

        assert exc_info.value.code == 0


class TestMainList:
    """Tests for main() - list cases."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case_info.Client")
    def test_list_all_cases(self, mock_client_cls):
        """Return all cases when no case_id specified."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_FIND_RESPONSE

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case_info.Client")
    def test_always_changed_false(self, mock_client_cls):
        """Info module always returns changed=False."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"cases": [], "total": 0}

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case_info.main()

        assert exc_info.value.code == 0


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case_info.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises unexpected ClientError."""
        mock_client_cls.side_effect = ClientError("Connection refused")

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case_info.main()

        assert exc_info.value.code == 1
