# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.elastic_watcher EDA event source."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.event_source.elastic_watcher import (
    main,
    _build_search_body,
    _extract_execution,
)


BASE_ARGS = {
    "api_url": "https://elasticsearch.example.com:9200",
    "api_key": "test-api-key",
    "interval": 1,
    "validate_certs": False,
}


def _make_hit(execution_id, watch_id, status="executed", execution_time="2099-01-01T00:00:00.000Z"):
    """Build a minimal watcher history hit."""
    return {
        "_id": execution_id,
        "_source": {
            "watch_id": watch_id,
            "state": status,
            "trigger_event": {
                "type": "schedule",
                "triggered_time": execution_time,
                "schedule": {"scheduled_time": execution_time},
            },
            "result": {
                "execution_time": execution_time,
                "execution_duration": 150,
                "input": {"type": "simple", "status": "success"},
                "condition": {"type": "always", "status": "success", "met": True},
                "actions": [
                    {
                        "id": "notify",
                        "type": "email",
                        "status": "success",
                    }
                ],
            },
            "messages": [],
        },
    }


def _watcher_stats_response(state="started"):
    return {"stats": [{"watcher_state": state, "watch_count": 5}]}


def _mock_response(data, status=200):
    """Create a mock aiohttp response context manager."""
    resp = AsyncMock()
    resp.status = status
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value=data)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ---- Unit tests for helper functions ----

class TestBuildSearchBody:
    def test_basic_body(self):
        body = _build_search_body("2024-01-01T00:00:00Z", [], [])
        filters = body["query"]["bool"]["filter"]
        assert len(filters) == 1  # only range filter
        assert body["size"] == 100

    def test_status_filter(self):
        body = _build_search_body("2024-01-01T00:00:00Z", ["executed", "failed"], [])
        filters = body["query"]["bool"]["filter"]
        assert len(filters) == 2
        assert filters[1]["terms"]["state"] == ["executed", "failed"]

    def test_watch_id_filter(self):
        body = _build_search_body("2024-01-01T00:00:00Z", [], ["disk_alert"])
        filters = body["query"]["bool"]["filter"]
        assert len(filters) == 2
        assert filters[1]["terms"]["watch_id"] == ["disk_alert"]

    def test_both_filters(self):
        body = _build_search_body("2024-01-01T00:00:00Z", ["failed"], ["disk_alert", "cpu_alert"])
        filters = body["query"]["bool"]["filter"]
        assert len(filters) == 3


class TestExtractExecution:
    def test_full_extraction(self):
        hit = _make_hit("exec-1", "disk_space_alert")
        event = _extract_execution(hit)
        assert event["watch_id"] == "disk_space_alert"
        assert event["execution_id"] == "exec-1"
        assert event["status"] == "executed"
        assert event["execution_duration"] == 150
        assert len(event["actions_results"]) == 1

    def test_missing_result(self):
        hit = {"_id": "exec-2", "_source": {"watch_id": "w1", "state": "failed"}}
        event = _extract_execution(hit)
        assert event["watch_id"] == "w1"
        assert event["status"] == "failed"
        assert event["actions_results"] == []


# ---- Async integration tests ----

