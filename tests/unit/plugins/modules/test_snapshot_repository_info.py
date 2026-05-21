"""Unit tests for stevefulme1.elastic.plugins.modules.snapshot_repository_info."""

from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import snapshot_repository_info


class TestSnapshotRepositoryInfoFetchSingle:
    def test_returns_entry_when_found(self):
        client = MagicMock()
        client.get.return_value = {
            "my_repo": {
                "type": "fs",
                "settings": {"location": "/mount/backups"},
            }
        }
        result = snapshot_repository_info.fetch_single(client, "my_repo")
        assert result is not None
        assert result["name"] == "my_repo"
        assert result["type"] == "fs"
        client.get.assert_called_once_with("/_snapshot/my_repo")

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError
        client.get.side_effect = ClientError("Not found", status_code=404)
        result = snapshot_repository_info.fetch_single(client, "missing")
        assert result is None

    def test_returns_none_when_key_missing(self):
        client = MagicMock()
        client.get.return_value = {"other_repo": {"type": "fs"}}
        result = snapshot_repository_info.fetch_single(client, "missing")
        assert result is None


class TestSnapshotRepositoryInfoFetchList:
    def test_returns_all_repos(self):
        client = MagicMock()
        module = MagicMock()
        client.get.return_value = {
            "repo_a": {"type": "fs", "settings": {}},
            "repo_b": {"type": "s3", "settings": {}},
        }
        result = snapshot_repository_info.fetch_list(client, module)
        assert len(result) == 2
        names = [item["name"] for item in result]
        assert "repo_a" in names
        assert "repo_b" in names

    def test_returns_empty_list_when_no_repos(self):
        client = MagicMock()
        module = MagicMock()
        client.get.return_value = {}
        result = snapshot_repository_info.fetch_list(client, module)
        assert result == []


class TestSnapshotRepositoryInfo:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository_info.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository_info.Client")
    def test_fetch_single_by_id(self, MockClient, MockModule):
        mock_module = MockModule.return_value
        mock_module.params = {
            "id": "my_repo",
            "page": None,
            "page_size": None,
            "api_key": "key",
            "api_url": "https://localhost:9200",
            "validate_certs": False,
            "request_timeout": 30,
        }

        mock_client = MockClient.return_value
        mock_client.get.return_value = {
            "my_repo": {"type": "fs", "settings": {"location": "/mount/backups"}}
        }

        snapshot_repository_info.main()

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
        assert len(call_kwargs["snapshot_repositories"]) == 1

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository_info.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository_info.Client")
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
            "repo_a": {"type": "fs", "settings": {}},
            "repo_b": {"type": "s3", "settings": {}},
        }

        snapshot_repository_info.main()

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
        assert len(call_kwargs["snapshot_repositories"]) == 2

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository_info.AnsibleModule")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.snapshot_repository_info.Client")
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

        snapshot_repository_info.main()

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
        assert call_kwargs["snapshot_repositories"] == []
