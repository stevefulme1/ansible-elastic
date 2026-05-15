"""Poll Elastic API for events/alerts."""

import asyncio
import logging
from typing import Any

IMPORT_ERRORS = []
try:
    import requests
except ImportError as ie:
    IMPORT_ERRORS.append(ie)

logger = logging.getLogger(__name__)


async def main(queue: asyncio.Queue, args: dict[str, Any]) -> None:
    """Poll Elastic for alerts and forward to the EDA rulebook."""
    for exc in IMPORT_ERRORS:
        raise exc

    host = args["host"]
    interval = int(args.get("interval", 60))
    api_key = args.get("api_key", "")

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    seen = set()

    while True:
        try:
            resp = requests.get(
                f"https://{host}/api/v1/kafka",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            for item in resp.json().get("data", resp.json() if isinstance(resp.json(), list) else []):
                item_id = str(item.get("id", ""))
                if item_id and item_id not in seen:
                    seen.add(item_id)
                    await queue.put({"elastic": item})
        except Exception as exc:
            logger.error("Error polling Elastic: %s", exc)

        await asyncio.sleep(interval)
