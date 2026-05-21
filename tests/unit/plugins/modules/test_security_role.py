# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import security_role
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:9200",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "name": "test_role",
        "cluster": ["monitor"],
        "indices": [{"names": ["index-*"], "privileges": ["read"]}],
        "applications": [],
        "run_as": [],
        "metadata": {"version": 1},
        "description": "Test role",
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:9200",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "name": "test_role",
        "cluster": None,
        "indices": None,
        "applications": None,
        "run_as": None,
        "metadata": None,
        "description": None,
    }


@pytest.fixture
def existing_role():
    return {
        "cluster": ["monitor"],
        "indices": [{"names": ["index-*"], "privileges": ["read"]}],
        "applications": [],
        "run_as": [],
        "metadata": {"version": 1},
        "description": "Test role",
    }


class TestGetCurrentState:
    def test_returns_role_when_exists(self):
        client = MagicMock()
        client.get.return_value = {"test_role": {"cluster": ["all"]}}
        module = MagicMock()
        module.params = {"name": "test_role"}

        result = security_role.get_current_state(client, module)
        assert result == {"cluster": ["all"]}

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"name": "nonexistent"}

        result = security_role.get_current_state(client, module)
        assert result is None

    def test_returns_none_when_name_is_none(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"name": None}

        result = security_role.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    def test_needs_update_when_current_is_none(self):
        assert security_role.needs_update(None, {"cluster": ["all"]}) is True

    def test_no_update_when_identical(self, existing_role):
        desired = {"cluster": ["monitor"], "description": "Test role"}
        assert security_role.needs_update(existing_role, desired) is False

    def test_needs_update_when_different(self, existing_role):
        desired = {"cluster": ["all"]}
        assert security_role.needs_update(existing_role, desired) is True

    def test_skips_none_values(self, existing_role):
        desired = {"cluster": None, "description": None}
        assert security_role.needs_update(existing_role, desired) is False


class TestBuildPayload:
    def test_builds_full_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = security_role.build_payload(module)
        assert payload["cluster"] == ["monitor"]
        assert payload["indices"] == [{"names": ["index-*"], "privileges": ["read"]}]
        assert payload["applications"] == []
        assert payload["run_as"] == []
        assert payload["metadata"] == {"version": 1}
        assert payload["description"] == "Test role"

    def test_skips_none_values(self):
        module = MagicMock()
        module.params = {
            "cluster": None,
            "indices": None,
            "applications": None,
            "run_as": None,
            "metadata": None,
            "description": None,
        }

        payload = security_role.build_payload(module)
        assert payload == {}


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.put.return_value = {"role": {"created": True}}
        mock_client_cls.return_value = mock_client

        security_role.main()

        mock_client.put.assert_called_once()
        call_args = mock_client.put.call_args
        assert "/_security/role/test_role" in call_args[0]
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client_cls.return_value = mock_client

        security_role.main()

        mock_client.put.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.AnsibleModule")
    def test_idempotent(self, mock_module_cls, mock_client_cls, module_params_present, existing_role):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"test_role": existing_role}
        mock_client_cls.return_value = mock_client

        security_role.main()

        mock_client.put.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.AnsibleModule")
    def test_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_role):
        mock_module = MagicMock()
        mock_module.params = dict(module_params_present, description="Updated description")
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"test_role": existing_role}
        mock_client.put.return_value = {"role": {"created": False}}
        mock_client_cls.return_value = mock_client

        security_role.main()

        mock_client.put.assert_called_once()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_role):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"test_role": existing_role}
        mock_client_cls.return_value = mock_client

        security_role.main()

        mock_client.delete.assert_called_once_with("/_security/role/test_role")
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client_cls.return_value = mock_client

        security_role.main()

        mock_client.delete.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
