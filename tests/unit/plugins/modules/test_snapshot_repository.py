"""Unit tests for stevefulme1.elastic.plugins.modules.snapshot_repository."""

from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import snapshot_repository


class TestSnapshotRepositoryGetCurrentState:
    def test_returns_repo_when_exists(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"repository": "my_repo"}
        client.get.return_value = {
            "my_repo": {
                "type": "fs",
                "settings": {"location": "/mount/backups"},
            }
        }
        result = snapshot_repository.get_current_state(client, module)
        assert result is not None
        assert result["type"] == "fs"
        client.get.assert_called_once_with("/_snapshot/my_repo")

    def test_returns_none_when_not_exists(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"repository": "missing"}
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        client.get.side_effect = ClientError("Not found", status_code=404)
        result = snapshot_repository.get_current_state(client, module)
        assert result is None

    def test_returns_none_when_repository_is_none(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"repository": None}
        result = snapshot_repository.get_current_state(client, module)
        assert result is None
        client.get.assert_not_called()


class TestSnapshotRepositoryNeedsUpdate:
    def test_returns_true_when_current_is_none(self):
        assert snapshot_repository.needs_update(None, {"type": "fs"}) is True

    def test_returns_false_when_matching(self):
        current = {"type": "fs", "settings": {"location": "/mount/backups"}}
        desired = {"type": "fs", "settings": {"location": "/mount/backups"}}
        assert snapshot_repository.needs_update(current, desired) is False

    def test_returns_true_when_different(self):
        current = {"type": "fs", "settings": {"location": "/mount/backups"}}
        desired = {"type": "fs", "settings": {"location": "/mount/new_backups"}}
        assert snapshot_repository.needs_update(current, desired) is True

    def test_skips_none_values(self):
        current = {"type": "fs", "settings": {"location": "/mount/backups"}}
        desired = {"type": None, "settings": None}
        assert snapshot_repository.needs_update(current, desired) is False


class TestSnapshotRepositoryBuildPayload:
    def test_builds_full_payload(self):
        module = MagicMock()
        module.params = {
            "type": "fs",
            "settings": {"location": "/mount/backups"},
        }
        result = snapshot_repository.build_payload(module)
        assert result == {
            "type": "fs",
            "settings": {"location": "/mount/backups"},
        }

    def test_builds_empty_when_all_none(self):
        module = MagicMock()
        module.params = {
            "type": None,
            "settings": None,
        }
        result = snapshot_repository.build_payload(module)
        assert result == {}


class TestSnapshotRepository:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.Client")
    def test_create(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "repository": "my_repo",
            "type": "fs",
            "settings": {"location": "/mount/backups"},
            "verify": True,
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

        snapshot_repository.main()

        mock_client.put.assert_called_once_with(
            "/_snapshot/my_repo",
            data={"type": "fs", "settings": {"location": "/mount/backups"}},
            params=None,
        )
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.Client")
    def test_create_without_verify(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "repository": "my_repo",
            "type": "fs",
            "settings": {"location": "/mount/backups"},
            "verify": False,
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

        snapshot_repository.main()

        mock_client.put.assert_called_once_with(
            "/_snapshot/my_repo",
            data={"type": "fs", "settings": {"location": "/mount/backups"}},
            params={"verify": "false"},
        )

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.Client")
    def test_update(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "repository": "my_repo",
            "type": "fs",
            "settings": {"location": "/mount/new_backups"},
            "verify": True,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "my_repo": {"type": "fs", "settings": {"location": "/mount/backups"}}
        }
        mock_client.put.return_value = {"acknowledged": True}

        snapshot_repository.main()

        mock_client.put.assert_called_once()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.Client")
    def test_delete(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "absent",
            "repository": "my_repo",
            "type": None,
            "settings": None,
            "verify": True,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "my_repo": {"type": "fs", "settings": {"location": "/mount/backups"}}
        }

        snapshot_repository.main()

        mock_client.delete.assert_called_once_with("/_snapshot/my_repo")
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.Client")
    def test_idempotent(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "repository": "my_repo",
            "type": "fs",
            "settings": {"location": "/mount/backups"},
            "verify": True,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "my_repo": {"type": "fs", "settings": {"location": "/mount/backups"}}
        }

        snapshot_repository.main()

        mock_client.put.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.Client")
    def test_check_mode(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "present",
            "repository": "my_repo",
            "type": "fs",
            "settings": {"location": "/mount/backups"},
            "verify": True,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = True

        mock_client = MockClient.return_value
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        snapshot_repository.main()

        mock_client.put.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository.Client")
    def test_delete_absent_idempotent(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "state": "absent",
            "repository": "nonexistent",
            "type": None,
            "settings": None,
            "verify": True,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }
        mock_module.check_mode = False

        mock_client = MockClient.return_value
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        mock_client.get.side_effect = ClientError("Not found", status_code=404)

        snapshot_repository.main()

        mock_client.delete.assert_not_called()
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
