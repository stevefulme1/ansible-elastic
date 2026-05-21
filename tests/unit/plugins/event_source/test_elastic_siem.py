# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.elastic_siem EDA event source."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.event_source.elastic_siem import (
    main,
    _build_search_body,
    _extract_signal,
)


BASE_ARGS = {
    "api_url": "https://kibana.example.com",
    "api_key": "test-api-key",
    "interval": 1,
    "validate_certs": False,
}


def _make_hit(signal_id, rule_name, severity="high", risk_score=75, host_name="web01", source_ip="10.0.0.1"):
    """Build a minimal SIEM signal hit."""
    return {
        "_id": signal_id,
        "_source": {
            "@timestamp": "2099-01-01T00:00:00.000Z",
            "signal": {
                "status": "open",
                "rule": {
                    "id": f"rule-{signal_id}",
                    "name": rule_name,
                    "severity": severity,
                    "risk_score": risk_score,
                    "description": f"Test rule {rule_name}",
                    "tags": ["test"],
                },
                "original_event": {"action": "blocked"},
            },
            "host": {"name": host_name},
            "source": {"ip": source_ip},
        },
    }


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
        body = _build_search_body("2024-01-01T00:00:00Z", [], 100)
        filters = body["query"]["bool"]["filter"]
        assert len(filters) == 2
        assert body["size"] == 100

    def test_severity_filter_added(self):
        body = _build_search_body("2024-01-01T00:00:00Z", ["high", "critical"], 50)
        filters = body["query"]["bool"]["filter"]
        assert len(filters) == 3
        terms_filter = filters[2]
        assert terms_filter["terms"]["signal.rule.severity"] == ["high", "critical"]

    def test_max_signals(self):
        body = _build_search_body("2024-01-01T00:00:00Z", [], 25)
        assert body["size"] == 25


class TestExtractSignal:
    def test_full_extraction(self):
        hit = _make_hit("sig-1", "Brute Force", severity="critical", risk_score=99)
        event = _extract_signal(hit)
        assert event["signal_id"] == "sig-1"
        assert event["rule_name"] == "Brute Force"
        assert event["severity"] == "critical"
        assert event["risk_score"] == 99
        assert event["host_name"] == "web01"
        assert event["source_ip"] == "10.0.0.1"

    def test_missing_host(self):
        hit = {"_id": "sig-2", "_source": {"signal": {"rule": {}, "status": "open"}}}
        event = _extract_signal(hit)
        assert event["host_name"] == ""
        assert event["source_ip"] == ""


# ---- Integration-style async tests ----

@pytest.mark.asyncio
async def test_emits_siem_event():
    """New signal hit should produce an event on the queue."""
    queue = asyncio.Queue()
    payload = {"hits": {"hits": [_make_hit("sig-100", "SSH Brute Force")]}}

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.post = MagicMock(return_value=_mock_response(payload))
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

    assert "elastic_siem" in event
    siem = event["elastic_siem"]
    assert siem["signal_id"] == "sig-100"
    assert siem["rule_name"] == "SSH Brute Force"
    assert siem["severity"] == "high"
    assert siem["host_name"] == "web01"


@pytest.mark.asyncio
async def test_severity_filter_applied_in_query():
    """severity_filter should be included in the search body sent to the API."""
    queue = asyncio.Queue()
    payload = {"hits": {"hits": []}}

    args = {**BASE_ARGS, "severity_filter": ["critical"]}
    posted_body = {}

    original_post = None

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()

        def capture_post(url, json=None, ssl=None):
            nonlocal posted_body
            posted_body = json
            return _mock_response(payload)

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

    # Verify the query body included severity filter
    filters = posted_body.get("query", {}).get("bool", {}).get("filter", [])
    severity_terms = [f for f in filters if "terms" in f and "signal.rule.severity" in f.get("terms", {})]
    assert len(severity_terms) == 1
    assert severity_terms[0]["terms"]["signal.rule.severity"] == ["critical"]


@pytest.mark.asyncio
async def test_multiple_signals_emitted():
    """Multiple hits should each produce a separate event."""
    queue = asyncio.Queue()
    payload = {
        "hits": {
            "hits": [
                _make_hit("sig-a", "Alert A"),
                _make_hit("sig-b", "Alert B"),
                _make_hit("sig-c", "Alert C"),
            ]
        }
    }

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.post = MagicMock(return_value=_mock_response(payload))
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = ctx

        task = asyncio.create_task(main(queue, BASE_ARGS))
        events = []
        try:
            for _i in range(3):
                event = await asyncio.wait_for(queue.get(), timeout=5)
                events.append(event)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    ids = {e["elastic_siem"]["signal_id"] for e in events}
    assert ids == {"sig-a", "sig-b", "sig-c"}


@pytest.mark.asyncio
async def test_empty_hits_no_events():
    """Empty hits array should produce no events."""
    queue = asyncio.Queue()
    payload = {"hits": {"hits": []}}

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.post = MagicMock(return_value=_mock_response(payload))
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


@pytest.mark.asyncio
async def test_api_error_does_not_crash():
    """HTTP errors should be caught without crashing the loop."""
    queue = asyncio.Queue()

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        err_resp = AsyncMock()
        err_resp.raise_for_status = MagicMock(side_effect=Exception("503 Service Unavailable"))
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
