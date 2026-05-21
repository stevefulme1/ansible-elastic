# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.kibana_alerting_rule module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_alerting_rule
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
    "id": "rule-123",
    "name": "CPU Alert",
    "rule_type_id": ".es-query",
    "consumer": "alerts",
    "schedule": {"interval": "1m"},
    "actions": [],
    "params": {
        "index": ["metrics-*"],
        "timeField": "@timestamp",
        "esQuery": '{"query": {"match_all": {}}}',
        "threshold": [1000],
        "thresholdComparator": ">",
    },
    "tags": ["production"],
    "enabled": True,
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
        """Return rule dict when found by rule_id."""
        client = MagicMock()
        client.get.return_value = SAMPLE_RULE
        module = MagicMock()
        module.params = {"rule_id": "rule-123", "name": "CPU Alert"}

        result = kibana_alerting_rule.get_current_state(client, module)

        client.get.assert_called_once_with("/api/alerting/rule/rule-123")
        assert result is not None
        assert result["id"] == "rule-123"

    def test_found_by_name(self):
        """Return rule dict when found by name search."""
        client = MagicMock()
        client.get.return_value = {"data": [SAMPLE_RULE], "total": 1}
        module = MagicMock()
        module.params = {"rule_id": None, "name": "CPU Alert"}

        result = kibana_alerting_rule.get_current_state(client, module)

        client.get.assert_called_once_with("/api/alerting/rules/_find")
        assert result is not None
        assert result["name"] == "CPU Alert"

    def test_not_found(self):
        """Return None when API raises ClientError (404)."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"rule_id": "nonexistent", "name": None}

        result = kibana_alerting_rule.get_current_state(client, module)
        assert result is None

    def test_no_identifier(self):
        """Return None when both rule_id and name are None."""
        client = MagicMock()
        module = MagicMock()
        module.params = {"rule_id": None, "name": None}

        result = kibana_alerting_rule.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    """Tests for needs_update function."""

    def test_current_none(self):
        """Return True when current is None (resource missing)."""
        assert kibana_alerting_rule.needs_update(None, {"name": "test"}) is True

    def test_no_changes(self):
        """Return False when desired matches current."""
        current = {"name": "CPU Alert", "schedule": {"interval": "1m"}}
        desired = {"name": "CPU Alert", "schedule": {"interval": "1m"}}
        assert kibana_alerting_rule.needs_update(current, desired) is False

    def test_value_changed(self):
        """Return True when a desired value differs from current."""
        current = {"name": "CPU Alert", "schedule": {"interval": "1m"}}
        desired = {"name": "CPU Alert", "schedule": {"interval": "5m"}}
        assert kibana_alerting_rule.needs_update(current, desired) is True

    def test_none_values_skipped(self):
        """Return False when all desired values are None."""
        current = {"name": "CPU Alert"}
        desired = {"name": None, "throttle": None}
        assert kibana_alerting_rule.needs_update(current, desired) is False


class TestBuildPayload:
    """Tests for build_payload function."""

    def test_full_payload(self):
        """Include all non-None params in payload for create."""
        module = MagicMock()
        module.params = {
            "name": "CPU Alert",
            "rule_type_id": ".es-query",
            "consumer": "alerts",
            "schedule": {"interval": "1m"},
            "actions": [],
            "params": {"index": ["metrics-*"]},
            "tags": ["production"],
            "enabled": True,
            "throttle": "5m",
            "notify_when": "onActiveAlert",
        }

        payload = kibana_alerting_rule.build_payload(module, for_update=False)

        assert payload["name"] == "CPU Alert"
        assert payload["rule_type_id"] == ".es-query"
        assert payload["consumer"] == "alerts"
        assert payload["throttle"] == "5m"

    def test_update_excludes_immutable(self):
        """Update payload excludes rule_type_id, consumer, enabled."""
        module = MagicMock()
        module.params = {
            "name": "CPU Alert",
            "rule_type_id": ".es-query",
            "consumer": "alerts",
            "schedule": {"interval": "5m"},
            "actions": [],
            "params": {"index": ["metrics-*"]},
            "tags": [],
            "enabled": True,
            "throttle": None,
            "notify_when": None,
        }

        payload = kibana_alerting_rule.build_payload(module, for_update=True)

        assert "rule_type_id" not in payload
        assert "consumer" not in payload
        assert "enabled" not in payload
        assert payload["schedule"] == {"interval": "5m"}


class TestMainCreate:
    """Tests for main() - create scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule.Client")
    def test_create_new_rule(self, mock_client_cls):
        """Create a new alerting rule when it does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.post.return_value = {"id": "rule-123", "name": "CPU Alert"}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "rule_id": "rule-123",
            "name": "CPU Alert",
            "rule_type_id": ".es-query",
            "consumer": "alerts",
            "schedule": {"interval": "1m"},
            "actions": [],
            "params": {"index": ["metrics-*"]},
            "tags": ["production"],
            "enabled": True,
            "throttle": None,
            "notify_when": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/api/alerting/rule"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule.Client")
    def test_create_check_mode(self, mock_client_cls):
        """Check mode on create reports changed but does not call POST."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "rule_id": "rule-123",
            "name": "CPU Alert",
            "rule_type_id": ".es-query",
            "consumer": "alerts",
            "schedule": {"interval": "1m"},
            "actions": [],
            "params": {"index": ["metrics-*"]},
            "tags": [],
            "enabled": True,
            "throttle": None,
            "notify_when": None,
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()


