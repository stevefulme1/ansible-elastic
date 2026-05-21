# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import security_role_mapping
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:9200",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "name": "my_mapping",
        "roles": ["admin"],
        "enabled": True,
        "rules": {"field": {"username": "*"}},
        "metadata": {},
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:9200",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "name": "my_mapping",
        "roles": None,
        "enabled": True,
        "rules": None,
        "metadata": None,
    }


@pytest.fixture
def existing_mapping():
    return {
        "roles": ["admin"],
        "enabled": True,
        "rules": {"field": {"username": "*"}},
        "metadata": {},
    }


class TestGetCurrentState:
    def test_returns_mapping_when_exists(self):
        client = MagicMock()
        client.get.return_value = {"my_mapping": {"roles": ["admin"], "enabled": True}}
        module = MagicMock()
        module.params = {"name": "my_mapping"}

        result = security_role_mapping.get_current_state(client, module)
        assert result == {"roles": ["admin"], "enabled": True}

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"name": "nonexistent"}

        result = security_role_mapping.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    def test_needs_update_when_current_is_none(self):
        assert security_role_mapping.needs_update(None, {"roles": ["admin"]}) is True

    def test_no_update_when_identical(self, existing_mapping):
        desired = {"roles": ["admin"], "enabled": True}
        assert security_role_mapping.needs_update(existing_mapping, desired) is False

    def test_needs_update_when_different(self, existing_mapping):
        desired = {"roles": ["viewer"]}
        assert security_role_mapping.needs_update(existing_mapping, desired) is True


class TestBuildPayload:
    def test_builds_full_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = security_role_mapping.build_payload(module)
        assert payload["roles"] == ["admin"]
        assert payload["enabled"] is True
        assert payload["rules"] == {"field": {"username": "*"}}

    def test_skips_none_values(self):
        module = MagicMock()
        module.params = {
            "roles": None,
            "enabled": None,
            "rules": None,
            "metadata": None,
        }

        payload = security_role_mapping.build_payload(module)
        assert payload == {}


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.put.return_value = {"role_mapping": {"created": True}}
        mock_client_cls.return_value = mock_client

        security_role_mapping.main()

        mock_client.put.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client_cls.return_value = mock_client

        security_role_mapping.main()

        mock_client.put.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.AnsibleModule")
    def test_idempotent(self, mock_module_cls, mock_client_cls, module_params_present, existing_mapping):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"my_mapping": existing_mapping}
        mock_client_cls.return_value = mock_client

        security_role_mapping.main()

        mock_client.put.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.AnsibleModule")
    def test_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_mapping):
        mock_module = MagicMock()
        mock_module.params = dict(module_params_present, roles=["viewer"])
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"my_mapping": existing_mapping}
        mock_client.put.return_value = {"role_mapping": {"created": False}}
        mock_client_cls.return_value = mock_client

        security_role_mapping.main()

        mock_client.put.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_mapping):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"my_mapping": existing_mapping}
        mock_client_cls.return_value = mock_client

        security_role_mapping.main()

        mock_client.delete.assert_called_once_with("/_security/role_mapping/my_mapping")
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_role_mapping.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client_cls.return_value = mock_client

        security_role_mapping.main()

        mock_client.delete.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
