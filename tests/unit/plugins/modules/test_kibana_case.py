# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.kibana_case module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_case
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


SAMPLE_CASE = {
    "id": "case-123",
    "version": "WzEsMV0=",
    "title": "Server Down",
    "description": "Production server unresponsive",
    "tags": ["incident"],
    "severity": "medium",
    "status": "open",
    "connector": {
        "id": "none",
        "name": "none",
        "type": ".none",
        "fields": None,
    },
    "settings": {"syncAlerts": True},
    "owner": "cases",
}

BASE_ARGS = {
    "api_key": "test-key",
    "api_url": "https://localhost:5601",
    "validate_certs": False,
    "request_timeout": 30,
}


class TestGetCurrentState:
    """Tests for get_current_state function."""

    def test_found(self):
        """Return case dict when found."""
        client = MagicMock()
        client.get.return_value = SAMPLE_CASE
        module = MagicMock()
        module.params = {"case_id": "case-123"}

        result = kibana_case.get_current_state(client, module)

        client.get.assert_called_once_with("/api/cases/case-123")
        assert result is not None
        assert result["id"] == "case-123"
        assert result["version"] == "WzEsMV0="

    def test_not_found(self):
        """Return None when API raises ClientError (404)."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"case_id": "nonexistent"}

        result = kibana_case.get_current_state(client, module)
        assert result is None

    def test_no_case_id(self):
        """Return None when case_id is None."""
        client = MagicMock()
        module = MagicMock()
        module.params = {"case_id": None}

        result = kibana_case.get_current_state(client, module)
        assert result is None
        client.get.assert_not_called()


class TestNeedsUpdate:
    """Tests for needs_update function."""

    def test_current_none(self):
        """Return True when current is None (resource missing)."""
        assert kibana_case.needs_update(None, {"title": "Test"}) is True

    def test_no_changes(self):
        """Return False when desired matches current."""
        current = {"title": "Server Down", "severity": "medium"}
        desired = {"title": "Server Down", "severity": "medium"}
        assert kibana_case.needs_update(current, desired) is False

    def test_value_changed(self):
        """Return True when a desired value differs from current."""
        current = {"title": "Server Down", "severity": "medium"}
        desired = {"title": "Server Down - Resolved", "severity": "medium"}
        assert kibana_case.needs_update(current, desired) is True

    def test_none_values_skipped(self):
        """Return False when all desired values are None."""
        current = {"title": "Server Down"}
        desired = {"title": None, "tags": None}
        assert kibana_case.needs_update(current, desired) is False

    def test_status_changed(self):
        """Return True when status changes."""
        current = {"title": "Server Down", "status": "open"}
        desired = {"status": "closed"}
        assert kibana_case.needs_update(current, desired) is True


class TestBuildPayload:
    """Tests for build_payload function."""

    def test_full_payload_create(self):
        """Include all params plus defaults on create."""
        module = MagicMock()
        module.params = {
            "title": "Server Down",
            "description": "Production server unresponsive",
            "tags": ["incident"],
            "severity": "medium",
            "connector": None,
            "settings": None,
            "owner": None,
        }

        payload = kibana_case.build_payload(module, for_create=True)

        assert payload["title"] == "Server Down"
        assert payload["description"] == "Production server unresponsive"
        assert payload["tags"] == ["incident"]
        assert payload["severity"] == "medium"
        assert payload["connector"]["id"] == "none"
        assert payload["settings"]["syncAlerts"] is True
        assert payload["owner"] == "cases"
        assert "status" not in payload

    def test_payload_update_no_defaults(self):
        """Exclude defaults on update when not explicitly set."""
        module = MagicMock()
        module.params = {
            "title": "Updated Title",
            "description": None,
            "tags": None,
            "severity": None,
            "status": "closed",
            "connector": None,
            "settings": None,
            "owner": None,
        }

        payload = kibana_case.build_payload(module, for_create=False)

        assert payload["title"] == "Updated Title"
        assert payload["status"] == "closed"
        assert "connector" not in payload
        assert "settings" not in payload
        assert "owner" not in payload
        assert "description" not in payload


class TestMainCreate:
    """Tests for main() - create scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case.Client")
    def test_create_new_case(self, mock_client_cls):
        """Create a new case when it does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.post.return_value = {"id": "case-new", "version": "WzEsMV0=", "title": "Server Down"}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "case_id": None,
            "title": "Server Down",
            "description": "Production server unresponsive",
            "tags": ["incident"],
            "severity": "medium",
            "connector": None,
            "settings": None,
            "owner": "cases",
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/api/cases"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case.Client")
    def test_create_check_mode(self, mock_client_cls):
        """Check mode on create reports changed but does not call POST."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "case_id": None,
            "title": "Server Down",
            "description": "Production server unresponsive",
            "tags": None,
            "severity": "medium",
            "connector": None,
            "settings": None,
            "owner": "cases",
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()


