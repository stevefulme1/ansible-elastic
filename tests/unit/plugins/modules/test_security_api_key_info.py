# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import security_api_key_info
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


class TestFetchSingle:
    def test_returns_key_by_id(self):
        client = MagicMock()
        client.get.return_value = {
            "api_keys": [{"id": "key-123", "name": "my-key"}]
        }

        result = security_api_key_info.fetch_single(client, key_id="key-123")
        assert result is not None
        assert result["id"] == "key-123"

    def test_returns_key_by_name(self):
        client = MagicMock()
        client.get.return_value = {
            "api_keys": [{"id": "key-123", "name": "my-key"}]
        }

        result = security_api_key_info.fetch_single(client, name="my-key")
        assert result is not None
        assert result["name"] == "my-key"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.return_value = {"api_keys": []}

        result = security_api_key_info.fetch_single(client, key_id="nonexistent")
        assert result is None

    def test_returns_none_on_404(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)

        result = security_api_key_info.fetch_single(client, key_id="bad")
        assert result is None

    def test_raises_on_non_404_error(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Server error", status_code=500)

        with pytest.raises(ClientError):
            security_api_key_info.fetch_single(client, key_id="bad")


class TestFetchList:
    def test_returns_all_keys(self):
        client = MagicMock()
        client.get.return_value = {
            "api_keys": [
                {"id": "key-1", "name": "key-a"},
                {"id": "key-2", "name": "key-b"},
            ]
        }
        module = MagicMock()

        result = security_api_key_info.fetch_list(client, module)
        assert len(result) == 2

    def test_returns_empty_on_404(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()

        result = security_api_key_info.fetch_list(client, module)
        assert result == []

    def test_raises_on_non_404_error(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Server error", status_code=500)
        module = MagicMock()

        with pytest.raises(ClientError):
            security_api_key_info.fetch_list(client, module)


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key_info.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key_info.AnsibleModule")
    def test_get_by_id(self, mock_module_cls, mock_client_cls):
        mock_module = MagicMock()
        mock_module.params = {
            "api_key": "test-key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
            "id": "key-123",
            "name": None,
        }
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {
            "api_keys": [{"id": "key-123", "name": "my-key"}]
        }
        mock_client_cls.return_value = mock_client

        security_api_key_info.main()

        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert len(result["security_api_keys"]) == 1

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key_info.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key_info.AnsibleModule")
    def test_get_by_name(self, mock_module_cls, mock_client_cls):
        mock_module = MagicMock()
        mock_module.params = {
            "api_key": "test-key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
            "id": None,
            "name": "my-key",
        }
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {
            "api_keys": [{"id": "key-123", "name": "my-key"}]
        }
        mock_client_cls.return_value = mock_client

        security_api_key_info.main()

        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert len(result["security_api_keys"]) == 1

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key_info.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_api_key_info.AnsibleModule")
    def test_list_all(self, mock_module_cls, mock_client_cls):
        mock_module = MagicMock()
        mock_module.params = {
            "api_key": "test-key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
            "id": None,
            "name": None,
        }
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {
            "api_keys": [
                {"id": "key-1", "name": "key-a"},
                {"id": "key-2", "name": "key-b"},
            ]
        }
        mock_client_cls.return_value = mock_client

        security_api_key_info.main()

        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert len(result["security_api_keys"]) == 2
