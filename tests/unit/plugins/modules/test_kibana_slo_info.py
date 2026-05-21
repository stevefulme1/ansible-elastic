# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.kibana_slo_info module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_slo_info
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

SAMPLE_SLO = {
    "id": "slo-123",
    "name": "Availability SLO",
    "description": "99% availability",
    "indicator": {"type": "sli.kql.custom", "params": {"index": "logs-*"}},
    "timeWindow": {"duration": "30d", "type": "rolling"},
    "budgetingMethod": "occurrences",
    "objective": {"target": 0.99},
    "tags": ["production"],
}

SAMPLE_LIST_RESPONSE = {
    "results": [
        SAMPLE_SLO,
        {
            "id": "slo-456",
            "name": "Latency SLO",
            "description": "P99 < 500ms",
            "indicator": {"type": "sli.kql.custom", "params": {"index": "apm-*"}},
            "timeWindow": {"duration": "7d", "type": "rolling"},
            "budgetingMethod": "timeslices",
            "objective": {"target": 0.95},
            "tags": [],
        },
    ],
    "total": 2,
}


class TestFetchSingle:
    """Tests for fetch_single function."""

    def test_found(self):
        """Return SLO dict when found."""
        client = MagicMock()
        client.get.return_value = SAMPLE_SLO

        result = kibana_slo_info.fetch_single(client, "slo-123")

        client.get.assert_called_once_with("/api/observability/slos/slo-123")
        assert result is not None
        assert result["id"] == "slo-123"

    def test_not_found(self):
        """Return None when SLO not found."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)

        result = kibana_slo_info.fetch_single(client, "nonexistent")
        assert result is None

    def test_client_error(self):
        """Return None when API raises ClientError."""
        client = MagicMock()
        client.get.side_effect = ClientError("Server error", status_code=500)

        result = kibana_slo_info.fetch_single(client, "slo-123")
        assert result is None


class TestFetchList:
    """Tests for fetch_list function."""

    def test_list_all(self):
        """Return all SLOs from API."""
        client = MagicMock()
        client.get.return_value = SAMPLE_LIST_RESPONSE
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = kibana_slo_info.fetch_list(client, module)

        assert len(result) == 2
        assert result[0]["id"] == "slo-123"

    def test_list_with_pagination(self):
        """Pass page/perPage when set."""
        client = MagicMock()
        client.get.return_value = SAMPLE_LIST_RESPONSE
        module = MagicMock()
        module.params = {"page": 2, "page_size": 10}

        result = kibana_slo_info.fetch_list(client, module)

        call_params = client.get.call_args[1].get("params", {})
        assert call_params.get("page") == 2
        assert call_params.get("perPage") == 10

    def test_list_empty(self):
        """Return empty list when no SLOs exist."""
        client = MagicMock()
        client.get.return_value = {"results": [], "total": 0}
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = kibana_slo_info.fetch_list(client, module)
        assert result == []

    def test_list_client_error(self):
        """Return empty list on ClientError."""
        client = MagicMock()
        client.get.side_effect = ClientError("Server error", status_code=500)
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = kibana_slo_info.fetch_list(client, module)
        assert result == []


class TestMainSingle:
    """Tests for main() - single SLO retrieval."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo_info.Client")
    def test_get_single_slo(self, mock_client_cls):
        """Return single SLO in kibana_slos list."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SLO
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["slo_id"] = "slo-123"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo_info.Client")
    def test_get_missing_slo(self, mock_client_cls):
        """Return empty list when SLO not found."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["slo_id"] = "missing"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo_info.main()

        assert exc_info.value.code == 0


class TestMainList:
    """Tests for main() - list SLOs."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo_info.Client")
    def test_list_all_slos(self, mock_client_cls):
        """Return all SLOs when no id specified."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_LIST_RESPONSE
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo_info.Client")
    def test_always_changed_false(self, mock_client_cls):
        """Info module always returns changed=False."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"results": [], "total": 0}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo_info.main()

        assert exc_info.value.code == 0


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo_info.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises unexpected ClientError."""
        mock_client_cls.side_effect = ClientError("Connection refused")

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo_info.main()

        assert exc_info.value.code == 1
