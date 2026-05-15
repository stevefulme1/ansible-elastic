"""Receive Elastic alert events via webhook."""

import asyncio
import logging
from typing import Any
from aiohttp import web

logger = logging.getLogger(__name__)


async def main(queue: asyncio.Queue, args: dict[str, Any]) -> None:
    """Receive Elastic webhook events and forward to the EDA rulebook."""
    host = str(args.get("host", "0.0.0.0"))
    port = int(args.get("port", 5000))
    token = args.get("token", "")

    app = web.Application()

    async def _handle(request: web.Request) -> web.Response:
        try:
            payload = await request.json()
            event = {dict([("elastic", payload)])}
            await queue.put(event)
            return web.Response(status=200, text="OK")
        except Exception as exc:
            logger.exception("Error processing webhook: %s", exc)
            return web.Response(status=500, text="Error")

    app.router.add_post("/", _handle)
    app.router.add_post("/webhook", _handle)
    app.router.add_get("/health", lambda r: web.Response(text="OK"))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("Elastic webhook listener on %s:%d", host, port)

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()
