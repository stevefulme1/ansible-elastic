"""Filter Elastic events by severity level."""

DOCUMENTATION = r"""
---
event_filter: severity
short_description: Filter Elastic events by severity
description:
  - Passes through only events matching the configured severity levels.
  - Supports severity values like critical, high, medium, low, informational.
version_added: "1.0.0"
author: Steve Fulmer (@stevefulme1)
options:
  min_severity:
    description: Minimum severity level to pass through.
    type: str
    choices: [informational, low, medium, high, critical]
    default: medium
  severity_key:
    description: Key in the event payload that contains the severity value.
    type: str
    default: severity
"""

EXAMPLES = r"""
- stevefulme1.elastic.severity:
    min_severity: high
"""

SEVERITY_ORDER = {"informational": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def main(event, min_severity="medium", severity_key="severity"):
    """Filter events by severity threshold."""
    if not isinstance(event, dict):
        return event

    payload = event.get("payload", event)
    event_severity = str(payload.get(severity_key, "")).lower()
    min_level = SEVERITY_ORDER.get(min_severity.lower(), 2)
    event_level = SEVERITY_ORDER.get(event_severity, -1)

    if event_level >= min_level:
        return event
    return None
