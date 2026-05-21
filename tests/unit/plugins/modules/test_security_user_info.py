# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import security_user_info
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


class TestFetchSingle:
    def test_returns_user_when_exists(self):
        client = MagicMock()
        client.get.return_value = {"john_doe": {"roles": ["admin"], "enabled": True}}

        result = security_user_info.fetch_single(client, "john_doe")
        assert result is not None
        assert result["roles"] == ["admin"]
        assert result["username"] == "john_doe"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)

        result = security_user_info.fetch_single(client, "nonexistent")
        assert result is None


class TestFetchList:
    def test_returns_all_users(self):
        client = MagicMock()
        client.get.return_value = {
            "alice": {"roles": ["admin"]},
            "bob": {"roles": ["viewer"]},
        }
        module = MagicMock()

        result = security_user_info.fetch_list(client, module)
        assert len(result) == 2
        usernames = [u["username"] for u in result]
        assert "alice" in usernames
        assert "bob" in usernames


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user_info.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user_info.AnsibleModule")
    def test_get_single(self, mock_module_cls, mock_client_cls):
        mock_module = MagicMock()
        mock_module.params = {
            "api_key": "test-key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
            "username": "john_doe",
        }
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"john_doe": {"roles": ["admin"]}}
        mock_client_cls.return_value = mock_client

        security_user_info.main()

        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert len(result["security_users"]) == 1

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user_info.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user_info.AnsibleModule")
    def test_list_all(self, mock_module_cls, mock_client_cls):
        mock_module = MagicMock()
        mock_module.params = {
            "api_key": "test-key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
            "username": None,
        }
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {
            "alice": {"roles": ["admin"]},
            "bob": {"roles": ["viewer"]},
        }
        mock_client_cls.return_value = mock_client

        security_user_info.main()

        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert len(result["security_users"]) == 2
