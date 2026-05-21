# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import fleet_agent_policy
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "policy_id": None,
        "name": "My Agent Policy",
        "namespace": "default",
        "description": "Test policy",
        "monitoring_enabled": ["logs", "metrics"],
        "is_managed": False,
        "inactivity_timeout": None,
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "policy_id": "policy-123",
        "name": "My Agent Policy",
        "namespace": "default",
        "description": None,
        "monitoring_enabled": None,
        "is_managed": None,
        "inactivity_timeout": None,
    }


@pytest.fixture
def existing_policy():
    return {
        "id": "policy-123",
        "name": "My Agent Policy",
        "namespace": "default",
        "description": "Test policy",
        "monitoring_enabled": ["logs", "metrics"],
        "is_managed": False,
    }


class TestGetCurrentState:
    def test_returns_policy_by_id(self):
        client = MagicMock()
        client.get.return_value = {"item": {"id": "policy-123", "name": "My Agent Policy"}}
        module = MagicMock()
        module.params = {"policy_id": "policy-123", "name": "My Agent Policy"}

        result = fleet_agent_policy.get_current_state(client, module)
        assert result == {"id": "policy-123", "name": "My Agent Policy"}
        client.get.assert_called_once_with("/api/fleet/agent_policies/policy-123")

    def test_returns_policy_by_name(self):
        client = MagicMock()
        client.get.return_value = {
            "items": [
                {"id": "policy-123", "name": "My Agent Policy"},
                {"id": "policy-456", "name": "Other"},
            ]
        }
        module = MagicMock()
        module.params = {"policy_id": None, "name": "My Agent Policy"}

        result = fleet_agent_policy.get_current_state(client, module)
        assert result["name"] == "My Agent Policy"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"policy_id": "nonexistent", "name": "test"}

        result = fleet_agent_policy.get_current_state(client, module)
        assert result is None

    def test_returns_none_when_no_id_or_name(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"policy_id": None, "name": None}

        result = fleet_agent_policy.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    def test_needs_update_when_current_is_none(self):
        assert fleet_agent_policy.needs_update(None, {"name": "Test"}) is True

    def test_no_update_when_identical(self, existing_policy):
        desired = {"name": "My Agent Policy", "namespace": "default", "description": "Test policy"}
        assert fleet_agent_policy.needs_update(existing_policy, desired) is False

    def test_needs_update_when_different(self, existing_policy):
        desired = {"name": "Updated Policy"}
        assert fleet_agent_policy.needs_update(existing_policy, desired) is True

    def test_skips_none_values(self, existing_policy):
        desired = {"name": None, "description": None}
        assert fleet_agent_policy.needs_update(existing_policy, desired) is False


class TestBuildPayload:
    def test_build_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = fleet_agent_policy.build_payload(module)
        assert payload["name"] == "My Agent Policy"
        assert payload["namespace"] == "default"
        assert payload["description"] == "Test policy"
        assert payload["monitoring_enabled"] == ["logs", "metrics"]
        assert payload["is_managed"] is False

    def test_build_payload_skips_none_values(self):
        module = MagicMock()
        module.params = {
            "name": "Test",
            "namespace": None,
            "description": None,
            "monitoring_enabled": None,
            "is_managed": None,
            "inactivity_timeout": None,
        }

        payload = fleet_agent_policy.build_payload(module)
        assert payload == {"name": "Test"}


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        mock_client.post.return_value = {"item": {"id": "policy-new", "name": "My Agent Policy"}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_agent_policy.main()

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/api/fleet/agent_policies" in call_args[0][0]
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_agent_policy.main()

        mock_client.post.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.AnsibleModule")
    def test_idempotent(self, mock_module_cls, mock_client_cls, module_params_present, existing_policy):
        mock_module = MagicMock()
        mock_module.params = dict(module_params_present, policy_id="policy-123")
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_policy}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_agent_policy.main()

        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.AnsibleModule")
    def test_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_policy):
        mock_module = MagicMock()
        params = dict(module_params_present, policy_id="policy-123", name="Updated Policy")
        mock_module.params = params
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_policy}
        mock_client.put.return_value = {"item": {"id": "policy-123", "name": "Updated Policy"}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_agent_policy.main()

        mock_client.put.assert_called_once()
        call_args = mock_client.put.call_args
        assert "policy-123" in call_args[0][0]
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_policy):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_policy}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_agent_policy.main()

        mock_client.post.assert_called_once_with(
            "/api/fleet/agent_policies/delete",
            data={"agentPolicyId": "policy-123"},
        )
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_agent_policy.main()

        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_agent_policy.AnsibleModule")
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

        fleet_agent_policy.main()

        assert mock_client.headers["kbn-xsrf"] == "true"
