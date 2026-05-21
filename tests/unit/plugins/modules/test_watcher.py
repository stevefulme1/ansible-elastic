"""Unit tests for stevefulme1.elastic.watcher module."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import MagicMock, patch
import pytest

MODULE_PATH = "ansible_collections.stevefulme1.elastic.plugins.modules.watcher"
CLIENT_PATH = "ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client"


def _build_resource(**overrides):
    """Return a mock watcher resource dict."""
    base = {
        "id": "res-123",
        "watch_id": "res-123",
        "trigger": "test-trigger",
        "input": "test-input",
        "condition": "test-condition",
        "actions": "test-actions"
    }
    base.update(overrides)
    return base


@pytest.fixture
def resource_args(module_args):
    """Module args for watcher operations."""
    module_args.update({
        "state": "present",
        "api_key": "test-api-key",
        "api_url": "https://api.example.com",
        "validate_certs": True,
        "request_timeout": 30,
        "watch_id": "test-watch_id",
        "trigger": None,
        "input": None,
        "condition": None,
        "actions": None,
        "transform": None,
        "throttle_period": None,
        "metadata": None,
        "active": None
    })
    return module_args


class TestGetCurrentState:
    """Test get_current_state() function (stub implementation)."""

    def test_returns_none_without_lookup(self, resource_args):
        """get_current_state returns None when no lookup is performed."""
        for k in list(resource_args.keys()):
            if k.endswith("_id") or k == "id" or k == "name":
                resource_args[k] = None
        mock_client = MagicMock()
        mock_module = MagicMock()
        mock_module.params = resource_args

        from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import get_current_state
        result = get_current_state(mock_client, mock_module)
        assert result is None


class TestNeedsUpdate:
    """Test needs_update() function."""

    def test_returns_true_when_no_current(self):
        """needs_update returns True when current state is None."""
        from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import needs_update
        assert needs_update(None, {"name": "test"}) is True

    def test_returns_true_when_values_differ(self):
        """needs_update returns True when desired differs from current."""
        from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import needs_update
        current = {"name": "old-name", "id": "123"}
        desired = {"name": "new-name"}
        assert needs_update(current, desired) is True

    def test_returns_false_when_values_match(self):
        """needs_update returns False when desired matches current."""
        from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import needs_update
        current = {"name": "same", "id": "123"}
        desired = {"name": "same"}
        assert needs_update(current, desired) is False

    def test_ignores_none_values_in_desired(self):
        """needs_update ignores None values in desired dict."""
        from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import needs_update
        current = {"name": "test", "description": "desc"}
        desired = {"name": "test", "description": None}
        assert needs_update(current, desired) is False


class TestBuildPayload:
    """Test build_payload() function."""

    def test_builds_payload_from_params(self, resource_args):
        """build_payload builds a dict from module params."""
        mock_module = MagicMock()
        mock_module.params = resource_args

        from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import build_payload
        payload = build_payload(mock_module)
        assert isinstance(payload, dict)

    def test_excludes_none_params(self, resource_args):
        """build_payload excludes params with None value."""
        # Set all non-required params to None
        for k in resource_args:
            if k not in ("state", "api_key", "api_url", "validate_certs", "request_timeout"):
                resource_args[k] = None

        mock_module = MagicMock()
        mock_module.params = resource_args

        from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import build_payload
        payload = build_payload(mock_module)
        for v in payload.values():
            assert v is not None


class TestCreate:
    """Test resource creation via main()."""

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_create_sets_changed(self, mock_ansible_cls, mock_client_cls, resource_args):
        """Creating a new resource sets changed=True."""
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = False
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"results": []}
        mock_client.POST.return_value = _build_resource()
        mock_client_cls.return_value = mock_client

        # Patch get_current_state to return None (new resource)
        with patch(f"{MODULE_PATH}.get_current_state", return_value=None):
            from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import main
            main()

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]["changed"] is True

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_create_check_mode_no_api_call(self, mock_ansible_cls, mock_client_cls, resource_args):
        """In check mode, no API call is made for create."""
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = True
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        with patch(f"{MODULE_PATH}.get_current_state", return_value=None):
            from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import main
            main()

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]["changed"] is True
        mock_client.POST.assert_not_called()


class TestDelete:
    """Test resource deletion via main()."""

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_delete_existing_sets_changed(self, mock_ansible_cls, mock_client_cls, resource_args):
        """Deleting an existing resource sets changed=True."""
        resource_args["state"] = "absent"
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = False
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        existing = _build_resource()
        with patch(f"{MODULE_PATH}.get_current_state", return_value=existing):
            from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import main
            main()

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]["changed"] is True

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_delete_nonexistent_no_change(self, mock_ansible_cls, mock_client_cls, resource_args):
        """Deleting a nonexistent resource sets changed=False."""
        resource_args["state"] = "absent"
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = False
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        with patch(f"{MODULE_PATH}.get_current_state", return_value=None):
            from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import main
            main()

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]["changed"] is False

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_delete_check_mode_no_api_call(self, mock_ansible_cls, mock_client_cls, resource_args):
        """In check mode, no API call is made for delete."""
        resource_args["state"] = "absent"
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = True
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        existing = _build_resource()
        with patch(f"{MODULE_PATH}.get_current_state", return_value=existing):
            from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import main
            main()

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]["changed"] is True
        mock_client.delete.assert_not_called()


class TestUpdate:
    """Test resource update via main()."""

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_update_when_changed(self, mock_ansible_cls, mock_client_cls, resource_args):
        """Updating a resource when values differ sets changed=True."""
        resource_args["trigger"] = "new-value"
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = False
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.put.return_value = _build_resource(trigger="new-value")
        mock_client_cls.return_value = mock_client

        existing = _build_resource(trigger="old-value")
        with patch(f"{MODULE_PATH}.get_current_state", return_value=existing), \
             patch(f"{MODULE_PATH}.needs_update", return_value=True):
            from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import main
            main()

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]["changed"] is True


class TestIdempotent:
    """Test idempotent behavior when no change is needed."""

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_no_change_when_up_to_date(self, mock_ansible_cls, mock_client_cls, resource_args):
        """When resource is up-to-date, changed is False."""
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = False
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Build existing resource that matches all desired params
        existing = _build_resource()
        for k, v in resource_args.items():
            if v is not None and k not in ("state", "api_key", "api_url", "validate_certs", "request_timeout"):
                existing[k] = v

        with patch(f"{MODULE_PATH}.get_current_state", return_value=existing), \
             patch(f"{MODULE_PATH}.needs_update", return_value=False):
            from ansible_collections.stevefulme1.elastic.plugins.modules.watcher import main
            main()

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]["changed"] is False
        mock_client.POST.assert_not_called()
        mock_client.put.assert_not_called()
