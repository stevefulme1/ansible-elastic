# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
name: elastic_webhook
short_description: Receive Elastic Stack webhook alerts as EDA events
description:
  - Starts an HTTP listener that accepts POST requests from Elastic Stack
    webhook actions (Watcher webhooks, Kibana alerting webhook connectors,
    or any Elastic integration that can fire HTTP POST payloads).
  - Each incoming request body is parsed as JSON and emitted as an EDA
    event under the C(elastic_webhook) key.
  - Supports optional HMAC-SHA256 signature verification for secure
    webhook delivery.
options:
  host:
    description: Address to bind the HTTP listener.
    type: str
    default: "0.0.0.0"
  port:
    description: Port to bind the HTTP listener.
    type: int
    default: 5000
  token:
    description:
      - Optional shared secret for HMAC-SHA256 request verification.
      - When set, every incoming request must include an
        C(X-Webhook-Signature) header containing the hex-encoded
        HMAC-SHA256 digest of the request body using this token as key.
      - Requests with missing or invalid signatures are rejected with
        HTTP 401.
    type: str
    secret: true
  certfile:
    description:
      - Path to a PEM-encoded TLS certificate for HTTPS mode.
      - Both I(certfile) and I(keyfile) must be set to enable TLS.
    type: str
  keyfile:
    description:
      - Path to the PEM-encoded private key for TLS.
    type: str
"""

EXAMPLES = r"""
- name: Receive Elastic webhook alerts
  stevefulme1.elastic.elastic_webhook:
    host: "0.0.0.0"
    port: 5000

- name: Receive with HMAC verification and TLS
  stevefulme1.elastic.elastic_webhook:
    host: "0.0.0.0"
    port: 5443
    token: "{{ webhook_secret }}"
    certfile: /etc/pki/tls/certs/webhook.pem
    keyfile: /etc/pki/tls/private/webhook.key
"""

import asyncio
import hashlib
import hmac
import json
import logging
import ssl as ssl_module
from typing import Any, Dict

from aiohttp import web

logger = logging.getLogger("stevefulme1.elastic.elastic_webhook")


def _verify_signature(body: bytes, signature: str, token: str) -> bool:
    """Verify HMAC-SHA256 signature of the request body."""
    expected = hmac.HMAC(
        token.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def main(queue: asyncio.Queue, args: Dict[str, Any]) -> None:
    """Start an HTTP server to receive Elastic webhook payloads."""

    host = args.get("host", "0.0.0.0")
    port = int(args.get("port", 5000))
    token = args.get("token")  # type: Optional[str]
    certfile = args.get("certfile")
    keyfile = args.get("keyfile")

    async def handle_post(request: web.Request) -> web.Response:
        body = await request.read()

        if token:
            signature = request.headers.get("X-Webhook-Signature", "")
            if not signature or not _verify_signature(body, signature, token):
                logger.warning(
                    "Rejected webhook from %s: invalid or missing signature",
                    request.remote,
                )
                return web.Response(status=401, text="Invalid signature")

        try:
            payload = json.loads(body) if body else {}
        except (json.JSONDecodeError, ValueError):
            logger.warning("Received non-JSON webhook body from %s", request.remote)
            return web.Response(status=400, text="Invalid JSON")

        if not isinstance(payload, dict):
            payload = {"data": payload}

        payload.setdefault("_source_ip", request.remote)

        await queue.put({"elastic_webhook": payload})
        logger.info(
            "Emitted webhook event from %s (%d bytes)",
            request.remote,
            len(body),
        )

        return web.Response(status=200, text="OK")

    async def handle_health(request: web.Request) -> web.Response:
        return web.Response(status=200, text="healthy")

    app = web.Application()
    app.router.add_post("/", handle_post)
    app.router.add_post("/webhook", handle_post)
    app.router.add_get("/health", handle_health)

    ssl_context = None
    if certfile and keyfile:
        ssl_context = ssl_module.SSLContext(ssl_module.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile, keyfile)
        logger.info("TLS enabled with cert=%s", certfile)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
    await site.start()
    logger.info("Elastic webhook listener started on %s:%d", host, port)

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()


if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    asyncio.run(
        main(
            MockQueue(),
            {
                "host": "127.0.0.1",
                "port": 5000,
            },
        )
    )
