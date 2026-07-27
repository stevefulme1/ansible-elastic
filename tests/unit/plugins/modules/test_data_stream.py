"""Unit tests for stevefulme1.elastic.data_stream module."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import MagicMock, patch
import pytest

MODULE_PATH = "ansible_collections.stevefulme1.elastic.plugins.modules.data_stream"
CLIENT_PATH = "ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client"


def _build_resource(**overrides):
    """Return a mock data_stream resource dict."""
    base = {
        "name": "test-name"
    }
    base.update(overrides)
    return base


@pytest.fixture
def resource_args(module_args):
    """Module args for data_stream operations."""
    module_args.update({
        "name": "test-name",
        "state": "present",
        "api_key": "test-api-key",
        "api_url": "https://api.example.com",
        "validate_certs": True,
        "request_timeout": 30
    })
    return module_args


class TestGetCurrentState:
    """Test get_current_state() function."""

    def test_returns_matching_resource(self, resource_args):
        """get_current_state returns existing resource when found."""
        resource_args["name"] = "test-name"
        mock_client = MagicMock()
        existing = _build_resource()
        mock_client.get.return_value = {"data_streams": [existing]}

        mock_module = MagicMock()
        mock_module.params = resource_args

        from ansible_collections.stevefulme1.elastic.plugins.modules.data_stream import get_current_state
        result = get_current_state(mock_client, mock_module)
        assert result is not None

    def test_returns_none_when_not_found(self, resource_args):
        """get_current_state returns None when resource does not exist."""
        resource_args["name"] = "test-name"
        mock_client = MagicMock()
        mock_client.get.return_value = {"data_streams": []}

        mock_module = MagicMock()
        mock_module.params = resource_args

        from ansible_collections.stevefulme1.elastic.plugins.modules.data_stream import get_current_state
        result = get_current_state(mock_client, mock_module)
        assert result is None

    def test_returns_none_when_no_search_value(self, resource_args):
        """get_current_state returns None when search value is missing."""
        resource_args["name"] = None

        mock_client = MagicMock()
        mock_module = MagicMock()
        mock_module.params = resource_args

        from ansible_collections.stevefulme1.elastic.plugins.modules.data_stream import get_current_state
        result = get_current_state(mock_client, mock_module)
        assert result is None

    def test_handles_client_error_404(self, resource_args):
        """get_current_state returns None on 404 error."""
        resource_args["name"] = "test-name"
        from ansible_collections.stevefulme1.elastic.plugins.modules.data_stream import get_current_state
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        mock_module = MagicMock()
        mock_module.params = resource_args

        result = get_current_state(mock_client, mock_module)
        assert result is None

    def test_handles_client_error_non_404(self, resource_args):
        """get_current_state raises exception on non-404 error."""
        resource_args["name"] = "test-name"
        from ansible_collections.stevefulme1.elastic.plugins.modules.data_stream import get_current_state
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Server error", status_code=500)

        mock_module = MagicMock()
        mock_module.params = resource_args

        with pytest.raises(ClientError):
            get_current_state(mock_client, mock_module)


class TestCreate:
    """Test resource creation via main()."""

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_create_sets_changed(self, mock_ansible_cls, mock_client_cls, resource_args):
        """Creating a new resource sets changed=True."""
        resource_args["name"] = "test-name"
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = False
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"data_streams": []}
        mock_client.put.return_value = {"acknowledged": True}
        mock_client_cls.return_value = mock_client

        # Patch get_current_state to return None (new resource)
        with patch(f"{MODULE_PATH}.get_current_state", return_value=None):
            from ansible_collections.stevefulme1.elastic.plugins.modules.data_stream import main
            main()

        mock_module.exit_json.assert_called_once()
        result_args = mock_module.exit_json.call_args[1]
        assert result_args["changed"] is True
        assert "api_response" in result_args

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_create_check_mode_no_api_call(self, mock_ansible_cls, mock_client_cls, resource_args):
        """In check mode, no API call is made for create."""
        resource_args["name"] = "test-name"
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = True
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        with patch(f"{MODULE_PATH}.get_current_state", return_value=None):
            from ansible_collections.stevefulme1.elastic.plugins.modules.data_stream import main
            main()

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]["changed"] is True
        mock_client.put.assert_not_called()


class TestDelete:
    """Test resource deletion via main()."""

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_delete_existing_sets_changed(self, mock_ansible_cls, mock_client_cls, resource_args):
        """Deleting an existing resource sets changed=True."""
        resource_args["state"] = "absent"
        resource_args["name"] = "test-name"
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = False
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.delete.return_value = {"acknowledged": True}
        mock_client_cls.return_value = mock_client

        existing = _build_resource()
        with patch(f"{MODULE_PATH}.get_current_state", return_value=existing):
            from ansible_collections.stevefulme1.elastic.plugins.modules.data_stream import main
            main()

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]["changed"] is True

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_delete_nonexistent_no_change(self, mock_ansible_cls, mock_client_cls, resource_args):
        """Deleting a nonexistent resource sets changed=False."""
        resource_args["state"] = "absent"
        resource_args["name"] = "test-name"
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = False
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        with patch(f"{MODULE_PATH}.get_current_state", return_value=None):
            from ansible_collections.stevefulme1.elastic.plugins.modules.data_stream import main
            main()

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]["changed"] is False

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_delete_check_mode_no_api_call(self, mock_ansible_cls, mock_client_cls, resource_args):
        """In check mode, no API call is made for delete."""
        resource_args["state"] = "absent"
        resource_args["name"] = "test-name"
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = True
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        existing = _build_resource()
        with patch(f"{MODULE_PATH}.get_current_state", return_value=existing):
            from ansible_collections.stevefulme1.elastic.plugins.modules.data_stream import main
            main()

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]["changed"] is True
        mock_client.delete.assert_not_called()


class TestIdempotent:
    """Test idempotent behavior when no change is needed."""

    @patch(f"{MODULE_PATH}.Client")
    @patch(f"{MODULE_PATH}.AnsibleModule")
    def test_no_change_when_up_to_date(self, mock_ansible_cls, mock_client_cls, resource_args):
        """When resource exists, changed is False."""
        resource_args["name"] = "test-name"
        mock_module = MagicMock()
        mock_module.params = resource_args
        mock_module.check_mode = False
        mock_ansible_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Build existing resource that matches
        existing = _build_resource(name="test-name")

        with patch(f"{MODULE_PATH}.get_current_state", return_value=existing):
            from ansible_collections.stevefulme1.elastic.plugins.modules.data_stream import main
            main()

        mock_module.exit_json.assert_called_once()
        result_args = mock_module.exit_json.call_args[1]
        assert result_args["changed"] is False
        assert "api_response" in result_args
        mock_client.put.assert_not_called()
