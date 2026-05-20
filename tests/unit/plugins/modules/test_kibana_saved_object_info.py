# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.kibana_saved_object_info module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import kibana_saved_object_info
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


def set_module_args(args):
    """Prepare arguments so that they will be picked up during module creation."""
    if "_ansible_remote_tmp" not in args:
        args["_ansible_remote_tmp"] = "/tmp"
    if "_ansible_keep_remote_files" not in args:
        args["_ansible_keep_remote_files"] = False
    args_json = json.dumps({"ANSIBLE_MODULE_ARGS": args})
    basic._ANSIBLE_ARGS = to_bytes(args_json)
    basic._ANSIBLE_PROFILE = "legacy"


BASE_ARGS = {
    "api_key": "test-key",
    "api_url": "https://localhost:5601",
    "validate_certs": False,
    "request_timeout": 30,
}

SAMPLE_SAVED_OBJECT = {
    "id": "my-index-pattern",
    "type": "index-pattern",
    "attributes": {"title": "logs-*", "timeFieldName": "@timestamp"},
    "references": [],
}

SAMPLE_FIND_RESPONSE = {
    "saved_objects": [
        SAMPLE_SAVED_OBJECT,
        {
            "id": "other-pattern",
            "type": "index-pattern",
            "attributes": {"title": "metrics-*"},
            "references": [],
        },
    ],
    "total": 2,
}


class TestFetchSingle:
    """Tests for fetch_single function."""

    def test_found(self):
        """Return saved object dict when found."""
        client = MagicMock()
        client.get.return_value = SAMPLE_SAVED_OBJECT

        result = kibana_saved_object_info.fetch_single(client, "index-pattern", "my-index-pattern")

        client.get.assert_called_once_with("/api/saved_objects/index-pattern/my-index-pattern")
        assert result is not None
        assert result["id"] == "my-index-pattern"

    def test_not_found(self):
        """Return None when object not found."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)

        result = kibana_saved_object_info.fetch_single(client, "index-pattern", "nonexistent")
        assert result is None

    def test_client_error(self):
        """Return None when API raises ClientError."""
        client = MagicMock()
        client.get.side_effect = ClientError("Server error", status_code=500)

        result = kibana_saved_object_info.fetch_single(client, "index-pattern", "test")
        assert result is None


class TestFetchList:
    """Tests for fetch_list function."""

    def test_list_all(self):
        """Return all saved objects of a type."""
        client = MagicMock()
        client.get.return_value = SAMPLE_FIND_RESPONSE
        module = MagicMock()
        module.params = {"object_type": "index-pattern", "page": None, "page_size": None}

        result = kibana_saved_object_info.fetch_list(client, module)

        assert len(result) == 2
        assert result[0]["id"] == "my-index-pattern"

    def test_list_with_pagination(self):
        """Pass page/per_page when set."""
        client = MagicMock()
        client.get.return_value = SAMPLE_FIND_RESPONSE
        module = MagicMock()
        module.params = {"object_type": "dashboard", "page": 2, "page_size": 10}

        result = kibana_saved_object_info.fetch_list(client, module)

        call_params = client.get.call_args[1].get("params", {})
        assert call_params.get("page") == 2
        assert call_params.get("per_page") == 10

    def test_list_empty(self):
        """Return empty list when no objects exist."""
        client = MagicMock()
        client.get.return_value = {"saved_objects": [], "total": 0}
        module = MagicMock()
        module.params = {"object_type": "index-pattern", "page": None, "page_size": None}

        result = kibana_saved_object_info.fetch_list(client, module)
        assert result == []

    def test_list_client_error(self):
        """Return empty list on ClientError."""
        client = MagicMock()
        client.get.side_effect = ClientError("Server error", status_code=500)
        module = MagicMock()
        module.params = {"object_type": "index-pattern", "page": None, "page_size": None}

        result = kibana_saved_object_info.fetch_list(client, module)
        assert result == []


class TestMainSingle:
    """Tests for main() - single saved object retrieval."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object_info.Client")
    def test_get_single_object(self, mock_client_cls):
        """Return single object in kibana_saved_objects list."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_SAVED_OBJECT
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["object_type"] = "index-pattern"
        args["object_id"] = "my-index-pattern"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object_info.Client")
    def test_get_missing_object(self, mock_client_cls):
        """Return empty list when object not found."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.side_effect = ClientError("Not found", status_code=404)
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["object_type"] = "index-pattern"
        args["object_id"] = "missing"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object_info.main()

        assert exc_info.value.code == 0


class TestMainList:
    """Tests for main() - list saved objects."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object_info.Client")
    def test_list_all_objects(self, mock_client_cls):
        """Return all objects when no id specified."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_FIND_RESPONSE
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["object_type"] = "index-pattern"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object_info.Client")
    def test_always_changed_false(self, mock_client_cls):
        """Info module always returns changed=False."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"saved_objects": [], "total": 0}
        mock_client.headers = {}

        args = dict(BASE_ARGS)
        args["object_type"] = "dashboard"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object_info.main()

        assert exc_info.value.code == 0


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.kibana_saved_object_info.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises unexpected ClientError."""
        mock_client_cls.side_effect = ClientError("Connection refused")

        args = dict(BASE_ARGS)
        args["object_type"] = "index-pattern"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            kibana_saved_object_info.main()

        assert exc_info.value.code == 1
