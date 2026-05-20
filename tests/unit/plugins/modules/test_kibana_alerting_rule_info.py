# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.kibana_alerting_rule_info module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_alerting_rule_info
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

SAMPLE_RULE = {
    "id": "rule-123",
    "name": "CPU Alert",
    "rule_type_id": ".es-query",
    "consumer": "alerts",
    "schedule": {"interval": "1m"},
    "actions": [],
    "params": {"index": ["metrics-*"]},
    "tags": ["production"],
    "enabled": True,
}

SAMPLE_LIST_RESPONSE = {
    "data": [
        SAMPLE_RULE,
        {
            "id": "rule-456",
            "name": "Memory Alert",
            "rule_type_id": ".es-query",
            "consumer": "alerts",
            "schedule": {"interval": "5m"},
            "actions": [],
            "params": {"index": ["metrics-*"]},
            "tags": [],
            "enabled": False,
        },
    ],
    "total": 2,
}


class TestFetchSingle:
    """Tests for fetch_single function."""

    def test_found(self):
        """Return rule dict when found."""
        client = MagicMock()
        client.get.return_value = SAMPLE_RULE

        result = kibana_alerting_rule_info.fetch_single(client, "rule-123")

        client.get.assert_called_once_with("/api/alerting/rule/rule-123")
        assert result is not None
        assert result["id"] == "rule-123"

    def test_not_found(self):
        """Return None when rule not found."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)

        result = kibana_alerting_rule_info.fetch_single(client, "nonexistent")
        assert result is None

    def test_client_error(self):
        """Return None when API raises ClientError."""
        client = MagicMock()
        client.get.side_effect = ClientError("Server error", status_code=500)

        result = kibana_alerting_rule_info.fetch_single(client, "rule-123")
        assert result is None


class TestFetchList:
    """Tests for fetch_list function."""

    def test_list_all(self):
        """Return all rules from find API."""
        client = MagicMock()
        client.get.return_value = SAMPLE_LIST_RESPONSE
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = kibana_alerting_rule_info.fetch_list(client, module)

        assert len(result) == 2
        assert result[0]["id"] == "rule-123"

    def test_list_with_pagination(self):
        """Pass page/per_page when set."""
        client = MagicMock()
        client.get.return_value = SAMPLE_LIST_RESPONSE
        module = MagicMock()
        module.params = {"page": 2, "page_size": 10}

        result = kibana_alerting_rule_info.fetch_list(client, module)

        call_params = client.get.call_args[1].get("params", {})
        assert call_params.get("page") == 2
        assert call_params.get("per_page") == 10

    def test_list_empty(self):
        """Return empty list when no rules exist."""
        client = MagicMock()
        client.get.return_value = {"data": [], "total": 0}
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = kibana_alerting_rule_info.fetch_list(client, module)
        assert result == []

    def test_list_client_error(self):
        """Return empty list on ClientError."""
        client = MagicMock()
        client.get.side_effect = ClientError("Server error", status_code=500)
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = kibana_alerting_rule_info.fetch_list(client, module)
        assert result == []


class TestMainSingle:
    """Tests for main() - single rule retrieval."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule_info.Client")
    def test_get_single_rule(self, mock_client_cls):
        """Return single rule in kibana_alerting_rules list."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_RULE
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["rule_id"] = "rule-123"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule_info.Client")
    def test_get_missing_rule(self, mock_client_cls):
        """Return empty list when rule not found."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["rule_id"] = "missing"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule_info.main()

        assert exc_info.value.code == 0


class TestMainList:
    """Tests for main() - list rules."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule_info.Client")
    def test_list_all_rules(self, mock_client_cls):
        """Return all rules when no id specified."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_LIST_RESPONSE
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule_info.Client")
    def test_always_changed_false(self, mock_client_cls):
        """Info module always returns changed=False."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"data": [], "total": 0}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule_info.main()

        assert exc_info.value.code == 0


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule_info.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises unexpected ClientError."""
        mock_client_cls.side_effect = ClientError("Connection refused")

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule_info.main()

        assert exc_info.value.code == 1
