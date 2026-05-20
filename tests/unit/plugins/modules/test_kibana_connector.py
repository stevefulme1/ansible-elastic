# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_connector
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "connector_id": None,
        "name": "My Webhook",
        "connector_type_id": ".webhook",
        "config": {"url": "https://example.com/hook", "method": "post"},
        "secrets": {"user": "admin", "password": "secret"},
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "connector_id": "conn-123",
        "name": "My Webhook",
        "connector_type_id": None,
        "config": None,
        "secrets": None,
    }


@pytest.fixture
def existing_connector():
    return {
        "id": "conn-123",
        "name": "My Webhook",
        "connector_type_id": ".webhook",
        "config": {"url": "https://example.com/hook", "method": "post"},
        "is_preconfigured": False,
    }


class TestGetCurrentState:
    def test_returns_connector_by_id(self):
        client = MagicMock()
        client.get.return_value = {"id": "conn-123", "name": "My Webhook"}
        module = MagicMock()
        module.params = {"connector_id": "conn-123", "name": "My Webhook"}

        result = kibana_connector.get_current_state(client, module)
        assert result == {"id": "conn-123", "name": "My Webhook"}
        client.get.assert_called_once_with("/api/actions/connector/conn-123")

    def test_returns_connector_by_name(self):
        client = MagicMock()
        client.get.return_value = [
            {"id": "conn-123", "name": "My Webhook"},
            {"id": "conn-456", "name": "Other"},
        ]
        module = MagicMock()
        module.params = {"connector_id": None, "name": "My Webhook"}

        result = kibana_connector.get_current_state(client, module)
        assert result["name"] == "My Webhook"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"connector_id": "nonexistent", "name": "test"}

        result = kibana_connector.get_current_state(client, module)
        assert result is None

    def test_returns_none_when_no_id_or_name(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"connector_id": None, "name": None}

        result = kibana_connector.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    def test_needs_update_when_current_is_none(self):
        assert kibana_connector.needs_update(None, {"name": "Test"}) is True

    def test_no_update_when_identical(self, existing_connector):
        desired = {"name": "My Webhook", "config": {"url": "https://example.com/hook", "method": "post"}}
        assert kibana_connector.needs_update(existing_connector, desired) is False

    def test_needs_update_when_different(self, existing_connector):
        desired = {"name": "Updated Webhook"}
        assert kibana_connector.needs_update(existing_connector, desired) is True

    def test_skips_none_values(self, existing_connector):
        desired = {"name": None, "config": None}
        assert kibana_connector.needs_update(existing_connector, desired) is False

    def test_skips_secrets_comparison(self, existing_connector):
        """Secrets are write-only and never returned, so they must be skipped."""
        desired = {"name": "My Webhook", "secrets": {"user": "admin", "password": "new"}}
        assert kibana_connector.needs_update(existing_connector, desired) is False


class TestBuildPayloads:
    def test_build_create_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = kibana_connector.build_create_payload(module)
        assert payload["name"] == "My Webhook"
        assert payload["connector_type_id"] == ".webhook"
        assert payload["config"] == {"url": "https://example.com/hook", "method": "post"}
        assert payload["secrets"] == {"user": "admin", "password": "secret"}

    def test_build_update_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = kibana_connector.build_update_payload(module)
        assert payload["name"] == "My Webhook"
        assert payload["config"] == {"url": "https://example.com/hook", "method": "post"}
        assert payload["secrets"] == {"user": "admin", "password": "secret"}
        # connector_type_id should NOT be in update payload
        assert "connector_type_id" not in payload

    def test_build_create_skips_none_values(self):
        module = MagicMock()
        module.params = {
            "name": "Test",
            "connector_type_id": None,
            "config": None,
            "secrets": None,
        }

        payload = kibana_connector.build_create_payload(module)
        assert payload == {"name": "Test"}


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = []
        mock_client.post.return_value = {"id": "conn-new", "name": "My Webhook"}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_connector.main()

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/api/actions/connector" in call_args[0]
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = []
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_connector.main()

        mock_client.post.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.AnsibleModule")
    def test_idempotent(self, mock_module_cls, mock_client_cls, module_params_present, existing_connector):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = [existing_connector]
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_connector.main()

        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.AnsibleModule")
    def test_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_connector):
        mock_module = MagicMock()
        params = dict(module_params_present, connector_id="conn-123", name="Updated Webhook")
        mock_module.params = params
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = existing_connector
        mock_client.put.return_value = {"id": "conn-123", "name": "Updated Webhook"}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_connector.main()

        mock_client.put.assert_called_once()
        call_args = mock_client.put.call_args
        assert "conn-123" in call_args[0][0]
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_connector):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = existing_connector
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_connector.main()

        mock_client.delete.assert_called_once_with("/api/actions/connector/conn-123")
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_connector.main()

        mock_client.delete.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_connector.AnsibleModule")
    def test_sets_kbn_xsrf_header(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = []
        mock_client.post.return_value = {}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_connector.main()

        assert mock_client.headers["kbn-xsrf"] == "true"
