"""Unit tests for stevefulme1.elastic.plugins.modules.slm_policy_info."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import slm_policy_info


class TestSlmPolicyInfoFetchSingle:
    def test_returns_entry_when_found(self):
        client = MagicMock()
        client.get.return_value = {
            "nightly": {
                "policy": {"schedule": "0 30 1 * * ?", "repository": "my_repo"},
                "version": 1,
                "modified_date": "2024-01-01T00:00:00.000Z",
            }
        }
        result = slm_policy_info.fetch_single(client, "nightly")
        assert result is not None
        assert result["name"] == "nightly"
        assert result["version"] == 1
        client.get.assert_called_once_with("/_slm/policy/nightly")

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        client.get.side_effect = ClientError("Not found", status_code=404)
        result = slm_policy_info.fetch_single(client, "missing")
        assert result is None

    def test_returns_none_when_key_missing(self):
        client = MagicMock()
        client.get.return_value = {"other_policy": {"policy": {}}}
        result = slm_policy_info.fetch_single(client, "missing")
        assert result is None


class TestSlmPolicyInfoFetchList:
    def test_returns_all_policies(self):
        client = MagicMock()
        module = MagicMock()
        client.get.return_value = {
            "nightly": {"policy": {}, "version": 1},
            "weekly": {"policy": {}, "version": 2},
        }
        result = slm_policy_info.fetch_list(client, module)
        assert len(result) == 2
        names = [item["name"] for item in result]
        assert "nightly" in names
        assert "weekly" in names

    def test_returns_empty_list_when_no_policies(self):
        client = MagicMock()
        module = MagicMock()
        client.get.return_value = {}
        result = slm_policy_info.fetch_list(client, module)
        assert result == []


class TestSlmPolicyInfo:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy_info.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy_info.Client")
    def test_fetch_single_by_id(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "id": "nightly",
            "page": None,
            "page_size": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "nightly": {"policy": {"schedule": "0 30 1 * * ?"}, "version": 1}
        }

        slm_policy_info.main()

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
        assert len(call_kwargs["slm_policies"]) == 1

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy_info.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy_info.Client")
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
            "nightly": {"policy": {}, "version": 1},
            "weekly": {"policy": {}, "version": 2},
        }

        slm_policy_info.main()

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
        assert len(call_kwargs["slm_policies"]) == 2

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy_info.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy_info.Client")
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

        slm_policy_info.main()

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
        assert call_kwargs["slm_policies"] == []
