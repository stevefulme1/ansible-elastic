# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.kibana_saved_object module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_saved_object
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


SAMPLE_SAVED_OBJECT = {
    "id": "my-index-pattern",
    "type": "index-pattern",
    "attributes": {
        "title": "logs-*",
        "timeFieldName": "@timestamp",
    },
    "references": [],
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
        """Return saved object dict when found."""
        client = MagicMock()
        client.get.return_value = SAMPLE_SAVED_OBJECT
        module = MagicMock()
        module.params = {"object_type": "index-pattern", "object_id": "my-index-pattern"}

        result = kibana_saved_object.get_current_state(client, module)

        client.get.assert_called_once_with("/api/saved_objects/index-pattern/my-index-pattern")
        assert result is not None
        assert result["id"] == "my-index-pattern"

    def test_not_found(self):
        """Return None when API raises ClientError (404)."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"object_type": "index-pattern", "object_id": "nonexistent"}

        result = kibana_saved_object.get_current_state(client, module)
        assert result is None

    def test_no_object_id(self):
        """Return None when object_id is None."""
        client = MagicMock()
        module = MagicMock()
        module.params = {"object_type": "index-pattern", "object_id": None}

        result = kibana_saved_object.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    """Tests for needs_update function."""

    def test_current_none(self):
        """Return True when current is None (resource missing)."""
        assert kibana_saved_object.needs_update(None, {"attributes": {}}) is True

    def test_no_changes(self):
        """Return False when desired matches current."""
        current = {"attributes": {"title": "logs-*"}, "references": []}
        desired = {"attributes": {"title": "logs-*"}, "references": []}
        assert kibana_saved_object.needs_update(current, desired) is False

    def test_value_changed(self):
        """Return True when a desired value differs from current."""
        current = {"attributes": {"title": "logs-*"}}
        desired = {"attributes": {"title": "metrics-*"}}
        assert kibana_saved_object.needs_update(current, desired) is True

    def test_none_values_skipped(self):
        """Return False when all desired values are None."""
        current = {"attributes": {"title": "logs-*"}}
        desired = {"attributes": None}
        assert kibana_saved_object.needs_update(current, desired) is False


class TestBuildPayload:
    """Tests for build_payload function."""

    def test_full_payload(self):
        """Include all non-None params in payload."""
        module = MagicMock()
        module.params = {
            "attributes": {"title": "logs-*", "timeFieldName": "@timestamp"},
            "references": [{"id": "ref-1", "type": "index-pattern", "name": "ref"}],
        }

        payload = kibana_saved_object.build_payload(module)

        assert payload["attributes"]["title"] == "logs-*"
        assert len(payload["references"]) == 1

    def test_minimal_payload(self):
        """Only include non-None params."""
        module = MagicMock()
        module.params = {
            "attributes": {"title": "logs-*"},
            "references": None,
        }

        payload = kibana_saved_object.build_payload(module)
        assert "references" not in payload


class TestMainCreate:
    """Tests for main() - create scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object.Client")
    def test_create_new_object(self, mock_client_cls):
        """Create a new saved object when it does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.post.return_value = SAMPLE_SAVED_OBJECT
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "object_type": "index-pattern",
            "object_id": "my-index-pattern",
            "attributes": {"title": "logs-*", "timeFieldName": "@timestamp"},
            "references": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/api/saved_objects/index-pattern/my-index-pattern"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object.Client")
    def test_create_check_mode(self, mock_client_cls):
        """Check mode on create reports changed but does not call POST."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "object_type": "index-pattern",
            "object_id": "my-index-pattern",
            "attributes": {"title": "logs-*"},
            "references": [],
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()


class TestMainUpdate:
    """Tests for main() - update scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object.Client")
    def test_update_changed(self, mock_client_cls):
        """Update when desired state differs from current."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SAVED_OBJECT
        mock_client.put.return_value = SAMPLE_SAVED_OBJECT
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "object_type": "index-pattern",
            "object_id": "my-index-pattern",
            "attributes": {"title": "metrics-*", "timeFieldName": "@timestamp"},  # changed
            "references": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_called_once()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object.Client")
    def test_idempotent_no_change(self, mock_client_cls):
        """No change when desired matches current state."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SAVED_OBJECT
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "object_type": "index-pattern",
            "object_id": "my-index-pattern",
            "attributes": {"title": "logs-*", "timeFieldName": "@timestamp"},
            "references": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_not_called()


class TestMainDelete:
    """Tests for main() - delete scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object.Client")
    def test_delete_existing(self, mock_client_cls):
        """Delete an existing saved object."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SAVED_OBJECT
        mock_client.delete.return_value = {}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "object_type": "index-pattern",
            "object_id": "my-index-pattern",
            "attributes": None,
            "references": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_called_once_with("/api/saved_objects/index-pattern/my-index-pattern")

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object.Client")
    def test_delete_nonexistent(self, mock_client_cls):
        """Delete idempotent when object does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "object_type": "index-pattern",
            "object_id": "nonexistent",
            "attributes": None,
            "references": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object.Client")
    def test_delete_check_mode(self, mock_client_cls):
        """Check mode on delete reports changed but does not call DELETE."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SAVED_OBJECT
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "object_type": "index-pattern",
            "object_id": "my-index-pattern",
            "attributes": None,
            "references": [],
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises ClientError."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SAVED_OBJECT
        mock_client.put.side_effect = ClientError("Server error", status_code=500)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "object_type": "index-pattern",
            "object_id": "my-index-pattern",
            "attributes": {"title": "changed-*"},
            "references": [],
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object.main()

        assert exc_info.value.code == 1