class TestMainUpdate:
    """Tests for main() - update scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case.Client")
    def test_update_changed(self, mock_client_cls):
        """Update when desired state differs from current."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_CASE
        mock_client.patch.return_value = [{"id": "case-123", "version": "WzIsMV0=", "title": "Updated"}]

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "case_id": "case-123",
            "title": "Server Down - Resolved",
            "description": None,
            "tags": None,
            "severity": "medium",
            "connector": None,
            "settings": None,
            "owner": "cases",
            "status": "closed",
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case.main()

        assert exc_info.value.code == 0
        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        assert call_args[0][0] == "/api/cases"
        patch_data = call_args[1].get("data") or call_args[0][1]
        # Verify version is included in the update payload
        assert patch_data["cases"][0]["version"] == "WzEsMV0="
        assert patch_data["cases"][0]["id"] == "case-123"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case.Client")
    def test_update_includes_version(self, mock_client_cls):
        """Verify that version from GET is included in PATCH payload."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_CASE
        mock_client.patch.return_value = [{"id": "case-123", "version": "WzIsMV0="}]

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "case_id": "case-123",
            "title": "New Title",
            "description": None,
            "tags": None,
            "severity": "medium",
            "connector": None,
            "settings": None,
            "owner": "cases",
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case.main()

        assert exc_info.value.code == 0
        patch_data = mock_client.patch.call_args[1].get("data") or mock_client.patch.call_args[0][1]
        case_update = patch_data["cases"][0]
        assert case_update["version"] == "WzEsMV0="
        assert case_update["id"] == "case-123"
        assert case_update["title"] == "New Title"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case.Client")
    def test_idempotent_no_change(self, mock_client_cls):
        """No change when desired matches current state."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_CASE

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "case_id": "case-123",
            "title": "Server Down",
            "description": "Production server unresponsive",
            "tags": ["incident"],
            "severity": "medium",
            "connector": None,
            "settings": None,
            "owner": "cases",
            "status": "open",
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case.main()

        assert exc_info.value.code == 0
        mock_client.patch.assert_not_called()


class TestMainDelete:
    """Tests for main() - delete scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case.Client")
    def test_delete_existing(self, mock_client_cls):
        """Delete an existing case."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_CASE
        mock_client._request.return_value = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "case_id": "case-123",
            "title": "unused",
            "description": None,
            "tags": None,
            "severity": "medium",
            "connector": None,
            "settings": None,
            "owner": "cases",
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case.main()

        assert exc_info.value.code == 0
        mock_client._request.assert_called_once_with(
            "DELETE",
            "/api/cases",
            data={"ids": ["case-123"]},
        )

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case.Client")
    def test_delete_nonexistent(self, mock_client_cls):
        """Delete idempotent when case does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "case_id": "nonexistent",
            "title": "unused",
            "description": None,
            "tags": None,
            "severity": "medium",
            "connector": None,
            "settings": None,
            "owner": "cases",
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case.main()

        assert exc_info.value.code == 0
        mock_client._request.assert_not_called()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case.Client")
    def test_delete_check_mode(self, mock_client_cls):
        """Check mode on delete reports changed but does not call DELETE."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_CASE

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "case_id": "case-123",
            "title": "unused",
            "description": None,
            "tags": None,
            "severity": "medium",
            "connector": None,
            "settings": None,
            "owner": "cases",
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case.main()

        assert exc_info.value.code == 0
        mock_client._request.assert_not_called()


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_case.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises ClientError."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"id": None}
        mock_client.post.side_effect = ClientError("Server error", status_code=500)

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "case_id": None,
            "title": "Server Down",
            "description": "Production server unresponsive",
            "tags": None,
            "severity": "medium",
            "connector": None,
            "settings": None,
            "owner": "cases",
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_case.main()

        assert exc_info.value.code == 1
