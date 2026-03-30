"""Generic webhook channel adapter for custom integrations."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)

# Pending outgoing messages (webhook is pull-based for responses)
_pending_responses: dict[str, list[OutgoingMessage]] = {}


class WebhookChannel(BaseChannel):
    """Generic webhook adapter for custom integrations.

    Receives messages via HTTP POST and returns responses.
    This adapter is used by the FastAPI webhook routes.
    """

    @property
    def name(self) -> str:
        return "webhook"

    @property
    def connection_type(self) -> str:
        return "webhook"

    async def start(self) -> None:
        self._secret = self._config.get("secret", "")
        logger.info("Webhook channel ready (awaiting HTTP requests)")

    async def stop(self) -> None:
        _pending_responses.clear()

    async def send(self, message: OutgoingMessage) -> None:
        # Store response for retrieval by webhook endpoint
        key = message.channel_id
        if key not in _pending_responses:
            _pending_responses[key] = []
        _pending_responses[key].append(message)

    async def handle_incoming(self, payload: dict[str, Any]) -> None:
        """Process an incoming webhook payload.

        Expected format:
        {
            "text": "message content",
            "user_id": "user123",
            "channel_id": "channel456",
            "thread_id": "optional_thread"
        }
        """
        message = IncomingMessage(
            channel_type="webhook",
            channel_id=payload.get("channel_id", "default"),
            user_id=payload.get("user_id", "webhook_user"),
            thread_id=payload.get("thread_id"),
            content=payload.get("text", ""),
            raw=payload,
        )
        await self._dispatch(message)

    def verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify webhook signature using HMAC-SHA256."""
        if not self._secret:
            return True  # No secret configured, skip verification

        expected = hmac.new(
            self._secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    @staticmethod
    def get_pending_responses(channel_id: str) -> list[OutgoingMessage]:
        """Get and clear pending responses for a channel."""
        return _pending_responses.pop(channel_id, [])
