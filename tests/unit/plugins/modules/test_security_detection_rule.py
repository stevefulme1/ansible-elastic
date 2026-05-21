# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.security_detection_rule module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import security_detection_rule
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


SAMPLE_RULE = {
    "id": "rule-abc-123",
    "name": "High CPU Alert",
    "description": "Detects high CPU usage",
    "risk_score": 50,
    "severity": "medium",
    "type": "query",
    "query": "host.cpu.usage > 90",
    "index": ["metrics-*"],
    "interval": "5m",
    "from": "now-6m",
    "to": "now",
    "language": "kuery",
    "enabled": True,
    "tags": [],
    "actions": [],
}

BASE_ARGS = {
    "api_key": "test-key",
    "api_url": "https://localhost:5601",
    "validate_certs": False,
    "request_timeout": 30,
}


class TestGetCurrentState:
    """Tests for get_current_state function."""

    def test_found_by_rule_id(self):
        """Return rule dict when found by rule_id via query param."""
        client = MagicMock()
        client.get.return_value = SAMPLE_RULE
        module = MagicMock()
        module.params = {"rule_id": "rule-abc-123", "name": "High CPU Alert"}

        result = security_detection_rule.get_current_state(client, module)

        client.get.assert_called_once_with(
            "/api/detection_engine/rules",
            params={"id": "rule-abc-123"},
        )
        assert result is not None
        assert result["id"] == "rule-abc-123"

    def test_found_by_name(self):
        """Return rule dict when found by name search."""
        client = MagicMock()
        client.get.return_value = {"data": [SAMPLE_RULE], "total": 1}
        module = MagicMock()
        module.params = {"rule_id": None, "name": "High CPU Alert"}

        result = security_detection_rule.get_current_state(client, module)

        client.get.assert_called_once_with("/api/detection_engine/rules/_find")
        assert result is not None
        assert result["name"] == "High CPU Alert"

    def test_not_found(self):
        """Return None when API raises ClientError (404)."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"rule_id": "nonexistent", "name": None}

        result = security_detection_rule.get_current_state(client, module)
        assert result is None

    def test_no_identifier(self):
        """Return None when both rule_id and name are None."""
        client = MagicMock()
        module = MagicMock()
        module.params = {"rule_id": None, "name": None}

        result = security_detection_rule.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    """Tests for needs_update function."""

    def test_current_none(self):
        """Return True when current is None (resource missing)."""
        assert security_detection_rule.needs_update(None, {"name": "test"}) is True

    def test_no_changes(self):
        """Return False when desired matches current."""
        current = {"name": "High CPU Alert", "risk_score": 50}
        desired = {"name": "High CPU Alert", "risk_score": 50}
        assert security_detection_rule.needs_update(current, desired) is False

    def test_value_changed(self):
        """Return True when a desired value differs from current."""
        current = {"name": "High CPU Alert", "risk_score": 50}
        desired = {"name": "High CPU Alert", "risk_score": 75}
        assert security_detection_rule.needs_update(current, desired) is True

    def test_none_values_skipped(self):
        """Return False when all desired values are None."""
        current = {"name": "High CPU Alert"}
        desired = {"name": None, "query": None}
        assert security_detection_rule.needs_update(current, desired) is False


class TestBuildPayload:
    """Tests for build_payload function."""

    def test_full_payload(self):
        """Include all non-None params in payload."""
        module = MagicMock()
        module.params = {
            "name": "High CPU Alert",
            "description": "Detects high CPU usage",
            "risk_score": 50,
            "severity": "medium",
            "type": "query",
            "query": "host.cpu.usage > 90",
            "index": ["metrics-*"],
            "interval": "5m",
            "from_time": "now-6m",
            "to_time": "now",
            "language": "kuery",
            "enabled": True,
            "tags": [],
            "filters": None,
            "threat": None,
            "actions": [],
        }

        payload = security_detection_rule.build_payload(module)

        assert payload["name"] == "High CPU Alert"
        assert payload["risk_score"] == 50
        assert payload["from"] == "now-6m"
        assert payload["to"] == "now"
        assert "from_time" not in payload
        assert "to_time" not in payload

    def test_from_time_mapping(self):
        """Verify from_time maps to from and to_time maps to to."""
        module = MagicMock()
        module.params = {
            "name": None,
            "description": None,
            "risk_score": None,
            "severity": None,
            "type": None,
            "query": None,
            "index": None,
            "interval": None,
            "from_time": "now-15m",
            "to_time": "now",
            "language": None,
            "enabled": None,
            "tags": None,
            "filters": None,
            "threat": None,
            "actions": None,
        }

        payload = security_detection_rule.build_payload(module)

        assert payload["from"] == "now-15m"
        assert payload["to"] == "now"


class TestMainCreate:
    """Tests for main() - create scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_detection_rule.Client")
    def test_create_new_rule(self, mock_client_cls):
        """Create a new detection rule when it does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.post.return_value = {"id": "rule-abc-123", "name": "High CPU Alert"}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "rule_id": "rule-abc-123",
            "name": "High CPU Alert",
            "description": "Detects high CPU usage",
            "risk_score": 50,
            "severity": "medium",
            "type": "query",
            "query": "host.cpu.usage > 90",
            "index": ["metrics-*"],
            "interval": "5m",
            "from_time": "now-6m",
            "to_time": "now",
            "language": "kuery",
            "enabled": True,
            "tags": [],
            "filters": None,
            "threat": None,
            "actions": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_detection_rule.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/api/detection_engine/rules"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_detection_rule.Client")
    def test_create_check_mode(self, mock_client_cls):
        """Check mode on create reports changed but does not call POST."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "rule_id": "rule-abc-123",
            "name": "High CPU Alert",
            "description": "Detects high CPU usage",
            "risk_score": 50,
            "severity": "medium",
            "type": "query",
            "query": "host.cpu.usage > 90",
            "index": ["metrics-*"],
            "interval": "5m",
            "from_time": "now-6m",
            "to_time": "now",
            "language": "kuery",
            "enabled": True,
            "tags": [],
            "filters": None,
            "threat": None,
            "actions": [],
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_detection_rule.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()


