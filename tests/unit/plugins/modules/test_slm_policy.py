"""Unit tests for stevefulme1.elastic.plugins.modules.slm_policy."""

from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import slm_policy


class TestSlmPolicyGetCurrentState:
    def test_returns_policy_when_exists(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"policy_id": "nightly"}
        client.get.return_value = {
            "nightly": {
                "policy": {
                    "schedule": "0 30 1 * * ?",
                    "name": "<nightly-snap-{now/d}>",
                    "repository": "my_repo",
                    "config": {"indices": ["*"]},
                },
                "version": 1,
                "modified_date": "2024-01-01T00:00:00.000Z",
            }
        }
        result = slm_policy.get_current_state(client, module)
        assert result is not None
        assert "policy" in result
        client.get.assert_called_once_with("/_slm/policy/nightly")

    def test_returns_none_when_not_exists(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"policy_id": "missing"}
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        client.get.side_effect = ClientError("Not found", status_code=404)
        result = slm_policy.get_current_state(client, module)
        assert result is None

    def test_returns_none_when_policy_id_is_none(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"policy_id": None}
        result = slm_policy.get_current_state(client, module)
        assert result is None
        client.get.assert_not_called()


class TestSlmPolicyNeedsUpdate:
    def test_returns_true_when_current_is_none(self):
        assert slm_policy.needs_update(None, {"schedule": "0 0 * * * ?"}) is True

    def test_returns_false_when_matching(self):
        current = {
            "policy": {"schedule": "0 30 1 * * ?", "repository": "my_repo"},
        }
        desired = {"schedule": "0 30 1 * * ?", "repository": "my_repo"}
        assert slm_policy.needs_update(current, desired) is False

    def test_returns_true_when_different(self):
        current = {
            "policy": {"schedule": "0 30 1 * * ?", "repository": "my_repo"},
        }
        desired = {"schedule": "0 0 2 * * ?"}
        assert slm_policy.needs_update(current, desired) is True

    def test_skips_none_values(self):
        current = {"policy": {"schedule": "0 30 1 * * ?"}}
        desired = {"schedule": None, "repository": None}
        assert slm_policy.needs_update(current, desired) is False


class TestSlmPolicyBuildPayload:
    def test_builds_full_payload(self):
        module = MagicMock()
        module.params = {
            "schedule": "0 30 1 * * ?",
            "name": "<snap-{now/d}>",
            "repository": "my_repo",
            "config": {"indices": ["*"]},
            "retention": {"expire_after": "30d", "min_count": 5},
        }
        result = slm_policy.build_payload(module)
        assert result == {
            "schedule": "0 30 1 * * ?",
            "name": "<snap-{now/d}>",
            "repository": "my_repo",
            "config": {"indices": ["*"]},
            "retention": {"expire_after": "30d", "min_count": 5},
        }

    def test_builds_empty_when_all_none(self):
        module = MagicMock()
        module.params = {
            "schedule": None,
            "name": None,
            "repository": None,
            "config": None,
            "retention": None,
        }
        result = slm_policy.build_payload(module)
        assert result == {}


class TestSlmPolicy:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.Client")
    def test_create(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "policy_id": "nightly",
            "schedule": "0 30 1 * * ?",
            "name": "<snap-{now/d}>",
            "repository": "my_repo",
            "config": {"indices": ["*"]},
            "retention": None,
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

        slm_policy.main()

        mock_client.put.assert_called_once()
        call_args = mock_client.put.call_args
        assert call_args[0][0] == "/_slm/policy/nightly"
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.Client")
    def test_update(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "policy_id": "nightly",
            "schedule": "0 0 2 * * ?",
            "name": None,
            "repository": None,
            "config": None,
            "retention": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "nightly": {
                "policy": {"schedule": "0 30 1 * * ?", "repository": "my_repo"},
                "version": 1,
            }
        }
        mock_client.put.return_value = {"acknowledged": True}

        slm_policy.main()

        mock_client.put.assert_called_once()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.Client")
    def test_delete(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "absent",
            "policy_id": "nightly",
            "schedule": None,
            "name": None,
            "repository": None,
            "config": None,
            "retention": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "nightly": {"policy": {"schedule": "0 30 1 * * ?"}, "version": 1}
        }

        slm_policy.main()

        mock_client.delete.assert_called_once_with("/_slm/policy/nightly")
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.Client")
    def test_idempotent(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "policy_id": "nightly",
            "schedule": "0 30 1 * * ?",
            "name": None,
            "repository": None,
            "config": None,
            "retention": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "nightly": {
                "policy": {"schedule": "0 30 1 * * ?"},
                "version": 1,
            }
        }

        slm_policy.main()

        mock_client.put.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.Client")
    def test_check_mode(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "policy_id": "nightly",
            "schedule": "0 30 1 * * ?",
            "name": "<snap-{now/d}>",
            "repository": "my_repo",
            "config": None,
            "retention": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = True

        mock_client = MockClient.return_value
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        slm_policy.main()

        mock_client.put.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.slm_policy.Client")
    def test_delete_absent_idempotent(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "absent",
            "policy_id": "nonexistent",
            "schedule": None,
            "name": None,
            "repository": None,
            "config": None,
            "retention": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        slm_policy.main()

        mock_client.delete.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
