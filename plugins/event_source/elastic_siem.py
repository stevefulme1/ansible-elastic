# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
name: elastic_siem
short_description: Watch for Elastic SIEM detection alerts
description:
  - Polls the Kibana Security Detection Engine for open signals
    (detection alerts) created since the last poll.
  - Each new signal is emitted as an event for EDA rule matching.
options:
  api_url:
    description: Kibana base URL (e.g. C(https://kibana.example.com)).
    type: str
    required: true
  api_key:
    description: Kibana API key for authentication.
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
  severity_filter:
    description:
      - List of severity levels to include.
      - Choices are C(low), C(medium), C(high), C(critical).
      - When empty or omitted, all severities are emitted.
    type: list
    elements: str
    default: []
  max_signals:
    description: Maximum number of signals to retrieve per poll.
    type: int
    default: 100
"""

EXAMPLES = r"""
- name: Watch for high/critical SIEM detections
  stevefulme1.elastic.elastic_siem:
    api_url: "https://kibana.example.com"
    api_key: "{{ elastic_api_key }}"
    interval: 15
    severity_filter:
      - high
      - critical
    max_signals: 50
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp

logger = logging.getLogger("stevefulme1.elastic.elastic_siem")

VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def _build_search_body(last_check: str, severity_filter: list[str], max_signals: int) -> dict:
    """Build the Elasticsearch query body for the signals search."""

    filters = [
        {"range": {"@timestamp": {"gte": last_check}}},
        {"term": {"signal.status": "open"}},
    ]

    if severity_filter:
        filters.append({"terms": {"signal.rule.severity": severity_filter}})

    return {
        "query": {"bool": {"filter": filters}},
        "size": max_signals,
        "sort": [{"@timestamp": {"order": "desc"}}],
    }


def _extract_signal(hit: dict) -> dict:
    """Extract a normalized event dict from a raw Elasticsearch hit."""

    source = hit.get("_source", {})
    signal = source.get("signal", {})
    rule = signal.get("rule", {})
    original = signal.get("original_event", {})

    # Try to pull host/IP from common locations
    host_name = ""
    source_ip = ""
    host = source.get("host", {})
    if isinstance(host, dict):
        host_name = host.get("name", host.get("hostname", ""))
    src = source.get("source", {})
    if isinstance(src, dict):
        source_ip = src.get("ip", "")

    return {
        "signal_id": hit.get("_id", ""),
        "rule_id": rule.get("id", ""),
        "rule_name": rule.get("name", ""),
        "severity": rule.get("severity", ""),
        "risk_score": rule.get("risk_score", 0),
        "description": rule.get("description", ""),
        "host_name": host_name,
        "source_ip": source_ip,
        "timestamp": source.get("@timestamp", ""),
        "signal_status": signal.get("status", "open"),
        "original_event": original,
        "tags": rule.get("tags", []),
    }


async def main(queue: asyncio.Queue, args: dict[str, Any]) -> None:
    """Poll Kibana SIEM Detection Engine and push signal events to *queue*."""

    api_url = args["api_url"].rstrip("/")
    api_key = args["api_key"]
    interval = int(args.get("interval", 30))
    validate_certs = args.get("validate_certs", True)
    max_signals = int(args.get("max_signals", 100))

    severity_filter = [s.lower() for s in args.get("severity_filter", [])]
    for sev in severity_filter:
        if sev not in VALID_SEVERITIES:
            logger.warning("Unknown severity '%s'; valid choices: %s", sev, VALID_SEVERITIES)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"ApiKey {api_key}",
        "kbn-xsrf": "true",
    }

    ssl = None if validate_certs else False
    last_check = datetime.now(timezone.utc).isoformat()

    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            try:
                url = f"{api_url}/api/detection_engine/signals/search"
                body = _build_search_body(last_check, severity_filter, max_signals)

                async with session.post(url, json=body, ssl=ssl) as resp:
                    resp.raise_for_status()
                    payload = await resp.json()

                now = datetime.now(timezone.utc).isoformat()
                hits = payload.get("hits", {}).get("hits", [])

                for hit in hits:
                    event = _extract_signal(hit)
                    await queue.put({"elastic_siem": event})
                    logger.info(
                        "Emitted SIEM event %s: %s (severity=%s)",
                        event["signal_id"],
                        event["rule_name"],
                        event["severity"],
                    )

                last_check = now

            except aiohttp.ClientError as exc:
                logger.error("SIEM detection API request failed: %s", exc)
            except Exception as exc:
                logger.exception("Unexpected error polling SIEM detections: %s", exc)

            await asyncio.sleep(interval)


if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    asyncio.run(
        main(
            MockQueue(),
            {
                "api_url": "https://localhost:5601",
                "api_key": "test-key",
                "interval": 5,
                "validate_certs": False,
                "severity_filter": ["high", "critical"],
            },
        )
    )
