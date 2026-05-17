"""Normalize Elasticsearch/Elastic alert payloads into a flat structure."""

DOCUMENTATION = r"""
---
event_filter: normalize
short_description: Flatten Elastic alert payloads
description:
  - Normalizes nested Elasticsearch Watcher or Kibana alert payloads
    into a flat key-value structure for EDA rule matching.
  - Extracts fields from watcher metadata, alert context, and hits.
version_added: "1.0.0"
author: Steve Fulmer (@stevefulme1)
options:
  include_raw:
    description: Whether to include the original raw payload under a C(raw) key.
    type: bool
    default: false
  prefix:
    description: Prefix to prepend to extracted keys.
    type: str
    default: ""
"""

EXAMPLES = r"""
- stevefulme1.elastic.normalize:
    include_raw: false
"""


def main(event, include_raw=False, prefix=""):
    """Flatten an Elastic alert payload."""
    if not isinstance(event, dict):
        return event

    payload = event.get("payload", event)
    result = {}

    for key in ("watch_id", "execution_time", "trigger", "state",
                "alert_id", "rule_id", "rule_name", "severity",
                "message", "status", "index", "timestamp"):
        if key in payload:
            result[prefix + key] = payload[key]

    # Flatten context/metadata
    ctx = payload.get("ctx", payload.get("context", {}))
    if isinstance(ctx, dict):
        for k, v in ctx.items():
            if not isinstance(v, (dict, list)):
                result[prefix + "ctx_" + k] = v

    # Extract hit count
    hits = payload.get("hits", {})
    if isinstance(hits, dict):
        result[prefix + "hit_count"] = hits.get("total", {}).get("value", 0) if isinstance(hits.get("total"), dict) else hits.get("total", 0)

    if include_raw:
        result["raw"] = event

    for key in ("meta", "source"):
        if key in event:
            result[key] = event[key]

    return result
