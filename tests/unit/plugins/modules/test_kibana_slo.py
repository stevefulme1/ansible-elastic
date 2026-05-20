# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.kibana_slo module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_slo
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


SAMPLE_SLO = {
    "id": "slo-123",
    "name": "Availability SLO",
    "description": "99% availability for web services",
    "indicator": {
        "type": "sli.kql.custom",
        "params": {
            "index": "logs-*",
            "good": "status: 200",
            "total": "*",
            "timestampField": "@timestamp",
        },
    },
    "timeWindow": {"duration": "30d", "type": "rolling"},
    "budgetingMethod": "occurrences",
    "objective": {"target": 0.99},
    "tags": ["production"],
}

BASE_ARGS = {
    "api_key": "test-key",
    "api_url": "https://localhost:5601",
    "validate_certs": False,
    "request_timeout": 30,
}


class TestGetCurrentState:
    """Tests for get_current_state function."""

    def test_found_by_id(self):
        """Return SLO dict when found by slo_id."""
        client = MagicMock()
        client.get.return_value = SAMPLE_SLO
        module = MagicMock()
        module.params = {"slo_id": "slo-123", "name": "Availability SLO"}

        result = kibana_slo.get_current_state(client, module)

        client.get.assert_called_once_with("/api/observability/slos/slo-123")
        assert result is not None
        assert result["id"] == "slo-123"

    def test_found_by_name(self):
        """Return SLO dict when found by name search."""
        client = MagicMock()
        client.get.return_value = {"results": [SAMPLE_SLO], "total": 1}
        module = MagicMock()
        module.params = {"slo_id": None, "name": "Availability SLO"}

        result = kibana_slo.get_current_state(client, module)

        client.get.assert_called_once_with("/api/observability/slos")
        assert result is not None
        assert result["name"] == "Availability SLO"

    def test_not_found(self):
        """Return None when API raises ClientError (404)."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"slo_id": "nonexistent", "name": None}

        result = kibana_slo.get_current_state(client, module)
        assert result is None

    def test_no_identifier(self):
        """Return None when both slo_id and name are None."""
        client = MagicMock()
        module = MagicMock()
        module.params = {"slo_id": None, "name": None}

        result = kibana_slo.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    """Tests for needs_update function."""

    def test_current_none(self):
        """Return True when current is None (resource missing)."""
        assert kibana_slo.needs_update(None, {"name": "test"}) is True

    def test_no_changes(self):
        """Return False when desired matches current."""
        current = {"name": "Availability SLO", "objective": {"target": 0.99}}
        desired = {"name": "Availability SLO", "objective": {"target": 0.99}}
        assert kibana_slo.needs_update(current, desired) is False

    def test_value_changed(self):
        """Return True when a desired value differs from current."""
        current = {"name": "Availability SLO", "objective": {"target": 0.99}}
        desired = {"name": "Availability SLO", "objective": {"target": 0.999}}
        assert kibana_slo.needs_update(current, desired) is True

    def test_none_values_skipped(self):
        """Return False when all desired values are None."""
        current = {"name": "Availability SLO"}
        desired = {"name": None, "description": None}
        assert kibana_slo.needs_update(current, desired) is False


class TestBuildPayload:
    """Tests for build_payload function."""

    def test_full_payload(self):
        """Include all non-None params with correct API key names."""
        module = MagicMock()
        module.params = {
            "name": "Availability SLO",
            "description": "99% availability",
            "indicator": {"type": "sli.kql.custom", "params": {"index": "logs-*"}},
            "time_window": {"duration": "30d", "type": "rolling"},
            "budgeting_method": "occurrences",
            "objective": {"target": 0.99},
            "tags": ["production"],
        }

        payload = kibana_slo.build_payload(module)

        assert payload["name"] == "Availability SLO"
        assert payload["timeWindow"] == {"duration": "30d", "type": "rolling"}
        assert payload["budgetingMethod"] == "occurrences"

    def test_minimal_payload(self):
        """Only include non-None params."""
        module = MagicMock()
        module.params = {
            "name": "Test SLO",
            "description": None,
            "indicator": None,
            "time_window": None,
            "budgeting_method": None,
            "objective": None,
            "tags": ["test"],
        }

        payload = kibana_slo.build_payload(module)
        assert set(payload.keys()) == {"name", "tags"}


class TestMainCreate:
    """Tests for main() - create scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo.Client")
    def test_create_new_slo(self, mock_client_cls):
        """Create a new SLO when it does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.post.return_value = {"id": "slo-123", "name": "Availability SLO"}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "slo_id": "slo-123",
            "name": "Availability SLO",
            "description": "99% availability",
            "indicator": {"type": "sli.kql.custom", "params": {"index": "logs-*"}},
            "time_window": {"duration": "30d", "type": "rolling"},
            "budgeting_method": "occurrences",
            "objective": {"target": 0.99},
            "tags": ["production"],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/api/observability/slos"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo.Client")
    def test_create_check_mode(self, mock_client_cls):
        """Check mode on create reports changed but does not call POST."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "slo_id": "slo-123",
            "name": "Availability SLO",
            "description": None,
            "indicator": {"type": "sli.kql.custom", "params": {"index": "logs-*"}},
            "time_window": {"duration": "30d", "type": "rolling"},
            "budgeting_method": "occurrences",
            "objective": {"target": 0.99},
            "tags": [],
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()


