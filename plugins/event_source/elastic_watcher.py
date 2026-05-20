# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
name: elastic_watcher
short_description: Watch for Elasticsearch Watcher execution history
description:
  - Polls the Elasticsearch Watcher execution history index
    (C(.watcher-history-*)) for watch executions that occurred since the
    last check.
  - Hits the Elasticsearch API directly (not Kibana).
options:
  api_url:
    description: Elasticsearch base URL (e.g. C(https://es.example.com:9200)).
    type: str
    required: true
  api_key:
    description: Elasticsearch API key for authentication.
    type: str
    required: true
    secret: true
  interval:
    description: Polling interval in seconds.
    type: int
    default: 30
  validate_certs:
    description: Whether to validate SSL certificates.
    type: bool
    default: true
  status_filter:
    description:
      - List of execution statuses to include.
      - Choices are C(executed), C(throttled), C(failed).
      - When empty or omitted, all statuses are emitted.
    type: list
    elements: str
    default: []
  watch_id_filter:
    description:
      - List of watch IDs to monitor.
      - When empty or omitted, all watches are monitored.
    type: list
    elements: str
    default: []
"""

EXAMPLES = r"""
- name: Watch for failed watcher executions
  stevefulme1.elastic.elastic_watcher:
    api_url: "https://elasticsearch.example.com:9200"
    api_key: "{{ elastic_api_key }}"
    interval: 60
    status_filter:
      - executed
      - failed
    watch_id_filter:
      - disk_space_alert
      - memory_alert
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp

logger = logging.getLogger("stevefulme1.elastic.elastic_watcher")

VALID_STATUSES = {"executed", "throttled", "failed"}


def _build_search_body(
    last_check: str,
    status_filter: list[str],
    watch_id_filter: list[str],
) -> dict:
    """Build the Elasticsearch query body for watcher history search."""

    filters: list[dict] = [
        {"range": {"result.execution_time": {"gte": last_check}}},
    ]

    if status_filter:
        filters.append({"terms": {"state": status_filter}})

    if watch_id_filter:
        filters.append({"terms": {"watch_id": watch_id_filter}})

    return {
        "query": {"bool": {"filter": filters}},
        "size": 100,
        "sort": [{"result.execution_time": {"order": "desc"}}],
    }


def _extract_execution(hit: dict) -> dict:
    """Extract a normalized event dict from a watcher history hit."""

    source = hit.get("_source", {})
    result = source.get("result", {})
    trigger_event = source.get("trigger_event", {})

    return {
        "watch_id": source.get("watch_id", ""),
        "execution_id": hit.get("_id", ""),
        "execution_time": result.get("execution_time", ""),
        "execution_duration": result.get("execution_duration", 0),
        "trigger_event": trigger_event,
        "status": source.get("state", ""),
        "actions_results": result.get("actions", []),
        "input_result": result.get("input", {}),
        "condition_result": result.get("condition", {}),
        "messages": source.get("messages", []),
    }


async def _check_watcher_running(session: aiohttp.ClientSession, api_url: str, ssl) -> bool:
    """Verify the Watcher service is running via /_watcher/stats."""
    try:
        async with session.get(f"{api_url}/_watcher/stats", ssl=ssl) as resp:
            if resp.status != 200:
                logger.warning("Watcher stats returned status %d", resp.status)
                return False
            data = await resp.json()
            stats = data.get("stats", [])
            if stats:
                state = stats[0].get("watcher_state", "stopped")
                if state != "started":
                    logger.warning("Watcher is not running (state=%s)", state)
                    return False
            return True
    except Exception as exc:
        logger.error("Failed to check watcher stats: %s", exc)
        return False


async def main(queue: asyncio.Queue, args: dict[str, Any]) -> None:
    """Poll Elasticsearch Watcher history and push execution events to *queue*."""

    api_url = args["api_url"].rstrip("/")
    api_key = args["api_key"]
    interval = int(args.get("interval", 30))
    validate_certs = args.get("validate_certs", True)

    status_filter = [s.lower() for s in args.get("status_filter", [])]
    for status in status_filter:
        if status not in VALID_STATUSES:
            logger.warning("Unknown status '%s'; valid choices: %s", status, VALID_STATUSES)

    watch_id_filter = args.get("watch_id_filter", [])

    # Elasticsearch direct -- no kbn-xsrf header needed
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"ApiKey {api_key}",
    }

    ssl = None if validate_certs else False
    last_check = datetime.now(timezone.utc).isoformat()

    async with aiohttp.ClientSession(headers=headers) as session:
        # Initial watcher health check
        running = await _check_watcher_running(session, api_url, ssl)
        if not running:
            logger.warning("Watcher may not be running; will continue polling anyway")

        while True:
            try:
                url = f"{api_url}/.watcher-history-*/_search"
                body = _build_search_body(last_check, status_filter, watch_id_filter)

                async with session.post(url, json=body, ssl=ssl) as resp:
                    resp.raise_for_status()
                    payload = await resp.json()

                now = datetime.now(timezone.utc).isoformat()
                hits = payload.get("hits", {}).get("hits", [])

                for hit in hits:
                    event = _extract_execution(hit)
                    await queue.put({"elastic_watcher": event})
                    logger.info(
                        "Emitted watcher event %s: watch=%s status=%s",
                        event["execution_id"],
                        event["watch_id"],
                        event["status"],
                    )

                last_check = now

            except aiohttp.ClientError as exc:
                logger.error("Watcher history search failed: %s", exc)
            except Exception as exc:
                logger.exception("Unexpected error polling watcher history: %s", exc)

            await asyncio.sleep(interval)


if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    asyncio.run(
        main(
            MockQueue(),
            {
                "api_url": "https://localhost:9200",
                "api_key": "test-key",
                "interval": 5,
                "validate_certs": False,
            },
        )
    )
