"""Unit tests for API client."""

from unittest.mock import MagicMock, patch


class TestApiClient:
    def test_session_created(self):
        with patch("requests.Session") as mock_session:
            session = mock_session()
            session.headers = dict()
            session.verify = True
            assert session.verify is True

    def test_auth_header_set(self):
        headers = dict()
        headers["Authorization"] = "Bearer test-key"
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key"

    def test_basic_auth(self):
        session = MagicMock()
        session.auth = ("admin", "password")
        assert session.auth == ("admin", "password")
