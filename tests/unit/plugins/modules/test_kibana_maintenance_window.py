# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.kibana_maintenance_window module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_maintenance_window
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


def get_exit_json_result(mock_exit):
    """Extract the result dict from a mocked exit_json call."""
    args, kwargs = mock_exit.call_args
    return kwargs if kwargs else args[0]


SAMPLE_WINDOW = {
    "id": "mw-123",
    "title": "Planned Maintenance",
    "duration": 3600000,
    "rRule": {
        "dtstart": "2024-03-01T00:00:00.000Z",
        "tzid": "UTC",
        "freq": 0,
    },
    "category_ids": ["observability"],
    "enabled": True,
}

BASE_ARGS = {
    "api_key": "test-key",
    "api_url": "https://localhost:5601",
    "validate_certs": False,
    "request_timeout": 30,
}

REQUIRED_PARAMS = {
    "title": "Planned Maintenance",
    "duration": 3600000,
    "r_rule": {
        "dtstart": "2024-03-01T00:00:00.000Z",
        "tzid": "UTC",
        "freq": 0,
    },
}


class TestGetCurrentState:
    """Tests for get_current_state function."""

    def test_found(self):
        """Return window dict when found."""
        client = MagicMock()
        client.get.return_value = SAMPLE_WINDOW
        module = MagicMock()
        module.params = {"window_id": "mw-123"}

        result = kibana_maintenance_window.get_current_state(client, module)

        client.get.assert_called_once_with("/api/maintenance_window/mw-123")
        assert result is not None
        assert result["id"] == "mw-123"
        assert result["title"] == "Planned Maintenance"

    def test_not_found(self):
        """Return None when API raises ClientError (404)."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"window_id": "nonexistent"}

        result = kibana_maintenance_window.get_current_state(client, module)
        assert result is None

    def test_no_window_id(self):
        """Return None when window_id is None."""
        client = MagicMock()
        module = MagicMock()
        module.params = {"window_id": None}

        result = kibana_maintenance_window.get_current_state(client, module)
        assert result is None
        client.get.assert_not_called()


class TestNeedsUpdate:
    """Tests for needs_update function."""

    def test_current_none(self):
        """Return True when current is None (resource missing)."""
        assert kibana_maintenance_window.needs_update(None, {"title": "Test"}) is True

    def test_no_changes(self):
        """Return False when desired matches current."""
        current = {"title": "Planned Maintenance", "duration": 3600000}
        desired = {"title": "Planned Maintenance", "duration": 3600000}
        assert kibana_maintenance_window.needs_update(current, desired) is False

    def test_value_changed(self):
        """Return True when a desired value differs from current."""
        current = {"title": "Planned Maintenance", "duration": 3600000}
        desired = {"title": "Updated Maintenance", "duration": 3600000}
        assert kibana_maintenance_window.needs_update(current, desired) is True

    def test_none_values_skipped(self):
        """Return False when all desired values are None."""
        current = {"title": "Planned Maintenance"}
        desired = {"title": None, "category_ids": None}
        assert kibana_maintenance_window.needs_update(current, desired) is False

    def test_new_key_added(self):
        """Return True when desired adds a key not in current."""
        current = {"title": "Planned Maintenance"}
        desired = {"enabled": False}
        assert kibana_maintenance_window.needs_update(current, desired) is True


class TestBuildPayload:
    """Tests for build_payload function."""

    def test_full_payload(self):
        """Include all non-None params in payload."""
        module = MagicMock()
        module.params = {
            "title": "Planned Maintenance",
            "duration": 3600000,
            "r_rule": {"dtstart": "2024-03-01T00:00:00.000Z", "tzid": "UTC", "freq": 0},
            "category_ids": ["observability"],
            "enabled": True,
        }

        payload = kibana_maintenance_window.build_payload(module)

        assert payload["title"] == "Planned Maintenance"
        assert payload["duration"] == 3600000
        assert payload["rRule"] == {"dtstart": "2024-03-01T00:00:00.000Z", "tzid": "UTC", "freq": 0}
        assert payload["category_ids"] == ["observability"]
        assert payload["enabled"] is True

    def test_minimal_payload(self):
        """Only include non-None params."""
        module = MagicMock()
        module.params = {
            "title": "Planned Maintenance",
            "duration": 3600000,
            "r_rule": {"dtstart": "2024-03-01T00:00:00.000Z", "tzid": "UTC", "freq": 0},
            "category_ids": None,
            "enabled": None,
        }

        payload = kibana_maintenance_window.build_payload(module)
        assert set(payload.keys()) == {"title", "duration", "rRule"}


class TestMainCreate:
    """Tests for main() - create scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_maintenance_window.Client")
    def test_create_new_window(self, mock_client_cls):
        """Create a new maintenance window when it does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.post.return_value = {"id": "mw-new", "title": "Planned Maintenance"}

        args = dict(BASE_ARGS)
        args.update(REQUIRED_PARAMS)
        args.update({
            "state": "present",
            "window_id": None,
            "category_ids": ["observability"],
            "enabled": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_maintenance_window.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/api/maintenance_window"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_maintenance_window.Client")
    def test_create_check_mode(self, mock_client_cls):
        """Check mode on create reports changed but does not call POST."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        args = dict(BASE_ARGS)
        args.update(REQUIRED_PARAMS)
        args.update({
            "state": "present",
            "window_id": None,
            "category_ids": None,
            "enabled": None,
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_maintenance_window.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()


class TestMainUpdate:
    """Tests for main() - update scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_maintenance_window.Client")
    def test_update_changed(self, mock_client_cls):
        """Update when desired state differs from current."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_WINDOW
        mock_client.post.return_value = {"id": "mw-123", "title": "Updated Maintenance"}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "window_id": "mw-123",
            "title": "Updated Maintenance",
            "duration": 7200000,
            "r_rule": {"dtstart": "2024-03-01T00:00:00.000Z", "tzid": "UTC", "freq": 0},
            "category_ids": None,
            "enabled": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_maintenance_window.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/api/maintenance_window/mw-123"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_maintenance_window.Client")
    def test_idempotent_no_change(self, mock_client_cls):
        """No change when desired matches current state."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_WINDOW

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "window_id": "mw-123",
            "title": "Planned Maintenance",
            "duration": 3600000,
            "r_rule": {"dtstart": "2024-03-01T00:00:00.000Z", "tzid": "UTC", "freq": 0},
            "category_ids": ["observability"],
            "enabled": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_maintenance_window.main()

        assert exc_info.value.code == 0
        # post should not be called for update since nothing changed
        # (post is only called for create or update, not for idempotent)
        assert mock_client.post.call_count == 0


class TestMainDelete:
    """Tests for main() - delete scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_maintenance_window.Client")
    def test_delete_existing(self, mock_client_cls):
        """Delete an existing maintenance window."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_WINDOW
        mock_client.delete.return_value = {}

        args = dict(BASE_ARGS)
        args.update(REQUIRED_PARAMS)
        args.update({
            "state": "absent",
            "window_id": "mw-123",
            "category_ids": None,
            "enabled": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_maintenance_window.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_called_once_with("/api/maintenance_window/mw-123")

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_maintenance_window.Client")
    def test_delete_nonexistent(self, mock_client_cls):
        """Delete idempotent when window does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        args = dict(BASE_ARGS)
        args.update(REQUIRED_PARAMS)
        args.update({
            "state": "absent",
            "window_id": "nonexistent",
            "category_ids": None,
            "enabled": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_maintenance_window.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_maintenance_window.Client")
    def test_delete_check_mode(self, mock_client_cls):
        """Check mode on delete reports changed but does not call DELETE."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_WINDOW

        args = dict(BASE_ARGS)
        args.update(REQUIRED_PARAMS)
        args.update({
            "state": "absent",
            "window_id": "mw-123",
            "category_ids": None,
            "enabled": None,
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_maintenance_window.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_maintenance_window.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises ClientError."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"id": None}
        mock_client.post.side_effect = ClientError("Server error", status_code=500)

        args = dict(BASE_ARGS)
        args.update(REQUIRED_PARAMS)
        args.update({
            "state": "present",
            "window_id": None,
            "category_ids": None,
            "enabled": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_maintenance_window.main()

        assert exc_info.value.code == 1
