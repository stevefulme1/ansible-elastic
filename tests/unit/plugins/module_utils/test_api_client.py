"""Unit tests for API client."""

from unittest.mock import MagicMock, patch

try:
    from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ApiClient
except ImportError:
    ApiClient = None


class TestApiClient:
    @patch("requests.Session")
    def test_auth_with_api_key(self, mock_session):
        module = MagicMock()
        module.params = {
            "host": "test.example.com",
            "api_key": "test-key",
            "username": None,
            "password": None,
            "validate_certs": True,
        }
        if ApiClient:
            client = ApiClient(module)
            assert "Authorization" in client.session.headers
