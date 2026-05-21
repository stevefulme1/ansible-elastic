"""Unit tests for stevefulme1.elastic.plugins.modules.ilm_policy."""

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import ilm_policy


@pytest.fixture
def module_args_present():
    return {
        "state": "present",
        "policy_id": "test_ilm_policy",
        "phases": {
            "hot": {"actions": {"rollover": {"max_primary_shard_size": "50gb"}}},
            "delete": {"min_age": "30d", "actions": {"delete": {}}},
        },
        "_meta": None,
        "api_key": "test-key",
        "api_url": "https://localhost:9200",
        "validate_certs": False,
        "request_timeout": 30,
    }


@pytest.fixture
def module_args_absent():
    return {
        "state": "absent",
        "policy_id": "test_ilm_policy",
        "phases": None,
        "_meta": None,
        "api_key": "test-key",
        "api_url": "https://localhost:9200",
        "validate_certs": False,
        "request_timeout": 30,
    }


class TestIlmPolicyGetCurrentState:
    def test_returns_policy_when_exists(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"policy_id": "my_policy"}
        client.get.return_value = {
            "my_policy": {
                "policy": {
                    "phases": {"hot": {"actions": {}}},
                },
                "version": 1,
                "modified_date": "2024-01-01T00:00:00.000Z",
            }
        }
        result = ilm_policy.get_current_state(client, module)
        assert result == {"phases": {"hot": {"actions": {}}}}
        client.get.assert_called_once_with("/_ilm/policy/my_policy")

    def test_returns_none_when_not_exists(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"policy_id": "missing_policy"}
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        client.get.side_effect = ClientError("Not found", status_code=404)
        result = ilm_policy.get_current_state(client, module)
        assert result is None

    def test_returns_none_when_policy_id_is_none(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"policy_id": None}
        result = ilm_policy.get_current_state(client, module)
        assert result is None
        client.get.assert_not_called()


class TestIlmPolicyNeedsUpdate:
    def test_returns_true_when_current_is_none(self):
        assert ilm_policy.needs_update(None, {"phases": {}}) is True

    def test_returns_false_when_matching(self):
        current = {"phases": {"hot": {"actions": {}}}}
        desired = {"phases": {"hot": {"actions": {}}}}
        assert ilm_policy.needs_update(current, desired) is False

    def test_returns_true_when_different(self):
        current = {"phases": {"hot": {"actions": {}}}}
        desired = {"phases": {"hot": {"actions": {"rollover": {"max_age": "7d"}}}}}
        assert ilm_policy.needs_update(current, desired) is True

    def test_skips_none_values(self):
        current = {"phases": {"hot": {"actions": {}}}}
        desired = {"phases": None}
        assert ilm_policy.needs_update(current, desired) is False


class TestIlmPolicyBuildPayload:
    def test_builds_with_phases(self):
        module = MagicMock()
        module.params = {
            "phases": {"hot": {"actions": {}}},
            "_meta": None,
        }
        result = ilm_policy.build_payload(module)
        assert result == {"phases": {"hot": {"actions": {}}}}

    def test_builds_with_meta(self):
        module = MagicMock()
        module.params = {
            "phases": None,
            "_meta": {"description": "test"},
        }
        result = ilm_policy.build_payload(module)
        assert result == {"_meta": {"description": "test"}}

    def test_builds_empty_when_all_none(self):
        module = MagicMock()
        module.params = {
            "phases": None,
            "_meta": None,
        }
        result = ilm_policy.build_payload(module)
        assert result == {}


class TestIlmPolicy:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.Client")
    def test_create(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "policy_id": "new_policy",
            "phases": {"delete": {"min_age": "30d", "actions": {"delete": {}}}},
            "_meta": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.put.return_value = {"acknowledged": True}

        ilm_policy.main()

        mock_client.put.assert_called_once_with(
            "/_ilm/policy/new_policy",
            data={"policy": {"phases": {"delete": {"min_age": "30d", "actions": {"delete": {}}}}}},
        )
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.Client")
    def test_update(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "policy_id": "existing_policy",
            "phases": {"delete": {"min_age": "60d", "actions": {"delete": {}}}},
            "_meta": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "existing_policy": {
                "policy": {"phases": {"delete": {"min_age": "30d", "actions": {"delete": {}}}}},
                "version": 1,
            }
        }
        mock_client.put.return_value = {"acknowledged": True}

        ilm_policy.main()

        mock_client.put.assert_called_once()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.Client")
    def test_delete(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "absent",
            "policy_id": "existing_policy",
            "phases": None,
            "_meta": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "existing_policy": {
                "policy": {"phases": {"delete": {"min_age": "30d", "actions": {"delete": {}}}}},
                "version": 1,
            }
        }

        ilm_policy.main()

        mock_client.delete.assert_called_once_with("/_ilm/policy/existing_policy")
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.Client")
    def test_idempotent(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        phases = {"delete": {"min_age": "30d", "actions": {"delete": {}}}}
        mock_module.params = {
            "state": "present",
            "policy_id": "existing_policy",
            "phases": phases,
            "_meta": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "existing_policy": {
                "policy": {"phases": phases},
                "version": 1,
            }
        }

        ilm_policy.main()

        mock_client.put.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.Client")
    def test_check_mode(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "policy_id": "new_policy",
            "phases": {"hot": {"actions": {}}},
            "_meta": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = True

        mock_client = MockClient.return_value
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        ilm_policy.main()

        mock_client.put.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.ilm_policy.Client")
    def test_delete_absent_idempotent(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "absent",
            "policy_id": "nonexistent_policy",
            "phases": None,
            "_meta": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        ilm_policy.main()

        mock_client.delete.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
