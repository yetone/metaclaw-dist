"""Zoom Chat channel adapter."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class ZoomChannel(BaseChannel):
    """Zoom Chat adapter using Zoom API and webhooks."""

    @property
    def name(self) -> str:
        return "zoom"

    @property
    def connection_type(self) -> str:
        return "webhook"

    async def start(self) -> None:
        self._client_id = os.getenv(
            self._config.get("client_id_env", "ZOOM_CLIENT_ID"), ""
        )
        self._client_secret = os.getenv(
            self._config.get("client_secret_env", "ZOOM_CLIENT_SECRET"), ""
        )
        self._bot_jid = self._config.get("bot_jid", "")

        if not self._client_id or not self._client_secret:
            raise ValueError("ZOOM_CLIENT_ID and ZOOM_CLIENT_SECRET must be set.")

        self._http = httpx.AsyncClient()
        self._token = ""
        await self._authenticate()
        logger.info("Zoom channel ready (webhook mode)")

    async def _authenticate(self) -> None:
        """Get Zoom API access token using client credentials."""
        resp = await self._http.post(
            "https://zoom.us/oauth/token",
            params={"grant_type": "client_credentials"},
            auth=(self._client_id, self._client_secret),
        )
        data = resp.json()
        self._token = data.get("access_token", "")

    async def stop(self) -> None:
        if hasattr(self, "_http"):
            await self._http.aclose()

    async def send(self, message: OutgoingMessage) -> None:
        """Send a chat message via Zoom."""
        await self._http.post(
            "https://api.zoom.us/v2/im/chat/messages",
            json={
                "robot_jid": self._bot_jid,
                "to_jid": message.channel_id,
                "account_id": "",
                "content": {"body": [{"type": "message", "text": message.content}]},
            },
            headers={"Authorization": f"Bearer {self._token}"},
        )

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process incoming Zoom chat webhook event."""
        event = payload.get("event", "")

        if event == "bot_notification":
            data = payload.get("payload", {})
            incoming = IncomingMessage(
                channel_type="zoom",
                channel_id=data.get("toJid", ""),
                user_id=data.get("userId", ""),
                user_name=data.get("userName", ""),
                content=data.get("cmd", ""),
                raw=payload,
            )
            await self._dispatch(incoming)

        # Zoom webhook verification
        if event == "endpoint.url_validation":
            import hashlib
            import hmac

            token = payload.get("payload", {}).get("plainToken", "")
            encrypted = hmac.new(
                self._client_secret.encode(),
                token.encode(),
                hashlib.sha256,
            ).hexdigest()
            return {
                "plainToken": token,
                "encryptedToken": encrypted,
            }

        return {"status": "ok"}
