"""Unit tests for stevefulme1.elastic.plugins.modules.ilm_policy_info."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import ilm_policy_info


class TestIlmPolicyInfoFetchSingle:
    def test_returns_entry_when_found(self):
        client = MagicMock()
        client.get.return_value = {
            "my_policy": {
                "policy": {"phases": {"hot": {"actions": {}}}},
                "version": 1,
                "modified_date": "2024-01-01T00:00:00.000Z",
            }
        }
        result = ilm_policy_info.fetch_single(client, "my_policy")
        assert result is not None
        assert result["name"] == "my_policy"
        assert result["version"] == 1
        client.get.assert_called_once_with("/_ilm/policy/my_policy")

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        client.get.side_effect = ClientError("Not found", status_code=404)
        result = ilm_policy_info.fetch_single(client, "missing_policy")
        assert result is None

    def test_returns_none_when_key_missing(self):
        client = MagicMock()
        client.get.return_value = {"other_policy": {"policy": {}}}
        result = ilm_policy_info.fetch_single(client, "missing_policy")
        assert result is None


class TestIlmPolicyInfoFetchList:
    def test_returns_all_policies(self):
        client = MagicMock()
        module = MagicMock()
        client.get.return_value = {
            "policy_a": {"policy": {"phases": {}}, "version": 1},
            "policy_b": {"policy": {"phases": {}}, "version": 2},
        }
        result = ilm_policy_info.fetch_list(client, module)
        assert len(result) == 2
        names = [item["name"] for item in result]
        assert "policy_a" in names
        assert "policy_b" in names

    def test_returns_empty_list_when_no_policies(self):
        client = MagicMock()
        module = MagicMock()
        client.get.return_value = {}
        result = ilm_policy_info.fetch_list(client, module)
        assert result == []


class TestIlmPolicyInfo:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy_info.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy_info.Client")
    def test_fetch_single_by_id(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "id": "my_policy",
            "page": None,
            "page_size": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "my_policy": {
                "policy": {"phases": {}},
                "version": 1,
            }
        }

        ilm_policy_info.main()

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
        assert len(call_kwargs["ilm_policies"]) == 1

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy_info.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy_info.Client")
    def test_fetch_list(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "id": None,
            "page": None,
            "page_size": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "policy_a": {"policy": {}, "version": 1},
            "policy_b": {"policy": {}, "version": 2},
        }

        ilm_policy_info.main()

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
        assert len(call_kwargs["ilm_policies"]) == 2

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy_info.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy_info.Client")
    def test_fetch_single_not_found(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "id": "nonexistent",
            "page": None,
            "page_size": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }

        mock_client = MockClient.return_value
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        ilm_policy_info.main()

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
        assert call_kwargs["ilm_policies"] == []
