# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import security_role_mapping_info
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


class TestFetchSingle:
    def test_returns_mapping_when_exists(self):
        client = MagicMock()
        client.get.return_value = {"my_mapping": {"roles": ["admin"], "enabled": True}}

        result = security_role_mapping_info.fetch_single(client, "my_mapping")
        assert result is not None
        assert result["roles"] == ["admin"]
        assert result["name"] == "my_mapping"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)

        result = security_role_mapping_info.fetch_single(client, "nonexistent")
        assert result is None


class TestFetchList:
    def test_returns_all_mappings(self):
        client = MagicMock()
        client.get.return_value = {
            "map_a": {"roles": ["admin"]},
            "map_b": {"roles": ["viewer"]},
        }
        module = MagicMock()

        result = security_role_mapping_info.fetch_list(client, module)
        assert len(result) == 2
        names = [m["name"] for m in result]
        assert "map_a" in names
        assert "map_b" in names


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping_info.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping_info.AnsibleModule")
    def test_get_single(self, mock_module_cls, mock_client_cls):
        mock_module = MagicMock()
        mock_module.params = {
            "api_key": "test-key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
            "name": "my_mapping",
        }
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"my_mapping": {"roles": ["admin"]}}
        mock_client_cls.return_value = mock_client

        security_role_mapping_info.main()

        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert len(result["security_role_mappings"]) == 1

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping_info.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping_info.AnsibleModule")
    def test_list_all(self, mock_module_cls, mock_client_cls):
        mock_module = MagicMock()
        mock_module.params = {
            "api_key": "test-key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
            "name": None,
        }
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {
            "map_a": {"roles": ["admin"]},
            "map_b": {"roles": ["viewer"]},
        }
        mock_client_cls.return_value = mock_client

        security_role_mapping_info.main()

        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert len(result["security_role_mappings"]) == 2
