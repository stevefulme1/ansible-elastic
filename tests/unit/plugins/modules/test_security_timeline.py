# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.security_timeline module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import security_timeline
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


SAMPLE_TIMELINE = {
    "savedObjectId": "timeline-123",
    "title": "Investigation",
    "description": "Security investigation timeline",
    "timelineType": "default",
    "columns": [],
    "dataProviders": [],
    "kqlMode": "filter",
    "version": "WzEyMzQ1LDFd",
}

BASE_ARGS = {
    "api_key": "test-key",
    "api_url": "https://localhost:5601",
    "validate_certs": False,
    "request_timeout": 30,
}


class TestGetCurrentState:
    """Tests for get_current_state function."""

    def test_found_by_timeline_id(self):
        """Return timeline dict when found by timeline_id."""
        client = MagicMock()
        client.get.return_value = {"timeline": SAMPLE_TIMELINE}
        module = MagicMock()
        module.params = {"timeline_id": "timeline-123", "title": None}

        result = security_timeline.get_current_state(client, module)

        client.get.assert_called_once_with(
            "/api/timelines",
            params={"id": "timeline-123"},
        )
        assert result is not None
        assert result["savedObjectId"] == "timeline-123"

    def test_found_by_title(self):
        """Return timeline dict when found by title in list."""
        client = MagicMock()
        client.get.return_value = {"timeline": [SAMPLE_TIMELINE], "totalCount": 1}
        module = MagicMock()
        module.params = {"timeline_id": None, "title": "Investigation"}

        result = security_timeline.get_current_state(client, module)

        assert result is not None
        assert result["title"] == "Investigation"

    def test_not_found(self):
        """Return None when API raises ClientError (404)."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"timeline_id": "nonexistent", "title": None}

        result = security_timeline.get_current_state(client, module)
        assert result is None

    def test_no_identifier(self):
        """Return None when both timeline_id and title are None."""
        client = MagicMock()
        module = MagicMock()
        module.params = {"timeline_id": None, "title": None}

        result = security_timeline.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    """Tests for needs_update function."""

    def test_current_none(self):
        """Return True when current is None."""
        assert security_timeline.needs_update(None, {"title": "test"}) is True

    def test_no_changes(self):
        """Return False when desired matches current."""
        current = {"title": "Investigation", "kqlMode": "filter"}
        desired = {"title": "Investigation", "kqlMode": "filter"}
        assert security_timeline.needs_update(current, desired) is False

    def test_value_changed(self):
        """Return True when a desired value differs from current."""
        current = {"title": "Investigation", "description": "old"}
        desired = {"title": "Investigation", "description": "new"}
        assert security_timeline.needs_update(current, desired) is True

    def test_none_values_skipped(self):
        """Return False when all desired values are None."""
        current = {"title": "Investigation"}
        desired = {"title": None, "description": None}
        assert security_timeline.needs_update(current, desired) is False


class TestBuildTimelineBody:
    """Tests for build_timeline_body function."""

    def test_full_body(self):
        """Include all non-None params in body with camelCase keys."""
        module = MagicMock()
        module.params = {
            "title": "Investigation",
            "description": "Security investigation",
            "timeline_type": "default",
            "columns": [],
            "data_providers": [],
            "kql_mode": "filter",
            "sort": None,
        }

        body = security_timeline.build_timeline_body(module)

        assert body["title"] == "Investigation"
        assert body["timelineType"] == "default"
        assert body["dataProviders"] == []
        assert body["kqlMode"] == "filter"
        assert "sort" not in body


class TestMainCreate:
    """Tests for main() - create scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_timeline.Client")
    def test_create_new_timeline(self, mock_client_cls):
        """Create a new timeline when it does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.post.return_value = {
            "data": {
                "savedObjectId": "timeline-123",
                "title": "Investigation",
                "version": "WzEyMzQ1LDFd",
            }
        }
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "timeline_id": "timeline-123",
            "title": "Investigation",
            "description": "Security investigation",
            "timeline_type": "default",
            "columns": [],
            "data_providers": [],
            "kql_mode": "filter",
            "sort": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_timeline.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        # Create uses POST /api/timeline (singular) with wrapped body
        assert call_args[0][0] == "/api/timeline"
        payload = call_args[1].get("data", call_args[0][1] if len(call_args[0]) > 1 else {})
        assert "timeline" in payload

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_timeline.Client")
    def test_create_check_mode(self, mock_client_cls):
        """Check mode on create reports changed but does not call POST."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "timeline_id": "timeline-123",
            "title": "Investigation",
            "description": "Security investigation",
            "timeline_type": "default",
            "columns": [],
            "data_providers": [],
            "kql_mode": "filter",
            "sort": None,
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_timeline.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()


