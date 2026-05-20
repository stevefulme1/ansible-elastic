# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for stevefulme1.elastic.elastic_alert EDA event source."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ansible_collections.stevefulme1.elastic.plugins.event_source.elastic_alert import main


BASE_ARGS = {
    "api_url": "https://kibana.example.com",
    "api_key": "test-api-key",
    "interval": 1,
    "validate_certs": False,
}

FUTURE_ISO = "2099-01-01T00:00:00+00:00"


def _make_rule(rule_id, name, status, last_exec, tags=None, rule_type_id=".es-query"):
    """Build a minimal Kibana alerting rule dict."""
    return {
        "id": rule_id,
        "name": name,
        "rule_type_id": rule_type_id,
        "tags": tags or [],
        "enabled": True,
        "consumer": "alerts",
        "executionStatus": {
            "status": status,
            "lastExecutionDate": last_exec,
            "lastDuration": 42,
            "error": {"message": "some error"} if status == "error" else {},
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


@pytest.mark.asyncio
async def test_emits_active_alert():
    """Active rule with future execution date should emit an event."""
    queue = asyncio.Queue()
    payload = {
        "data": [
            _make_rule("r1", "CPU Alert", "active", FUTURE_ISO, tags=["critical"]),
        ]
    }

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(payload))
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

    assert "elastic_alert" in event
    alert = event["elastic_alert"]
    assert alert["rule_id"] == "r1"
    assert alert["rule_name"] == "CPU Alert"
    assert alert["status"] == "active"
    assert alert["last_duration"] == 42


@pytest.mark.asyncio
async def test_emits_error_alert_with_message():
    """Error rule should include the error message in the event payload."""
    queue = asyncio.Queue()
    payload = {
        "data": [_make_rule("r2", "Disk Alert", "error", FUTURE_ISO)]
    }

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(payload))
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

    assert event["elastic_alert"]["status"] == "error"
    assert event["elastic_alert"]["error_message"] == "some error"


@pytest.mark.asyncio
async def test_severity_filter_excludes():
    """Rules that don't match the severity_filter should be skipped."""
    queue = asyncio.Queue()
    payload = {
        "data": [
            _make_rule("r3", "Low Alert", "active", FUTURE_ISO, tags=["low"]),
        ]
    }

    args = {**BASE_ARGS, "severity_filter": ["critical"]}

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(payload))
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

    assert queue.empty(), "Low-severity rule should have been filtered out"


@pytest.mark.asyncio
async def test_rule_type_filter():
    """Only rules matching rule_type_filter should be emitted."""
    queue = asyncio.Queue()
    payload = {
        "data": [
            _make_rule("r4", "Query Alert", "active", FUTURE_ISO, rule_type_id=".es-query"),
            _make_rule("r5", "Metric Alert", "active", FUTURE_ISO, rule_type_id="metrics.alert.threshold"),
        ]
    }

    args = {**BASE_ARGS, "rule_type_filter": [".es-query"]}

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(payload))
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = ctx

        task = asyncio.create_task(main(queue, args))
        try:
            event = await asyncio.wait_for(queue.get(), timeout=5)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    assert event["elastic_alert"]["rule_id"] == "r4"
    assert queue.empty(), "Metric alert should have been filtered out"


@pytest.mark.asyncio
async def test_skips_old_rules():
    """Rules with execution date before last_check should not be emitted."""
    queue = asyncio.Queue()
    payload = {
        "data": [
            _make_rule("r6", "Old Alert", "active", "2000-01-01T00:00:00+00:00"),
        ]
    }

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(payload))
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

    assert queue.empty(), "Old rule execution should not produce events"


@pytest.mark.asyncio
async def test_api_error_does_not_crash():
    """An HTTP error should be caught without crashing the event loop."""
    queue = asyncio.Queue()

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        err_resp = AsyncMock()
        err_resp.raise_for_status = MagicMock(side_effect=Exception("Connection refused"))
        err_ctx = AsyncMock()
        err_ctx.__aenter__ = AsyncMock(return_value=err_resp)
        err_ctx.__aexit__ = AsyncMock(return_value=False)
        session.get = MagicMock(return_value=err_ctx)

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

    # No exception means the loop survived the error
    assert queue.empty()