class TestMainUpdate:
    """Tests for main() - update scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo.Client")
    def test_update_changed(self, mock_client_cls):
        """Update when desired state differs from current."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SLO
        mock_client.put.return_value = {"id": "slo-123", "name": "Availability SLO"}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "slo_id": "slo-123",
            "name": "Availability SLO",
            "description": "99.9% availability",  # changed
            "indicator": None,
            "time_window": None,
            "budgeting_method": "occurrences",
            "objective": {"target": 0.999},  # changed
            "tags": ["production"],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_called_once()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo.Client")
    def test_idempotent_no_change(self, mock_client_cls):
        """No change when desired matches current state."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SLO
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "slo_id": "slo-123",
            "name": "Availability SLO",
            "description": "99% availability for web services",
            "indicator": {
                "type": "sli.kql.custom",
                "params": {
                    "index": "logs-*",
                    "good": "status: 200",
                    "total": "*",
                    "timestampField": "@timestamp",
                },
            },
            "time_window": None,
            "budgeting_method": "occurrences",
            "objective": {"target": 0.99},
            "tags": ["production"],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_not_called()


class TestMainDelete:
    """Tests for main() - delete scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo.Client")
    def test_delete_existing(self, mock_client_cls):
        """Delete an existing SLO."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SLO
        mock_client.delete.return_value = {}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "slo_id": "slo-123",
            "name": None,
            "description": None,
            "indicator": None,
            "time_window": None,
            "budgeting_method": "occurrences",
            "objective": None,
            "tags": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_called_once_with("/api/observability/slos/slo-123")

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo.Client")
    def test_delete_nonexistent(self, mock_client_cls):
        """Delete idempotent when SLO does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "slo_id": "nonexistent",
            "name": None,
            "description": None,
            "indicator": None,
            "time_window": None,
            "budgeting_method": "occurrences",
            "objective": None,
            "tags": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo.Client")
    def test_delete_check_mode(self, mock_client_cls):
        """Check mode on delete reports changed but does not call DELETE."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SLO
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "slo_id": "slo-123",
            "name": None,
            "description": None,
            "indicator": None,
            "time_window": None,
            "budgeting_method": "occurrences",
            "objective": None,
            "tags": [],
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_slo.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises ClientError."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SLO
        mock_client.put.side_effect = ClientError("Server error", status_code=500)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "slo_id": "slo-123",
            "name": "Changed SLO",
            "description": None,
            "indicator": None,
            "time_window": None,
            "budgeting_method": "occurrences",
            "objective": None,
            "tags": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_slo.main()

        assert exc_info.value.code == 1
