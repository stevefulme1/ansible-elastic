# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_data_view
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "data_view_id": None,
        "title": "logs-*",
        "time_field_name": "@timestamp",
        "name": "My Logs",
        "source_filters": None,
        "field_formats": None,
        "runtime_field_map": None,
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "data_view_id": "dv-123",
        "title": None,
        "time_field_name": None,
        "name": None,
        "source_filters": None,
        "field_formats": None,
        "runtime_field_map": None,
    }


@pytest.fixture
def existing_data_view():
    return {
        "id": "dv-123",
        "title": "logs-*",
        "timeFieldName": "@timestamp",
        "name": "My Logs",
    }


class TestGetCurrentState:
    def test_returns_data_view_by_id(self):
        client = MagicMock()
        client.get.return_value = {"data_view": {"id": "dv-123", "title": "logs-*"}}
        module = MagicMock()
        module.params = {"data_view_id": "dv-123", "title": None}

        result = kibana_data_view.get_current_state(client, module)
        assert result == {"id": "dv-123", "title": "logs-*"}

    def test_returns_data_view_by_title(self):
        client = MagicMock()
        client.get.return_value = {
            "data_view": [
                {"id": "dv-123", "title": "logs-*"},
                {"id": "dv-456", "title": "metrics-*"},
            ]
        }
        module = MagicMock()
        module.params = {"data_view_id": None, "title": "logs-*"}

        result = kibana_data_view.get_current_state(client, module)
        assert result["title"] == "logs-*"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"data_view_id": "nonexistent", "title": None}

        result = kibana_data_view.get_current_state(client, module)
        assert result is None

    def test_returns_none_when_no_id_or_title(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"data_view_id": None, "title": None}

        result = kibana_data_view.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    def test_needs_update_when_current_is_none(self):
        assert kibana_data_view.needs_update(None, {"title": "logs-*"}) is True

    def test_no_update_when_identical(self, existing_data_view):
        desired = {"title": "logs-*", "timeFieldName": "@timestamp", "name": "My Logs"}
        assert kibana_data_view.needs_update(existing_data_view, desired) is False

    def test_needs_update_when_different(self, existing_data_view):
        desired = {"name": "Updated Logs"}
        assert kibana_data_view.needs_update(existing_data_view, desired) is True

    def test_skips_none_values(self, existing_data_view):
        desired = {"title": None, "name": None}
        assert kibana_data_view.needs_update(existing_data_view, desired) is False


class TestBuildPayload:
    def test_builds_full_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = kibana_data_view.build_payload(module)
        assert payload["title"] == "logs-*"
        assert payload["timeFieldName"] == "@timestamp"
        assert payload["name"] == "My Logs"

    def test_skips_none_values(self):
        module = MagicMock()
        module.params = {
            "data_view_id": None,
            "title": None,
            "time_field_name": None,
            "name": None,
            "source_filters": None,
            "field_formats": None,
            "runtime_field_map": None,
        }

        payload = kibana_data_view.build_payload(module)
        assert payload == {}

    def test_includes_id_when_provided(self):
        module = MagicMock()
        module.params = {
            "data_view_id": "dv-123",
            "title": "logs-*",
            "time_field_name": None,
            "name": None,
            "source_filters": None,
            "field_formats": None,
            "runtime_field_map": None,
        }

        payload = kibana_data_view.build_payload(module)
        assert payload["id"] == "dv-123"
        assert payload["title"] == "logs-*"


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"data_view": []}
        mock_client.post.return_value = {"data_view": {"id": "dv-new", "title": "logs-*"}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_data_view.main()

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/api/data_views/data_view" in call_args[0]
        assert "data_view" in call_args[1]["data"]
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"data_view": []}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_data_view.main()

        mock_client.post.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.AnsibleModule")
    def test_idempotent(self, mock_module_cls, mock_client_cls, module_params_present, existing_data_view):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"data_view": [existing_data_view]}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_data_view.main()

        # Should not call post for create or update
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.AnsibleModule")
    def test_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_data_view):
        mock_module = MagicMock()
        params = dict(module_params_present, data_view_id="dv-123", name="Updated Logs")
        mock_module.params = params
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"data_view": existing_data_view}
        mock_client.post.return_value = {"data_view": {"id": "dv-123", "name": "Updated Logs"}}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_data_view.main()

        # Update uses POST /api/data_views/data_view/{id}
        assert mock_client.post.call_count == 1
        call_args = mock_client.post.call_args
        assert "dv-123" in call_args[0][0]
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_data_view):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = {"data_view": existing_data_view}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_data_view.main()

        mock_client.delete.assert_called_once_with("/api/data_views/data_view/dv-123")
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_data_view.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_data_view.main()

        mock_client.delete.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
