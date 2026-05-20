# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_space
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


@pytest.fixture
def module_params_present():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "present",
        "space_id": "marketing",
        "name": "Marketing",
        "description": "Marketing team space",
        "color": "#aabbcc",
        "disabled_features": [],
        "initials": "MK",
        "image_url": None,
    }


@pytest.fixture
def module_params_absent():
    return {
        "api_key": "test-key",
        "api_url": "https://localhost:5601",
        "validate_certs": False,
        "request_timeout": 30,
        "state": "absent",
        "space_id": "marketing",
        "name": None,
        "description": None,
        "color": None,
        "disabled_features": None,
        "initials": None,
        "image_url": None,
    }


@pytest.fixture
def existing_space():
    return {
        "id": "marketing",
        "name": "Marketing",
        "description": "Marketing team space",
        "color": "#aabbcc",
        "disabledFeatures": [],
        "initials": "MK",
    }


class TestGetCurrentState:
    def test_returns_space_when_exists(self):
        client = MagicMock()
        client.get.return_value = {"id": "marketing", "name": "Marketing"}
        module = MagicMock()
        module.params = {"space_id": "marketing"}

        result = kibana_space.get_current_state(client, module)
        assert result == {"id": "marketing", "name": "Marketing"}
        client.get.assert_called_once_with("/api/spaces/space/marketing")

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)
        module = MagicMock()
        module.params = {"space_id": "nonexistent"}

        result = kibana_space.get_current_state(client, module)
        assert result is None

    def test_returns_none_when_id_is_none(self):
        client = MagicMock()
        module = MagicMock()
        module.params = {"space_id": None}

        result = kibana_space.get_current_state(client, module)
        assert result is None


class TestNeedsUpdate:
    def test_needs_update_when_current_is_none(self):
        assert kibana_space.needs_update(None, {"name": "Test"}) is True

    def test_no_update_when_identical(self, existing_space):
        desired = {"id": "marketing", "name": "Marketing", "description": "Marketing team space"}
        assert kibana_space.needs_update(existing_space, desired) is False

    def test_needs_update_when_different(self, existing_space):
        desired = {"name": "Marketing Updated"}
        assert kibana_space.needs_update(existing_space, desired) is True

    def test_skips_none_values(self, existing_space):
        desired = {"name": None, "description": None}
        assert kibana_space.needs_update(existing_space, desired) is False


class TestBuildPayload:
    def test_builds_full_payload(self, module_params_present):
        module = MagicMock()
        module.params = module_params_present

        payload = kibana_space.build_payload(module)
        assert payload["id"] == "marketing"
        assert payload["name"] == "Marketing"
        assert payload["description"] == "Marketing team space"
        assert payload["color"] == "#aabbcc"
        assert payload["disabledFeatures"] == []
        assert payload["initials"] == "MK"

    def test_skips_none_values(self):
        module = MagicMock()
        module.params = {
            "space_id": "test",
            "name": None,
            "description": None,
            "color": None,
            "disabled_features": None,
            "initials": None,
            "image_url": None,
        }

        payload = kibana_space.build_payload(module)
        assert payload == {"id": "test"}


class TestMain:
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.AnsibleModule")
    def test_create(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.post.return_value = {"id": "marketing", "name": "Marketing"}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_space.main()

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/api/spaces/space" in call_args[0]
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.AnsibleModule")
    def test_create_check_mode(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = True
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_space.main()

        mock_client.post.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.AnsibleModule")
    def test_idempotent(self, mock_module_cls, mock_client_cls, module_params_present, existing_space):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = existing_space
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_space.main()

        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.AnsibleModule")
    def test_update(self, mock_module_cls, mock_client_cls, module_params_present, existing_space):
        mock_module = MagicMock()
        mock_module.params = dict(module_params_present, name="Marketing Updated")
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = existing_space
        mock_client.put.return_value = {"id": "marketing", "name": "Marketing Updated"}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_space.main()

        mock_client.put.assert_called_once()
        call_args = mock_client.put.call_args
        assert "/api/spaces/space/marketing" in call_args[0]
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.AnsibleModule")
    def test_delete(self, mock_module_cls, mock_client_cls, module_params_absent, existing_space):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.return_value = existing_space
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_space.main()

        mock_client.delete.assert_called_once_with("/api/spaces/space/marketing")
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is True

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.AnsibleModule")
    def test_delete_idempotent(self, mock_module_cls, mock_client_cls, module_params_absent):
        mock_module = MagicMock()
        mock_module.params = module_params_absent
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_space.main()

        mock_client.delete.assert_not_called()
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.Client")
    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_space.AnsibleModule")
    def test_sets_kbn_xsrf_header(self, mock_module_cls, mock_client_cls, module_params_present):
        mock_module = MagicMock()
        mock_module.params = module_params_present
        mock_module.check_mode = False
        mock_module_cls.return_value = mock_module

        mock_client = MagicMock()
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.post.return_value = {}
        mock_client.headers = {}
        mock_client_cls.return_value = mock_client

        kibana_space.main()

        assert mock_client.headers["kbn-xsrf"] == "true"
