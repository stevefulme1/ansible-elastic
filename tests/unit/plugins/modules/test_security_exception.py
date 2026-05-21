# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.security_exception module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import security_exception
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


SAMPLE_EXCEPTION = {
    "id": "exc-uuid-123",
    "list_id": "trusted-processes",
    "name": "Trusted Processes",
    "description": "Processes excluded from detection",
    "type": "detection",
    "namespace_type": "single",
    "tags": [],
}

BASE_ARGS = {
    "api_key": "test-key",
    "api_url": "https://localhost:5601",
    "validate_certs": False,
    "request_timeout": 30,
}


class TestGetCurrentState:
    """Tests for get_current_state function."""

    def test_found_by_list_id(self):
        """Return exception dict when found by list_id."""
        client = MagicMock()
        client.get.return_value = SAMPLE_EXCEPTION
        module = MagicMock()
        module.params = {"exception_id": None, "list_id": "trusted-processes", "name": None}

        result = security_exception.get_current_state(client, module)

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
        module = MagicMock()
        module.params = {"exception_id": "exc-uuid-123", "list_id": None, "name": None}

        result = security_exception.get_current_state(client, module)

        client.get.assert_called_once_with(
            "/api/exception_lists",
            params={"id": "exc-uuid-123"},
        )
        assert result is not None
        assert result["id"] == "exc-uuid-123"

    def test_found_by_name(self):
        """Return exception dict when found by name in list."""
        client = MagicMock()
        client.get.return_value = {"data": [SAMPLE_EXCEPTION], "total": 1}
        module = MagicMock()
        module.params = {"exception_id": None, "list_id": None, "name": "Trusted Processes"}

        result = security_exception.get_current_state(client, module)

        assert result is not None
        assert result["name"] == "Trusted Processes"

    def test_not_found(self):
        """Return None when API raises ClientError (404)."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"exception_id": "nonexistent", "list_id": None, "name": None}

        result = security_exception.get_current_state(client, module)
        assert result is None

    def test_no_identifier(self):
        """Return None when all identifiers are None."""
        client = MagicMock()
        module = MagicMock()
        module.params = {"exception_id": None, "list_id": None, "name": None}

        result = security_exception.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    """Tests for needs_update function."""

    def test_current_none(self):
        """Return True when current is None."""
        assert security_exception.needs_update(None, {"name": "test"}) is True

    def test_no_changes(self):
        """Return False when desired matches current."""
        current = {"name": "Trusted Processes", "type": "detection"}
        desired = {"name": "Trusted Processes", "type": "detection"}
        assert security_exception.needs_update(current, desired) is False

    def test_value_changed(self):
        """Return True when a desired value differs from current."""
        current = {"name": "Trusted Processes", "description": "old"}
        desired = {"name": "Trusted Processes", "description": "new"}
        assert security_exception.needs_update(current, desired) is True

    def test_none_values_skipped(self):
        """Return False when all desired values are None."""
        current = {"name": "Trusted Processes"}
        desired = {"name": None, "description": None}
        assert security_exception.needs_update(current, desired) is False


class TestBuildPayload:
    """Tests for build_payload function."""

    def test_full_payload(self):
        """Include all non-None params in payload."""
        module = MagicMock()
        module.params = {
            "name": "Trusted Processes",
            "description": "Processes excluded from detection",
            "type": "detection",
            "namespace_type": "single",
            "list_id": "trusted-processes",
            "tags": [],
        }

        payload = security_exception.build_payload(module)

        assert payload["name"] == "Trusted Processes"
        assert payload["type"] == "detection"
        assert payload["list_id"] == "trusted-processes"
        assert payload["namespace_type"] == "single"


class TestMainCreate:
    """Tests for main() - create scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception.Client")
    def test_create_new_exception(self, mock_client_cls):
        """Create a new exception list when it does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.post.return_value = SAMPLE_EXCEPTION
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "exception_id": None,
            "list_id": "trusted-processes",
            "name": "Trusted Processes",
            "description": "Processes excluded from detection",
            "type": "detection",
            "namespace_type": "single",
            "tags": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception.Client")
    def test_create_check_mode(self, mock_client_cls):
        """Check mode on create reports changed but does not call POST."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "exception_id": None,
            "list_id": "trusted-processes",
            "name": "Trusted Processes",
            "description": "Processes excluded from detection",
            "type": "detection",
            "namespace_type": "single",
            "tags": [],
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()


class TestMainUpdate:
    """Tests for main() - update scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception.Client")
    def test_update_changed(self, mock_client_cls):
        """Update when desired state differs from current."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_EXCEPTION
        mock_client.put.return_value = SAMPLE_EXCEPTION
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "exception_id": None,
            "list_id": "trusted-processes",
            "name": "Trusted Processes - Updated",  # changed
            "description": "Updated description",  # changed
            "type": "detection",
            "namespace_type": "single",
            "tags": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_called_once()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception.Client")
    def test_idempotent_no_change(self, mock_client_cls):
        """No change when desired matches current state."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_EXCEPTION
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "exception_id": None,
            "list_id": "trusted-processes",
            "name": "Trusted Processes",
            "description": "Processes excluded from detection",
            "type": "detection",
            "namespace_type": "single",
            "tags": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_not_called()


class TestMainDelete:
    """Tests for main() - delete scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception.Client")
    def test_delete_existing(self, mock_client_cls):
        """Delete an existing exception list."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_EXCEPTION
        mock_client.delete.return_value = {}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "exception_id": "exc-uuid-123",
            "tags": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_called_once_with(
            "/api/exception_lists",
            params={"id": "exc-uuid-123"},
        )

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception.Client")
    def test_delete_nonexistent(self, mock_client_cls):
        """Delete idempotent when exception list does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "exception_id": "nonexistent",
            "tags": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception.Client")
    def test_delete_check_mode(self, mock_client_cls):
        """Check mode on delete reports changed but does not call DELETE."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_EXCEPTION
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "exception_id": "exc-uuid-123",
            "tags": [],
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_exception.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises ClientError."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_EXCEPTION
        mock_client.put.side_effect = ClientError("Server error", status_code=500)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "exception_id": None,
            "list_id": "trusted-processes",
            "name": "Updated Name",
            "description": "Updated",
            "type": "detection",
            "namespace_type": "single",
            "tags": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            security_exception.main()

        assert exc_info.value.code == 1