class TestMainUpdate:
    """Tests for main() - update scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_timeline.Client")
    def test_update_changed(self, mock_client_cls):
        """Update when desired state differs from current, using PATCH with version."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"timeline": SAMPLE_TIMELINE}
        mock_client.patch.return_value = {
            "data": {
                "savedObjectId": "timeline-123",
                "title": "Investigation - Updated",
                "version": "WzEyMzQ2LDFd",
            }
        }
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "timeline_id": "timeline-123",
            "title": "Investigation - Updated",  # changed
            "description": "Security investigation timeline",
            "timeline_type": "default",
            "columns": [],
            "data_providers": [],
            "kql_mode": "filter",
            "sort": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_timeline.main()

        assert exc_info.value.code == 0
        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        assert call_args[0][0] == "/api/timeline"
        payload = call_args[1].get("data", call_args[0][1] if len(call_args[0]) > 1 else {})
        assert payload.get("timelineId") == "timeline-123"
        assert payload.get("version") == "WzEyMzQ1LDFd"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_timeline.Client")
    def test_idempotent_no_change(self, mock_client_cls):
        """No change when desired matches current state."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"timeline": SAMPLE_TIMELINE}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "timeline_id": "timeline-123",
            "title": "Investigation",
            "description": "Security investigation timeline",
            "timeline_type": "default",
            "columns": [],
            "data_providers": [],
            "kql_mode": "filter",
            "sort": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_timeline.main()

        assert exc_info.value.code == 0
        mock_client.patch.assert_not_called()


class TestMainDelete:
    """Tests for main() - delete scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_timeline.Client")
    def test_delete_existing(self, mock_client_cls):
        """Delete an existing timeline using body with savedObjectIds."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"timeline": SAMPLE_TIMELINE}
        mock_client._request.return_value = {}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "timeline_id": "timeline-123",
            "title": None,
            "description": None,
            "timeline_type": "default",
            "columns": [],
            "data_providers": [],
            "kql_mode": "filter",
            "sort": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_timeline.main()

        assert exc_info.value.code == 0
        mock_client._request.assert_called_once_with(
            "DELETE",
            "/api/timelines",
            data={"savedObjectIds": ["timeline-123"]},
        )

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_timeline.Client")
    def test_delete_nonexistent(self, mock_client_cls):
        """Delete idempotent when timeline does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "timeline_id": "nonexistent",
            "title": None,
            "description": None,
            "timeline_type": "default",
            "columns": [],
            "data_providers": [],
            "kql_mode": "filter",
            "sort": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_timeline.main()

        assert exc_info.value.code == 0
        mock_client._request.assert_not_called()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_timeline.Client")
    def test_delete_check_mode(self, mock_client_cls):
        """Check mode on delete reports changed but does not call DELETE."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"timeline": SAMPLE_TIMELINE}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "timeline_id": "timeline-123",
            "title": None,
            "description": None,
            "timeline_type": "default",
            "columns": [],
            "data_providers": [],
            "kql_mode": "filter",
            "sort": None,
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_timeline.main()

        assert exc_info.value.code == 0
        mock_client._request.assert_not_called()


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_timeline.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises ClientError."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"timeline": SAMPLE_TIMELINE}
        mock_client.patch.side_effect = ClientError("Server error", status_code=500)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "timeline_id": "timeline-123",
            "title": "Investigation - Updated",
            "description": "Updated",
            "timeline_type": "default",
            "columns": [],
            "data_providers": [],
            "kql_mode": "filter",
            "sort": None,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_timeline.main()

        assert exc_info.value.code == 1
