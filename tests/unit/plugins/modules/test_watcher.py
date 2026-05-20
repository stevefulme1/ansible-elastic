# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.watcher module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

# Import module under test
from ansible_collections.stevefulme1.elastic.plugins.modules import watcher
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


def set_module_args(args):
    """Prepare arguments so that they will be picked up during module creation."""
    if "_ansible_remote_tmp" not in args:
        args["_ansible_remote_tmp"] = "/tmp"
    if "_ansible_keep_remote_files" not in args:
        args["_ansible_keep_remote_files"] = False
    args_json = json.dumps({"ANSIBLE_MODULE_ARGS": args})
    basic._ANSIBLE_ARGS = to_bytes(args_json)
    # Ansible 2.21+ requires a serialization profile
    basic._ANSIBLE_PROFILE = "legacy"


def get_exit_json_result(mock_exit):
    """Extract the result dict from a mocked exit_json call."""
    args, kwargs = mock_exit.call_args
    return kwargs if kwargs else args[0]


SAMPLE_WATCH = {
    "trigger": {"schedule": {"interval": "10s"}},
    "input": {
        "search": {
            "request": {
                "indices": ["logs"],
                "body": {"query": {"match": {"status": "error"}}},
            }
        }
    },
    "condition": {"compare": {"ctx.payload.hits.total": {"gt": 0}}},
    "actions": {"log_error": {"logging": {"text": "Found errors"}}},
    "active": True,
}

SAMPLE_GET_RESPONSE = {
    "_id": "test_watch",
    "found": True,
    "_version": 1,
    "watch": dict(SAMPLE_WATCH),
}

BASE_ARGS = {
    "api_key": "test-key",
    "api_url": "https://localhost:9200",
    "validate_certs": False,
    "request_timeout": 30,
}


class TestGetCurrentState:
    """Tests for get_current_state function."""

    def test_found(self):
        """Return watch dict when found=True."""
        client = MagicMock()
        client.get.return_value = SAMPLE_GET_RESPONSE
        module = MagicMock()
        module.params = {"watch_id": "test_watch"}

        result = watcher.get_current_state(client, module)

        client.get.assert_called_once_with("/_watcher/watch/test_watch")
        assert result is not None
        assert result["_id"] == "test_watch"
        assert result["trigger"] == SAMPLE_WATCH["trigger"]

    def test_not_found(self):
        """Return None when found=False."""
        client = MagicMock()
        client.get.return_value = {"_id": "missing", "found": False}
        module = MagicMock()
        module.params = {"watch_id": "missing"}

        result = watcher.get_current_state(client, module)
        assert result is None

    def test_client_error(self):
        """Return None when API raises ClientError (404)."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"watch_id": "nonexistent"}

        result = watcher.get_current_state(client, module)
        assert result is None

    def test_no_watch_id(self):
        """Return None when watch_id is None."""
        client = MagicMock()
        module = MagicMock()
        module.params = {"watch_id": None}

        result = watcher.get_current_state(client, module)
        assert result is None
        client.get.assert_not_called()


class TestNeedsUpdate:
    """Tests for needs_update function."""

    def test_current_none(self):
        """Return True when current is None (resource missing)."""
        assert watcher.needs_update(None, {"trigger": {}}) is True

    def test_no_changes(self):
        """Return False when desired matches current."""
        current = {"trigger": {"schedule": {"interval": "10s"}}, "active": True}
        desired = {"trigger": {"schedule": {"interval": "10s"}}, "active": True}
        assert watcher.needs_update(current, desired) is False

    def test_value_changed(self):
        """Return True when a desired value differs from current."""
        current = {"trigger": {"schedule": {"interval": "10s"}}}
        desired = {"trigger": {"schedule": {"interval": "30s"}}}
        assert watcher.needs_update(current, desired) is True

    def test_none_values_skipped(self):
        """Return False when all desired values are None."""
        current = {"trigger": {"schedule": {"interval": "10s"}}}
        desired = {"trigger": None, "actions": None}
        assert watcher.needs_update(current, desired) is False

    def test_new_key_added(self):
        """Return True when desired adds a key not in current."""
        current = {"trigger": {"schedule": {"interval": "10s"}}}
        desired = {"throttle_period": "5m"}
        assert watcher.needs_update(current, desired) is True


class TestBuildPayload:
    """Tests for build_payload function."""

    def test_full_payload(self):
        """Include all non-None params in payload."""
        module = MagicMock()
        module.params = {
            "trigger": {"schedule": {"interval": "10s"}},
            "input": {"search": {"request": {"indices": ["logs"]}}},
            "condition": {"compare": {"ctx.payload.hits.total": {"gt": 0}}},
            "actions": {"log_error": {"logging": {"text": "Found errors"}}},
            "transform": None,
            "throttle_period": "5m",
            "metadata": {"env": "production"},
            "active": True,
        }

        payload = watcher.build_payload(module)

        assert payload["trigger"] == {"schedule": {"interval": "10s"}}
        assert payload["throttle_period"] == "5m"
        assert payload["metadata"] == {"env": "production"}
        assert payload["active"] is True
        assert "transform" not in payload

    def test_minimal_payload(self):
        """Only include non-None params."""
        module = MagicMock()
        module.params = {
            "trigger": {"schedule": {"interval": "10s"}},
            "input": None,
            "condition": None,
            "actions": None,
            "transform": None,
            "throttle_period": None,
            "metadata": None,
            "active": True,
        }

        payload = watcher.build_payload(module)
        assert set(payload.keys()) == {"trigger", "active"}


class TestMainCreate:
    """Tests for main() - create scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher.Client")
    def test_create_new_watch(self, mock_client_cls):
        """Create a new watch when it does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.put.return_value = {"_id": "test_watch", "created": True, "_version": 1}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "watch_id": "test_watch",
            "trigger": {"schedule": {"interval": "10s"}},
            "input": {"search": {"request": {"indices": ["logs"]}}},
            "condition": {"compare": {"ctx.payload.hits.total": {"gt": 0}}},
            "actions": {"log_error": {"logging": {"text": "Found errors"}}},
            "transform": None,
            "throttle_period": None,
            "metadata": None,
            "active": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_called_once()
        call_args = mock_client.put.call_args
        assert call_args[0][0] == "/_watcher/watch/test_watch"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher.Client")
    def test_create_check_mode(self, mock_client_cls):
        """Check mode on create reports changed but does not call PUT."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "watch_id": "test_watch",
            "trigger": {"schedule": {"interval": "10s"}},
            "input": None,
            "condition": None,
            "actions": None,
            "transform": None,
            "throttle_period": None,
            "metadata": None,
            "active": True,
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_not_called()


