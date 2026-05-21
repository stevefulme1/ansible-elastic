# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
name: elastic_alert
short_description: Watch for fired Kibana alerting rules
description:
  - Polls the Kibana Alerting API for rules whose execution status is
    C(active) or C(error) since the last check.
  - Each newly-fired rule is emitted as an event that EDA can match with
    conditions and route to remediation playbooks.
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
      - List of severity tags to include (e.g. C(critical), C(high)).
      - Only rules whose tags contain at least one of these values are emitted.
      - When empty or omitted, all rules are emitted.
    type: list
    elements: str
    default: []
  rule_type_filter:
    description:
      - List of Kibana rule type IDs to include
        (e.g. C(.es-query), C(metrics.alert.threshold)).
      - When empty or omitted, all rule types are emitted.
    type: list
    elements: str
    default: []
"""

EXAMPLES = r"""
- name: Watch for critical Kibana alerts
  stevefulme1.elastic.elastic_alert:
    api_url: "https://kibana.example.com"
    api_key: "{{ elastic_api_key }}"
    interval: 30
    severity_filter:
      - critical
      - high
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp

logger = logging.getLogger("stevefulme1.elastic.elastic_alert")


async def main(queue: asyncio.Queue, args: dict[str, Any]) -> None:
    """Poll Kibana Alerting API and push fired-rule events to *queue*."""

    api_url = args["api_url"].rstrip("/")
    api_key = args["api_key"]
    interval = int(args.get("interval", 30))
    validate_certs = args.get("validate_certs", True)
    severity_filter = [s.lower() for s in args.get("severity_filter", [])]
    rule_type_filter = args.get("rule_type_filter", [])

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
                params = {
                    "sort_field": "executionStatus.lastExecutionDate",
                    "sort_order": "desc",
                    "per_page": "100",
                }

                url = f"{api_url}/api/alerting/rules/_find"
                async with session.get(url, params=params, ssl=ssl) as resp:
                    resp.raise_for_status()
                    payload = await resp.json()

                rules = payload.get("data", [])
                now = datetime.now(timezone.utc).isoformat()

                for rule in rules:
                    exec_status = rule.get("executionStatus", {})
                    status = exec_status.get("status", "")
                    last_exec = exec_status.get("lastExecutionDate", "")

                    # Only emit if execution happened after our last check
                    if last_exec <= last_check:
                        continue

                    # Only emit active or error statuses
                    if status not in ("active", "error"):
                        continue

                    # Apply rule_type_filter
                    if rule_type_filter and rule.get("rule_type_id") not in rule_type_filter:
                        continue

                    # Apply severity_filter against rule tags
                    if severity_filter:
                        rule_tags = [t.lower() for t in rule.get("tags", [])]
                        if not any(sev in rule_tags for sev in severity_filter):
                            continue

                    event = {
                        "rule_id": rule.get("id", ""),
                        "rule_name": rule.get("name", ""),
                        "rule_type_id": rule.get("rule_type_id", ""),
                        "status": status,
                        "last_execution_date": last_exec,
                        "last_duration": exec_status.get("lastDuration", 0),
                        "error_message": exec_status.get("error", {}).get("message", ""),
                        "tags": rule.get("tags", []),
                        "enabled": rule.get("enabled", False),
                        "consumer": rule.get("consumer", ""),
                    }

                    await queue.put({"elastic_alert": event})
                    logger.info("Emitted alert event for rule %s (%s)", event["rule_id"], event["rule_name"])

                last_check = now

            except aiohttp.ClientError as exc:
                logger.error("Kibana alerting API request failed: %s", exc)
            except Exception as exc:
                logger.exception("Unexpected error polling Kibana alerts: %s", exc)

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
            },
        )
    )
