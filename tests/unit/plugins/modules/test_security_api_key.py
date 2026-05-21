# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import security_api_key
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:9200",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "name": "my-api-key",
        "id": None,
        "expiration": "30d",
        "role_descriptors": {},
        "metadata": {},
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:9200",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "name": "my-api-key",
        "id": "key-id-123",
        "expiration": None,
        "role_descriptors": None,
        "metadata": None,
    }


@pytest.fixture
def existing_api_key():
    return {
        "id": "key-id-123",
        "name": "my-api-key",
        "creation": 1609459200000,
        "invalidated": False,
    }


class TestGetCurrentState:
    def test_returns_key_when_exists(self):
        client = MagicMock()
        client.get.return_value = {
            "api_keys": [
                {"id": "key-id-123", "name": "my-api-key", "invalidated": False}
            ]
        }
        module = MagicMock()
        module.params = {"id": None, "name": "my-api-key"}

        result = security_api_key.get_current_state(client, module)
        assert result is not None
        assert result["id"] == "key-id-123"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.return_value = {"api_keys": []}
        module = MagicMock()
        module.params = {"id": None, "name": "nonexistent"}

        result = security_api_key.get_current_state(client, module)
        assert result is None

    def test_filters_out_invalidated_keys(self):
        client = MagicMock()
        client.get.return_value = {
            "api_keys": [
                {"id": "key-1", "name": "my-api-key", "invalidated": True},
            ]
        }
        module = MagicMock()
        module.params = {"id": None, "name": "my-api-key"}

        result = security_api_key.get_current_state(client, module)
        assert result is None

    def test_returns_none_on_client_error(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"id": None, "name": "my-api-key"}

        result = security_api_key.get_current_state(client, module)
        assert result is None


class TestBuildPayload:
    def test_builds_full_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = security_api_key.build_payload(module)
        assert payload["name"] == "my-api-key"
        assert payload["expiration"] == "30d"
        assert payload["role_descriptors"] == {}
        assert payload["metadata"] == {}


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"api_keys": []}
        mock_client.post.return_value = {
            "id": "new-key-id",
            "api_key": "the-secret-key",
            "name": "my-api-key",
        }
        mock_client_cls.return_value = mock_client

        security_api_key.main()

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/_security/api_key" in call_args[0]
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True
        assert result["id"] == "new-key-id"
        assert result["api_key"] == "the-secret-key"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"api_keys": []}
        mock_client_cls.return_value = mock_client

        security_api_key.main()

        mock_client.post.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key.AnsibleModule")
    def test_idempotent_no_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_api_key):
        """API keys cannot be updated - if key exists, no change."""
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"api_keys": [existing_api_key]}
        mock_client_cls.return_value = mock_client

        security_api_key.main()

        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert result["id"] == "key-id-123"

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_api_key):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"api_keys": [existing_api_key]}
        mock_client._request.return_value = {"invalidated_api_keys": ["key-id-123"]}
        mock_client_cls.return_value = mock_client

        security_api_key.main()

        mock_client._request.assert_called_once_with(
            "DELETE",
            "/_security/api_key",
            data={"ids": ["key-id-123"]},
        )
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"api_keys": []}
        mock_client_cls.return_value = mock_client

        security_api_key.main()

        mock_client._request.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