class TestMainUpdate:
    """Tests for main() - update scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher.Client")
    def test_update_changed(self, mock_client_cls):
        """Update when desired state differs from current."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_GET_RESPONSE
        mock_client.put.return_value = {"_id": "test_watch", "_version": 2}

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "watch_id": "test_watch",
            "trigger": {"schedule": {"interval": "30s"}},  # changed
            "input": None,
            "condition": None,
            "actions": None,
            "transform": None,
            "throttle_period": "5m",  # new
            "metadata": None,
            "active": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_called_once()
        call_args = mock_client.put.call_args
        if len(call_args[0]) > 1:
            call_data = call_args[0][1]
        else:
            call_data = call_args[1]["data"]
        assert call_data["trigger"]["schedule"]["interval"] == "30s"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher.Client")
    def test_idempotent_no_change(self, mock_client_cls):
        """No change when desired matches current state."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_GET_RESPONSE

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "watch_id": "test_watch",
            "trigger": {"schedule": {"interval": "10s"}},
            "input": {
                "search": {
                    "request": {
                        "indices": ["logs"],
                        "body": {"query": {"match": {"status": "error"}}},
                    }
                }
            },
            "condition": {"compare": {"ctx.payload.hits.total": {"gt": 0}}},
            "actions": {"log_error": {"logging": {"text": "Found errors"}}},
            "transform": None,
            "throttle_period": None,
            "metadata": None,
            "active": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_not_called()


class TestMainDelete:
    """Tests for main() - delete scenarios."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher.Client")
    def test_delete_existing(self, mock_client_cls):
        """Delete an existing watch."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_GET_RESPONSE
        mock_client.delete.return_value = {}

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "watch_id": "test_watch",
            "trigger": None,
            "input": None,
            "condition": None,
            "actions": None,
            "transform": None,
            "throttle_period": None,
            "metadata": None,
            "active": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_called_once_with("/_watcher/watch/test_watch")

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher.Client")
    def test_delete_nonexistent(self, mock_client_cls):
        """Delete idempotent when watch does not exist."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "watch_id": "test_watch",
            "trigger": None,
            "input": None,
            "condition": None,
            "actions": None,
            "transform": None,
            "throttle_period": None,
            "metadata": None,
            "active": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher.Client")
    def test_delete_check_mode(self, mock_client_cls):
        """Check mode on delete reports changed but does not call DELETE."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_GET_RESPONSE

        args = dict(BASE_ARGS)
        args.update({
            "state": "absent",
            "watch_id": "test_watch",
            "trigger": None,
            "input": None,
            "condition": None,
            "actions": None,
            "transform": None,
            "throttle_period": None,
            "metadata": None,
            "active": True,
            "_ansible_check_mode": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_not_called()


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises ClientError."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Connection refused")

        # ClientError from get_current_state is caught, but a non-404
        # error during the full main flow will propagate
        mock_client.get.return_value = {"_id": "test_watch", "found": False}
        mock_client.put.side_effect = ClientError("Server error", status_code=500)

        args = dict(BASE_ARGS)
        args.update({
            "state": "present",
            "watch_id": "test_watch",
            "trigger": {"schedule": {"interval": "10s"}},
            "input": None,
            "condition": None,
            "actions": None,
            "transform": None,
            "throttle_period": None,
            "metadata": None,
            "active": True,
        })
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher.main()

        assert exc_info.value.code == 1
