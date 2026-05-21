# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import fleet_package_policy
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "package_policy_id": None,
        "name": "system-1",
        "namespace": "default",
        "policy_id": "agent-policy-123",
        "package": {"name": "system", "version": "1.0.0"},
        "inputs": None,
        "description": None,
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "package_policy_id": "pkg-123",
        "name": "system-1",
        "namespace": "default",
        "policy_id": None,
        "package": None,
        "inputs": None,
        "description": None,
    }


@pytest.fixture
def existing_package_policy():
    return {
        "id": "pkg-123",
        "name": "system-1",
        "namespace": "default",
        "policy_id": "agent-policy-123",
        "package": {"name": "system", "version": "1.0.0"},
    }


class TestGetCurrentState:
    def test_returns_policy_by_id(self):
        client = MagicMock()
        client.get.return_value = {"item": {"id": "pkg-123", "name": "system-1"}}
        module = MagicMock()
        module.params = {"package_policy_id": "pkg-123", "name": "system-1"}

        result = fleet_package_policy.get_current_state(client, module)
        assert result == {"id": "pkg-123", "name": "system-1"}

    def test_returns_policy_by_name(self):
        client = MagicMock()
        client.get.return_value = {
            "items": [
                {"id": "pkg-123", "name": "system-1"},
                {"id": "pkg-456", "name": "other"},
            ]
        }
        module = MagicMock()
        module.params = {"package_policy_id": None, "name": "system-1"}

        result = fleet_package_policy.get_current_state(client, module)
        assert result["name"] == "system-1"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"package_policy_id": "nonexistent", "name": "test"}

        result = fleet_package_policy.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    def test_needs_update_when_current_is_none(self):
        assert fleet_package_policy.needs_update(None, {"name": "Test"}) is True

    def test_no_update_when_identical(self, existing_package_policy):
        desired = {"name": "system-1", "namespace": "default"}
        assert fleet_package_policy.needs_update(existing_package_policy, desired) is False

    def test_needs_update_when_different(self, existing_package_policy):
        desired = {"name": "system-2"}
        assert fleet_package_policy.needs_update(existing_package_policy, desired) is True

    def test_skips_none_values(self, existing_package_policy):
        desired = {"name": None, "description": None}
        assert fleet_package_policy.needs_update(existing_package_policy, desired) is False


class TestBuildPayload:
    def test_build_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = fleet_package_policy.build_payload(module)
        assert payload["name"] == "system-1"
        assert payload["namespace"] == "default"
        assert payload["policy_id"] == "agent-policy-123"
        assert payload["package"] == {"name": "system", "version": "1.0.0"}


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        mock_client.post.return_value = {"item": {"id": "pkg-new", "name": "system-1"}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_package_policy.main()

        mock_client.post.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_package_policy.main()

        mock_client.post.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.AnsibleModule")
    def test_idempotent(self, mock_module_cls, mock_client_cls, module_params_present, existing_package_policy):
        mock_module = MagicMock()
        mock_module.params = dict(module_params_present, package_policy_id="pkg-123")
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_package_policy}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_package_policy.main()

        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.AnsibleModule")
    def test_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_package_policy):
        mock_module = MagicMock()
        params = dict(module_params_present, package_policy_id="pkg-123", name="system-2")
        mock_module.params = params
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_package_policy}
        mock_client.put.return_value = {"item": {"id": "pkg-123", "name": "system-2"}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_package_policy.main()

        mock_client.put.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_package_policy):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_package_policy}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_package_policy.main()

        mock_client.delete.assert_called_once_with("/api/fleet/package_policies/pkg-123")
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_package_policy.main()

        mock_client.delete.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_package_policy.AnsibleModule")
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

        fleet_package_policy.main()

        assert mock_client.headers["kbn-xsrf"] == "true"