class TestMainUpdate:
    """Tests for main() - update scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_detection_rule.Client")
    def test_update_changed(self, mock_client_cls):
        """Update when desired state differs from current."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_RULE
        mock_client.put.return_value = {"id": "rule-abc-123", "name": "High CPU Alert"}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "rule_id": "rule-abc-123",
            "name": "High CPU Alert",
            "description": "Detects high CPU usage",
            "risk_score": 75,  # changed
            "severity": "high",  # changed
            "type": "query",
            "query": "host.cpu.usage > 90",
            "index": ["metrics-*"],
            "interval": "5m",
            "from_time": "now-6m",
            "to_time": "now",
            "language": "kuery",
            "enabled": True,
            "tags": [],
            "filters": None,
            "threat": None,
            "actions": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_detection_rule.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_called_once()
        # Verify id is in the PUT payload body
        call_data = mock_client.put.call_args[1].get("data", mock_client.put.call_args[0][1] if len(mock_client.put.call_args[0]) > 1 else {})
        assert call_data.get("id") == "rule-abc-123"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_detection_rule.Client")
    def test_idempotent_no_change(self, mock_client_cls):
        """No change when desired matches current state."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_RULE
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "rule_id": "rule-abc-123",
            "name": "High CPU Alert",
            "description": "Detects high CPU usage",
            "risk_score": 50,
            "severity": "medium",
            "type": "query",
            "query": "host.cpu.usage > 90",
            "index": ["metrics-*"],
            "interval": "5m",
            "from_time": "now-6m",
            "to_time": "now",
            "language": "kuery",
            "enabled": True,
            "tags": [],
            "filters": None,
            "threat": None,
            "actions": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_detection_rule.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_not_called()


class TestMainDelete:
    """Tests for main() - delete scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_detection_rule.Client")
    def test_delete_existing(self, mock_client_cls):
        """Delete an existing detection rule."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_RULE
        mock_client.delete.return_value = {}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "rule_id": "rule-abc-123",
            "name": None,
            "description": None,
            "risk_score": None,
            "tags": [],
            "actions": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_detection_rule.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_called_once_with(
            "/api/detection_engine/rules",
            params={"id": "rule-abc-123"},
        )

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_detection_rule.Client")
    def test_delete_nonexistent(self, mock_client_cls):
        """Delete idempotent when rule does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "rule_id": "nonexistent",
            "tags": [],
            "actions": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_detection_rule.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_detection_rule.Client")
    def test_delete_check_mode(self, mock_client_cls):
        """Check mode on delete reports changed but does not call DELETE."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_RULE
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "rule_id": "rule-abc-123",
            "tags": [],
            "actions": [],
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_detection_rule.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_detection_rule.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises ClientError."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_RULE
        mock_client.put.side_effect = ClientError("Server error", status_code=500)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "rule_id": "rule-abc-123",
            "name": "High CPU Alert Updated",
            "description": "Detects high CPU usage",
            "risk_score": 75,
            "severity": "high",
            "type": "query",
            "query": "host.cpu.usage > 80",
            "index": ["metrics-*"],
            "interval": "5m",
            "from_time": "now-6m",
            "to_time": "now",
            "language": "kuery",
            "enabled": True,
            "tags": [],
            "filters": None,
            "threat": None,
            "actions": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_detection_rule.main()

        assert exc_info.value.code == 1
