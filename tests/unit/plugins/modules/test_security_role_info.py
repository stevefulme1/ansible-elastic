# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import security_role_info
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


class TestFetchSingle:
    def test_returns_role_when_exists(self):
        client = MagicMock()
        client.get.return_value = {"test_role": {"cluster": ["all"]}}

        result = security_role_info.fetch_single(client, "test_role")
        assert result is not None
        assert result["cluster"] == ["all"]
        assert result["name"] == "test_role"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)

        result = security_role_info.fetch_single(client, "nonexistent")
        assert result is None

    def test_returns_none_when_key_missing(self):
        client = MagicMock()
        client.get.return_value = {"other_role": {"cluster": ["all"]}}

        result = security_role_info.fetch_single(client, "test_role")
        assert result is None


class TestFetchList:
    def test_returns_all_roles(self):
        client = MagicMock()
        client.get.return_value = {
            "role_a": {"cluster": ["all"]},
            "role_b": {"cluster": ["monitor"]},
        }
        module = MagicMock()

        result = security_role_info.fetch_list(client, module)
        assert len(result) == 2
        names = [r["name"] for r in result]
        assert "role_a" in names
        assert "role_b" in names

    def test_returns_empty_list_on_empty_response(self):
        client = MagicMock()
        client.get.return_value = {}
        module = MagicMock()

        result = security_role_info.fetch_list(client, module)
        assert result == []


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_info.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_info.AnsibleModule")
    def test_get_single(self, mock_module_cls, mock_client_cls):
        mock_module = MagicMock()
        mock_module.params = {
            "api_key": "test-key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
            "name": "test_role",
        }
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"test_role": {"cluster": ["all"]}}
        mock_client_cls.return_value = mock_client

        security_role_info.main()

        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert len(result["security_roles"]) == 1

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_info.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_info.AnsibleModule")
    def test_list_all(self, mock_module_cls, mock_client_cls):
        mock_module = MagicMock()
        mock_module.params = {
            "api_key": "test-key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
            "name": None,
        }
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {
            "role_a": {"cluster": ["all"]},
            "role_b": {"cluster": ["monitor"]},
        }
        mock_client_cls.return_value = mock_client

        security_role_info.main()

        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert len(result["security_roles"]) == 2