class TestMainUpdate:
    """Tests for main() - update scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule.Client")
    def test_update_changed(self, mock_client_cls):
        """Update when desired state differs from current."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_RULE
        mock_client.put.return_value = {"id": "rule-123", "name": "CPU Alert"}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "rule_id": "rule-123",
            "name": "CPU Alert",
            "rule_type_id": ".es-query",
            "consumer": "alerts",
            "schedule": {"interval": "5m"},  # changed
            "actions": [],
            "params": {"index": ["metrics-*"]},
            "tags": ["production"],
            "enabled": True,
            "throttle": None,
            "notify_when": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_called_once()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule.Client")
    def test_idempotent_no_change(self, mock_client_cls):
        """No change when desired matches current state."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_RULE
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "rule_id": "rule-123",
            "name": "CPU Alert",
            "rule_type_id": ".es-query",
            "consumer": "alerts",
            "schedule": {"interval": "1m"},
            "actions": [],
            "params": {
                "index": ["metrics-*"],
                "timeField": "@timestamp",
                "esQuery": '{"query": {"match_all": {}}}',
                "threshold": [1000],
                "thresholdComparator": ">",
            },
            "tags": ["production"],
            "enabled": True,
            "throttle": None,
            "notify_when": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_not_called()


class TestMainDelete:
    """Tests for main() - delete scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule.Client")
    def test_delete_existing(self, mock_client_cls):
        """Delete an existing alerting rule."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_RULE
        mock_client.delete.return_value = {}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "rule_id": "rule-123",
            "name": None,
            "rule_type_id": None,
            "consumer": None,
            "schedule": None,
            "actions": [],
            "params": None,
            "tags": [],
            "enabled": True,
            "throttle": None,
            "notify_when": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_called_once_with("/api/alerting/rule/rule-123")

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule.Client")
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
            "name": None,
            "rule_type_id": None,
            "consumer": None,
            "schedule": None,
            "actions": [],
            "params": None,
            "tags": [],
            "enabled": True,
            "throttle": None,
            "notify_when": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule.Client")
    def test_delete_check_mode(self, mock_client_cls):
        """Check mode on delete reports changed but does not call DELETE."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_RULE
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "rule_id": "rule-123",
            "name": None,
            "rule_type_id": None,
            "consumer": None,
            "schedule": None,
            "actions": [],
            "params": None,
            "tags": [],
            "enabled": True,
            "throttle": None,
            "notify_when": None,
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_alerting_rule.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises ClientError."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"id": "rule-123", "name": "CPU Alert"}
        mock_client.put.side_effect = ClientError("Server error", status_code=500)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "rule_id": "rule-123",
            "name": "CPU Alert Updated",
            "rule_type_id": ".es-query",
            "consumer": "alerts",
            "schedule": {"interval": "5m"},
            "actions": [],
            "params": {"index": ["metrics-*"]},
            "tags": [],
            "enabled": True,
            "throttle": None,
            "notify_when": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_alerting_rule.main()

        assert exc_info.value.code == 1
