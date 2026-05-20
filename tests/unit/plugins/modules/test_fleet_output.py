# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import fleet_output
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "output_id": None,
        "name": "My ES Output",
        "type": "elasticsearch",
        "hosts": ["https://es:9200"],
        "is_default": False,
        "is_default_monitoring": False,
        "config_yaml": None,
        "ssl": None,
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "output_id": "output-123",
        "name": "My ES Output",
        "type": None,
        "hosts": None,
        "is_default": None,
        "is_default_monitoring": None,
        "config_yaml": None,
        "ssl": None,
    }


@pytest.fixture
def existing_output():
    return {
        "id": "output-123",
        "name": "My ES Output",
        "type": "elasticsearch",
        "hosts": ["https://es:9200"],
        "is_default": False,
        "is_default_monitoring": False,
    }


class TestGetCurrentState:
    def test_returns_output_by_id(self):
        client = MagicMock()
        client.get.return_value = {"item": {"id": "output-123", "name": "My ES Output"}}
        module = MagicMock()
        module.params = {"output_id": "output-123", "name": "My ES Output"}

        result = fleet_output.get_current_state(client, module)
        assert result == {"id": "output-123", "name": "My ES Output"}

    def test_returns_output_by_name(self):
        client = MagicMock()
        client.get.return_value = {
            "items": [
                {"id": "output-123", "name": "My ES Output"},
                {"id": "output-456", "name": "Other"},
            ]
        }
        module = MagicMock()
        module.params = {"output_id": None, "name": "My ES Output"}

        result = fleet_output.get_current_state(client, module)
        assert result["name"] == "My ES Output"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"output_id": "nonexistent", "name": "test"}

        result = fleet_output.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    def test_needs_update_when_current_is_none(self):
        assert fleet_output.needs_update(None, {"name": "Test"}) is True

    def test_no_update_when_identical(self, existing_output):
        desired = {"name": "My ES Output", "type": "elasticsearch", "hosts": ["https://es:9200"]}
        assert fleet_output.needs_update(existing_output, desired) is False

    def test_needs_update_when_different(self, existing_output):
        desired = {"name": "Updated Output"}
        assert fleet_output.needs_update(existing_output, desired) is True

    def test_skips_none_values(self, existing_output):
        desired = {"name": None, "hosts": None}
        assert fleet_output.needs_update(existing_output, desired) is False


class TestBuildPayload:
    def test_build_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = fleet_output.build_payload(module)
        assert payload["name"] == "My ES Output"
        assert payload["type"] == "elasticsearch"
        assert payload["hosts"] == ["https://es:9200"]


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        mock_client.post.return_value = {"item": {"id": "output-new", "name": "My ES Output"}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_output.main()

        mock_client.post.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"items": []}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_output.main()

        mock_client.post.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.AnsibleModule")
    def test_idempotent(self, mock_module_cls, mock_client_cls, module_params_present, existing_output):
        mock_module = MagicMock()
        mock_module.params = dict(module_params_present, output_id="output-123")
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_output}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_output.main()

        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.AnsibleModule")
    def test_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_output):
        mock_module = MagicMock()
        params = dict(module_params_present, output_id="output-123", name="Updated Output")
        mock_module.params = params
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_output}
        mock_client.put.return_value = {"item": {"id": "output-123", "name": "Updated Output"}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_output.main()

        mock_client.put.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_output):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"item": existing_output}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_output.main()

        mock_client.delete.assert_called_once_with("/api/fleet/outputs/output-123")
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        fleet_output.main()

        mock_client.delete.assert_not_called()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.fleet_output.AnsibleModule")
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

        fleet_output.main()

        assert mock_client.headers["kbn-xsrf"] == "true"
