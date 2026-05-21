# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import fleet_server_host
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "host_id": None,
        "name": "Fleet Server",
        "host_urls": ["https://fleet:8220"],
        "is_default": False,
        "is_preconfigured": None,
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "host_id": "host-123",
        "name": "Fleet Server",
        "host_urls": None,
        "is_default": None,
        "is_preconfigured": None,
    }


@pytest.fixture
def existing_host():
    return {
        "id": "host-123",
        "name": "Fleet Server",
        "host_urls": ["https://fleet:8220"],
        "is_default": False,
    }


class TestGetCurrentState:
    def test_returns_host_by_id(self):
        client = MagicMock()
        client.get.return_value = {"item": {"id": "host-123", "name": "Fleet Server"}}
        module = MagicMock()
        module.params = {"host_id": "host-123", "name": "Fleet Server"}

        result = fleet_server_host.get_current_state(client, module)
        assert result == {"id": "host-123", "name": "Fleet Server"}

    def test_returns_host_by_name(self):
        client = MagicMock()
        client.get.return_value = {
            "items": [
                {"id": "host-123", "name": "Fleet Server"},
                {"id": "host-456", "name": "Other"},
            ]
        }
        module = MagicMock()
        module.params = {"host_id": None, "name": "Fleet Server"}

        result = fleet_server_host.get_current_state(client, module)
        assert result["name"] == "Fleet Server"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"host_id": "nonexistent", "name": "test"}

        result = fleet_server_host.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    def test_needs_update_when_current_is_none(self):
        assert fleet_server_host.needs_update(None, {"name": "Test"}) is True

    def test_no_update_when_identical(self, existing_host):
        desired = {"name": "Fleet Server", "host_urls": ["https://fleet:8220"]}
        assert fleet_server_host.needs_update(existing_host, desired) is False

    def test_needs_update_when_different(self, existing_host):
        desired = {"name": "Fleet Server Updated"}
        assert fleet_server_host.needs_update(existing_host, desired) is True

    def test_skips_none_values(self, existing_host):
        desired = {"name": None, "host_urls": None}
        assert fleet_server_host.needs_update(existing_host, desired) is False


class TestBuildPayload:
    def test_build_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = fleet_server_host.build_payload(module)
        assert payload["name"] == "Fleet Server"
        assert payload["host_urls"] == ["https://fleet:8220"]
        assert payload["is_default"] is False


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        mock_client.post.return_value = {"item": {"id": "host-new", "name": "Fleet Server"}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_server_host.main()

        mock_client.post.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_server_host.main()

        mock_client.post.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.AnsibleModule")
    def test_idempotent(self, mock_module_cls, mock_client_cls, module_params_present, existing_host):
        mock_module = MagicMock()
        mock_module.params = dict(module_params_present, host_id="host-123")
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_host}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_server_host.main()

        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.AnsibleModule")
    def test_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_host):
        mock_module = MagicMock()
        params = dict(module_params_present, host_id="host-123", name="Fleet Server Updated")
        mock_module.params = params
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_host}
        mock_client.put.return_value = {"item": {"id": "host-123", "name": "Fleet Server Updated"}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_server_host.main()

        mock_client.put.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_host):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_host}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_server_host.main()

        mock_client.delete.assert_called_once_with("/api/fleet/fleet_server_hosts/host-123")
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_server_host.main()

        mock_client.delete.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_server_host.AnsibleModule")
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

        fleet_server_host.main()

        assert mock_client.headers["kbn-xsrf"] == "true"
