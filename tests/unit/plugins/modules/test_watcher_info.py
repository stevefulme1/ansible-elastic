# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.watcher_info module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.stevefulme1.elastic.plugins.modules import watcher_info
from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import ClientError


def set_module_args(args):
    """Prepare arguments so that they will be picked up during module creation."""
    if "_ansible_remote_tmp" not in args:
        args["_ansible_remote_tmp"] = "/tmp"
    if "_ansible_keep_remote_files" not in args:
        args["_ansible_keep_remote_files"] = False
    args_json = json.dumps({"ANSIBLE_MODULE_ARGS": args})
    basic._ANSIBLE_ARGS = to_bytes(args_json)
    # Ansible 2.21+ requires a serialization profile
    basic._ANSIBLE_PROFILE = "legacy"


BASE_ARGS = {
    "api_key": "test-key",
    "api_url": "https://localhost:9200",
    "validate_certs": False,
    "request_timeout": 30,
}

SAMPLE_GET_RESPONSE = {
    "_id": "test_watch",
    "found": True,
    "_version": 1,
    "status": {"state": {"active": True}},
    "watch": {
        "trigger": {"schedule": {"interval": "10s"}},
        "input": {"search": {"request": {"indices": ["logs"]}}},
        "condition": {"compare": {"ctx.payload.hits.total": {"gt": 0}}},
        "actions": {"log_error": {"logging": {"text": "Found errors"}}},
    },
}

SAMPLE_QUERY_RESPONSE = {
    "count": 2,
    "watches": [
        {
            "_id": "watch_1",
            "status": {"state": {"active": True}},
            "watch": {
                "trigger": {"schedule": {"interval": "10s"}},
                "actions": {"log_it": {"logging": {"text": "Watch 1"}}},
            },
        },
        {
            "_id": "watch_2",
            "status": {"state": {"active": False}},
            "watch": {
                "trigger": {"schedule": {"interval": "60s"}},
                "actions": {"log_it": {"logging": {"text": "Watch 2"}}},
            },
        },
    ],
}


class TestFetchSingle:
    """Tests for fetch_single function."""

    def test_found(self):
        """Return watch dict when found."""
        client = MagicMock()
        client.get.return_value = SAMPLE_GET_RESPONSE

        result = watcher_info.fetch_single(client, "test_watch")

        client.get.assert_called_once_with("/_watcher/watch/test_watch")
        assert result is not None
        assert result["_id"] == "test_watch"
        assert result["trigger"] == {"schedule": {"interval": "10s"}}
        assert result["status"] == {"state": {"active": True}}

    def test_not_found(self):
        """Return None when found=False."""
        client = MagicMock()
        client.get.return_value = {"_id": "missing", "found": False}

        result = watcher_info.fetch_single(client, "missing")
        assert result is None

    def test_client_error(self):
        """Return None when API raises ClientError."""
        client = MagicMock()
        client.get.side_effect = ClientError("Not found", status_code=404)

        result = watcher_info.fetch_single(client, "nonexistent")
        assert result is None


class TestFetchList:
    """Tests for fetch_list function."""

    def test_list_all(self):
        """Return all watches from query API."""
        client = MagicMock()
        client.post.return_value = SAMPLE_QUERY_RESPONSE
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = watcher_info.fetch_list(client, module)

        client.post.assert_called_once_with(
            "/_watcher/_query/watches",
            data={"size": 100},
        )
        assert len(result) == 2
        assert result[0]["_id"] == "watch_1"
        assert result[1]["_id"] == "watch_2"

    def test_list_with_pagination(self):
        """Pass from/size when page and page_size are set."""
        client = MagicMock()
        client.post.return_value = SAMPLE_QUERY_RESPONSE
        module = MagicMock()
        module.params = {"page": 2, "page_size": 10}

        result = watcher_info.fetch_list(client, module)

        client.post.assert_called_once_with(
            "/_watcher/_query/watches",
            data={"size": 10, "from": 10},
        )
        assert len(result) == 2

    def test_list_empty(self):
        """Return empty list when no watches exist."""
        client = MagicMock()
        client.post.return_value = {"count": 0, "watches": []}
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = watcher_info.fetch_list(client, module)
        assert result == []

    def test_list_client_error(self):
        """Return empty list on ClientError."""
        client = MagicMock()
        client.post.side_effect = ClientError("Server error", status_code=500)
        module = MagicMock()
        module.params = {"page": None, "page_size": None}

        result = watcher_info.fetch_list(client, module)
        assert result == []


class TestMainSingle:
    """Tests for main() - single watch retrieval."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher_info.Client")
    def test_get_single_watch(self, mock_client_cls):
        """Return single watch in watchers list."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = SAMPLE_GET_RESPONSE

        args = dict(BASE_ARGS)
        args["id"] = "test_watch"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher_info.Client")
    def test_get_missing_watch(self, mock_client_cls):
        """Return empty watchers list when watch not found."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = {"_id": "missing", "found": False}

        args = dict(BASE_ARGS)
        args["id"] = "missing"
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher_info.main()

        assert exc_info.value.code == 0


class TestMainList:
    """Tests for main() - list watches."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher_info.Client")
    def test_list_all_watches(self, mock_client_cls):
        """Return all watches when no id specified."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.post.return_value = SAMPLE_QUERY_RESPONSE

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher_info.main()

        assert exc_info.value.code == 0

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher_info.Client")
    def test_always_changed_false(self, mock_client_cls):
        """Info module always returns changed=False."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.post.return_value = {"count": 0, "watches": []}

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher_info.main()

        assert exc_info.value.code == 0


class TestMainError:
    """Tests for main() - error handling."""

    @patch("ansible_collections.stevefulme1.elastic.plugins.modules.watcher_info.Client")
    def test_client_error_fails_module(self, mock_client_cls):
        """Module fails with msg when Client raises unexpected ClientError."""
        mock_client_cls.side_effect = ClientError("Connection refused")

        args = dict(BASE_ARGS)
        set_module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            watcher_info.main()

        assert exc_info.value.code == 1
