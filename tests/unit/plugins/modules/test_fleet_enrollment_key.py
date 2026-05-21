# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import fleet_enrollment_key
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "key_id": None,
        "name": "My Enrollment Key",
        "policy_id": "agent-policy-123",
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "key_id": "key-123",
        "name": None,
        "policy_id": None,
    }


@pytest.fixture
def existing_key():
    return {
        "id": "key-123",
        "name": "My Enrollment Key",
        "policy_id": "agent-policy-123",
        "api_key": "encoded-key-value",
    }


class TestGetCurrentState:
    def test_returns_key_by_id(self):
        client = MagicMock()
        client.get.return_value = {"item": {"id": "key-123", "name": "My Enrollment Key"}}
        module = MagicMock()
        module.params = {"key_id": "key-123", "name": "My Enrollment Key"}

        result = fleet_enrollment_key.get_current_state(client, module)
        assert result == {"id": "key-123", "name": "My Enrollment Key"}

    def test_returns_key_by_name(self):
        client = MagicMock()
        client.get.return_value = {
            "items": [
                {"id": "key-123", "name": "My Enrollment Key"},
                {"id": "key-456", "name": "Other Key"},
            ]
        }
        module = MagicMock()
        module.params = {"key_id": None, "name": "My Enrollment Key"}

        result = fleet_enrollment_key.get_current_state(client, module)
        assert result["name"] == "My Enrollment Key"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"key_id": "nonexistent", "name": "test"}

        result = fleet_enrollment_key.get_current_state(client, module)
        assert result is None

    def test_returns_none_when_no_id_or_name(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"key_id": None, "name": None}

        result = fleet_enrollment_key.get_current_state(client, module)
        assert result is None


class TestBuildPayload:
    def test_build_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = fleet_enrollment_key.build_payload(module)
        assert payload["name"] == "My Enrollment Key"
        assert payload["policy_id"] == "agent-policy-123"

    def test_build_payload_skips_none(self):
        module = MagicMock()
        module.params = {"name": None, "policy_id": "agent-policy-123"}

        payload = fleet_enrollment_key.build_payload(module)
        assert "name" not in payload
        assert payload["policy_id"] == "agent-policy-123"


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        mock_client.post.return_value = {"item": {"id": "key-new", "name": "My Enrollment Key"}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_enrollment_key.main()

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/api/fleet/enrollment_api_keys" in call_args[0][0]
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_enrollment_key.main()

        mock_client.post.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.AnsibleModule")
    def test_idempotent_no_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_key):
        """Enrollment keys cannot be updated, so existing key returns unchanged."""
        mock_module = MagicMock()
        mock_module.params = dict(module_params_present, key_id="key-123")
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_key}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_enrollment_key.main()

        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_key):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_key}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_enrollment_key.main()

        mock_client.delete.assert_called_once_with("/api/fleet/enrollment_api_keys/key-123")
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_enrollment_key.main()

        mock_client.delete.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_enrollment_key.AnsibleModule")
    def test_sets_kbn_xsrf_header(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        mock_client.post.return_value = {"item": {}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_enrollment_key.main()

        assert mock_client.headers["kbn-xsrf"] == "true"
