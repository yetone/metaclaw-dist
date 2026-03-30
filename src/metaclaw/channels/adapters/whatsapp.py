"""WhatsApp Business Cloud API channel adapter."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class WhatsAppChannel(BaseChannel):
    """WhatsApp adapter using the Cloud API (requires webhook endpoint)."""

    @property
    def name(self) -> str:
        return "whatsapp"

    @property
    def connection_type(self) -> str:
        return "webhook"

    async def start(self) -> None:
        self._token = os.getenv(
            self._config.get("token_env", "WHATSAPP_TOKEN"), ""
        )
        self._phone_number_id = os.getenv(
            self._config.get("phone_number_id_env", "WHATSAPP_PHONE_NUMBER_ID"), ""
        )
        self._verify_token = self._config.get("verify_token", "metaclaw-verify")

        if not self._token or not self._phone_number_id:
            raise ValueError(
                "WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID must be set."
            )

        self._client = httpx.AsyncClient(
            base_url="https://graph.facebook.com/v18.0",
            headers={"Authorization": f"Bearer {self._token}"},
        )
        logger.info("WhatsApp channel ready (webhook mode)")

    async def stop(self) -> None:
        if hasattr(self, "_client"):
            await self._client.aclose()

    async def send(self, message: OutgoingMessage) -> None:
        await self._client.post(
            f"/{self._phone_number_id}/messages",
            json={
                "messaging_product": "whatsapp",
                "to": message.channel_id,
                "type": "text",
                "text": {"body": message.content},
            },
        )

    async def handle_webhook(self, payload: dict[str, Any]) -> None:
        """Process incoming WhatsApp webhook event."""
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        continue

                    incoming = IncomingMessage(
                        channel_type="whatsapp",
                        channel_id=msg.get("from", ""),
                        user_id=msg.get("from", ""),
                        content=msg.get("text", {}).get("body", ""),
                        raw=msg,
                    )
                    await self._dispatch(incoming)

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None:
        """Verify WhatsApp webhook subscription."""
        if mode == "subscribe" and token == self._verify_token:
            return challenge
        return None
