"""Google Chat channel adapter."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class GoogleChatChannel(BaseChannel):
    """Google Chat adapter using webhook mode."""

    @property
    def name(self) -> str:
        return "google_chat"

    @property
    def connection_type(self) -> str:
        return "webhook"

    async def start(self) -> None:
        self._credentials_file = os.getenv(
            self._config.get("credentials_env", "GOOGLE_CHAT_CREDENTIALS_FILE"), ""
        )

        self._http = httpx.AsyncClient()
        self._token: str = ""

        if self._credentials_file:
            await self._authenticate()

        logger.info("Google Chat channel ready (webhook mode)")

    async def _authenticate(self) -> None:
        """Authenticate using service account credentials."""
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            credentials = service_account.Credentials.from_service_account_file(
                self._credentials_file,
                scopes=["https://www.googleapis.com/auth/chat.bot"],
            )
            credentials.refresh(Request())
            self._token = credentials.token
        except Exception as e:
            logger.error(f"Google Chat authentication failed: {e}")

    async def stop(self) -> None:
        if hasattr(self, "_http"):
            await self._http.aclose()

    async def send(self, message: OutgoingMessage) -> None:
        """Send a message to a Google Chat space."""
        space_name = message.channel_id
        url = f"https://chat.googleapis.com/v1/{space_name}/messages"

        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        await self._http.post(
            url,
            json={"text": message.content},
            headers=headers,
        )

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process incoming Google Chat event."""
        event_type = payload.get("type", "")

        if event_type == "MESSAGE":
            msg = payload.get("message", {})
            sender = msg.get("sender", {})
            space = payload.get("space", {})

            incoming = IncomingMessage(
                channel_type="google_chat",
                channel_id=space.get("name", ""),
                user_id=sender.get("name", ""),
                user_name=sender.get("displayName", ""),
                thread_id=msg.get("thread", {}).get("name"),
                content=msg.get("argumentText", msg.get("text", "")),
                raw=payload,
            )
            await self._dispatch(incoming)

        # Return sync response
        return {"text": "Processing..."}
