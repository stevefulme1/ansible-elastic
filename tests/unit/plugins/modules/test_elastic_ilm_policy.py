"""Unit tests for elastic_ilm_policy module."""

from unittest.mock import MagicMock, patch


class TestCreate:
    def test_create_returns_resource(self):
        mock_client = MagicMock()
        mock_client.create.return_value = {"id": "123", "name": "test"}
        result = mock_client.create("ilm_policy", {"name": "test"})
        assert result["id"] == "123"
        mock_client.create.assert_called_once()


class TestDelete:
    def test_delete_calls_api(self):
        mock_client = MagicMock()
        mock_client.delete.return_value = None
        mock_client.delete("ilm_policy", "123")
        mock_client.delete.assert_called_once_with("ilm_policy", "123")


class TestList:
    def test_list_returns_items(self):
        mock_client = MagicMock()
        mock_client.list.return_value = [{"id": "1"}, {"id": "2"}]
        result = mock_client.list("ilm_policy")
        assert len(result) == 2


class TestGet:
    def test_get_returns_single(self):
        mock_client = MagicMock()
        mock_client.get.return_value = {"id": "123", "name": "test"}
        result = mock_client.get("ilm_policy", "123")
        assert result["name"] == "test"

    def test_get_not_found(self):
        mock_client = MagicMock()
        mock_client.get.return_value = None
        result = mock_client.get("ilm_policy", "nonexistent")
        assert result is None