@pytest.mark.asyncio
async def test_emits_watcher_event():
    """Executed watch should produce an event on the queue."""
    queue = asyncio.Queue()
    stats_payload = _watcher_stats_response("started")
    search_payload = {"hits": {"hits": [_make_hit("exec-100", "disk_watch")]}}

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()

        call_count = 0

        def route_calls(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "/_watcher/stats" in url:
                return _mock_response(stats_payload)
            return _mock_response(search_payload)

        def route_get(url, **kwargs):
            return route_calls(url, **kwargs)

        def route_post(url, **kwargs):
            return route_calls(url, **kwargs)

        session.get = MagicMock(side_effect=route_get)
        session.post = MagicMock(side_effect=route_post)

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = ctx

        task = asyncio.create_task(main(queue, BASE_ARGS))
        try:
            event = await asyncio.wait_for(queue.get(), timeout=5)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    assert "elastic_watcher" in event
    watcher = event["elastic_watcher"]
    assert watcher["watch_id"] == "disk_watch"
    assert watcher["execution_id"] == "exec-100"
    assert watcher["status"] == "executed"


@pytest.mark.asyncio
async def test_status_filter_in_query():
    """status_filter should be passed to the search query body."""
    queue = asyncio.Queue()
    stats_payload = _watcher_stats_response("started")
    search_payload = {"hits": {"hits": []}}
    posted_body = {}

    args = {**BASE_ARGS, "status_filter": ["failed"]}

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()

        def route_get(url, **kwargs):
            return _mock_response(stats_payload)

        def route_post(url, json=None, **kwargs):
            nonlocal posted_body
            if json:
                posted_body = json
            return _mock_response(search_payload)

        session.get = MagicMock(side_effect=route_get)
        session.post = MagicMock(side_effect=route_post)

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = ctx

        task = asyncio.create_task(main(queue, args))
        await asyncio.sleep(0.3)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    filters = posted_body.get("query", {}).get("bool", {}).get("filter", [])
    state_terms = [f for f in filters if "terms" in f and "state" in f.get("terms", {})]
    assert len(state_terms) == 1
    assert state_terms[0]["terms"]["state"] == ["failed"]


@pytest.mark.asyncio
async def test_watch_id_filter_in_query():
    """watch_id_filter should be passed to the search query body."""
    queue = asyncio.Queue()
    stats_payload = _watcher_stats_response("started")
    search_payload = {"hits": {"hits": []}}
    posted_body = {}

    args = {**BASE_ARGS, "watch_id_filter": ["cpu_alert", "mem_alert"]}

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(stats_payload))

        def capture_post(url, json=None, **kwargs):
            nonlocal posted_body
            if json:
                posted_body = json
            return _mock_response(search_payload)

        session.post = MagicMock(side_effect=capture_post)

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = ctx

        task = asyncio.create_task(main(queue, args))
        await asyncio.sleep(0.3)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    filters = posted_body.get("query", {}).get("bool", {}).get("filter", [])
    wid_terms = [f for f in filters if "terms" in f and "watch_id" in f.get("terms", {})]
    assert len(wid_terms) == 1
    assert set(wid_terms[0]["terms"]["watch_id"]) == {"cpu_alert", "mem_alert"}


@pytest.mark.asyncio
async def test_no_kbn_xsrf_header():
    """Watcher hits Elasticsearch directly -- kbn-xsrf header must NOT be present."""
    queue = asyncio.Queue()
    captured_headers = {}

    with patch("aiohttp.ClientSession") as mock_session_cls:
        def capture_init(*_args, **kwargs):
            nonlocal captured_headers
            captured_headers = kwargs.get("headers", {})
            session = AsyncMock()
            session.get = MagicMock(return_value=_mock_response(_watcher_stats_response()))
            session.post = MagicMock(return_value=_mock_response({"hits": {"hits": []}}))
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=session)
            ctx.__aexit__ = AsyncMock(return_value=False)
            return ctx

        mock_session_cls.side_effect = capture_init

        task = asyncio.create_task(main(queue, BASE_ARGS))
        await asyncio.sleep(0.3)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert "kbn-xsrf" not in captured_headers


@pytest.mark.asyncio
async def test_watcher_stopped_continues():
    """If watcher is stopped, the plugin should warn but continue polling."""
    queue = asyncio.Queue()
    stats_payload = _watcher_stats_response("stopped")
    search_payload = {"hits": {"hits": [_make_hit("exec-200", "test_watch")]}}

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(stats_payload))
        session.post = MagicMock(return_value=_mock_response(search_payload))

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = ctx

        task = asyncio.create_task(main(queue, BASE_ARGS))
        try:
            event = await asyncio.wait_for(queue.get(), timeout=5)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    # Even with watcher "stopped", events from history should still be emitted
    assert event["elastic_watcher"]["watch_id"] == "test_watch"


@pytest.mark.asyncio
async def test_api_error_does_not_crash():
    """HTTP errors should be caught without crashing the loop."""
    queue = asyncio.Queue()

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(_watcher_stats_response()))

        err_resp = AsyncMock()
        err_resp.raise_for_status = MagicMock(side_effect=Exception("Connection reset"))
        err_ctx = AsyncMock()
        err_ctx.__aenter__ = AsyncMock(return_value=err_resp)
        err_ctx.__aexit__ = AsyncMock(return_value=False)
        session.post = MagicMock(return_value=err_ctx)

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = ctx

        task = asyncio.create_task(main(queue, BASE_ARGS))
        await asyncio.sleep(0.3)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert queue.empty()
