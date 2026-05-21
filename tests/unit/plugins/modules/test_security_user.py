# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import security_user
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:9200",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "username": "john_doe",
        "password": "s3cret!",
        "roles": ["admin"],
        "full_name": "John Doe",
        "email": "john@example.com",
        "metadata": {},
        "enabled": True,
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:9200",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "username": "john_doe",
        "password": None,
        "roles": None,
        "full_name": None,
        "email": None,
        "metadata": None,
        "enabled": True,
    }


@pytest.fixture
def existing_user():
    return {
        "roles": ["admin"],
        "full_name": "John Doe",
        "email": "john@example.com",
        "metadata": {},
        "enabled": True,
    }


class TestGetCurrentState:
    def test_returns_user_when_exists(self):
        client = MagicMock()
        client.get.return_value = {"john_doe": {"roles": ["admin"], "enabled": True}}
        module = MagicMock()
        module.params = {"username": "john_doe"}

        result = security_user.get_current_state(client, module)
        assert result == {"roles": ["admin"], "enabled": True}

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"username": "nonexistent"}

        result = security_user.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    def test_needs_update_when_current_is_none(self):
        assert security_user.needs_update(None, {"roles": ["admin"]}) is True

    def test_no_update_when_identical(self, existing_user):
        desired = {"roles": ["admin"], "full_name": "John Doe", "enabled": True}
        assert security_user.needs_update(existing_user, desired) is False

    def test_needs_update_when_different(self, existing_user):
        desired = {"full_name": "Jane Doe"}
        assert security_user.needs_update(existing_user, desired) is True

    def test_password_is_skipped_in_comparison(self, existing_user):
        desired = {"password": "newpassword", "roles": ["admin"], "full_name": "John Doe", "enabled": True}
        assert security_user.needs_update(existing_user, desired) is False


class TestBuildPayload:
    def test_builds_full_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = security_user.build_payload(module)
        assert payload["password"] == "s3cret!"
        assert payload["roles"] == ["admin"]
        assert payload["full_name"] == "John Doe"
        assert payload["email"] == "john@example.com"
        assert payload["enabled"] is True

    def test_skips_none_values(self):
        module = MagicMock()
        module.params = {
            "password": None,
            "roles": None,
            "full_name": None,
            "email": None,
            "metadata": None,
            "enabled": None,
        }

        payload = security_user.build_payload(module)
        assert payload == {}


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.put.return_value = {"created": True}
        mock_client_cls.return_value = mock_client

        security_user.main()

        mock_client.put.assert_called_once()
        call_args = mock_client.put.call_args
        assert "/_security/user/john_doe" in call_args[0]
        # Verify password is in the payload sent to API
        assert call_args[1]["data"]["password"] == "s3cret!"
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True
        # Verify password is NOT in the result diff
        assert "password" not in result["diff"]["after"]

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client_cls.return_value = mock_client

        security_user.main()

        mock_client.put.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.AnsibleModule")
    def test_idempotent(self, mock_module_cls, mock_client_cls, module_params_present, existing_user):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"john_doe": existing_user}
        mock_client_cls.return_value = mock_client

        security_user.main()

        mock_client.put.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.AnsibleModule")
    def test_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_user):
        mock_module = MagicMock()
        mock_module.params = dict(module_params_present, full_name="Jane Doe")
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"john_doe": existing_user}
        mock_client.put.return_value = {"created": False}
        mock_client_cls.return_value = mock_client

        security_user.main()

        mock_client.put.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_user):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"john_doe": existing_user}
        mock_client_cls.return_value = mock_client

        security_user.main()

        mock_client.delete.assert_called_once_with("/_security/user/john_doe")
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.security_user.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client_cls.return_value = mock_client

        security_user.main()

        mock_client.delete.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
