"""LINE Messaging API channel adapter."""

from __future__ import annotations

import logging
import os
from typing import Any

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class LineChannel(BaseChannel):
    """LINE adapter using the Messaging API (webhook mode)."""

    @property
    def name(self) -> str:
        return "line"

    @property
    def connection_type(self) -> str:
        return "webhook"

    async def start(self) -> None:
        self._channel_secret = os.getenv(
            self._config.get("channel_secret_env", "LINE_CHANNEL_SECRET"), ""
        )
        self._channel_access_token = os.getenv(
            self._config.get("channel_access_token_env", "LINE_CHANNEL_ACCESS_TOKEN"), ""
        )

        if not self._channel_secret or not self._channel_access_token:
            raise ValueError(
                "LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN must be set."
            )

        try:
            from linebot.v3.messaging import AsyncMessagingApi, AsyncApiClient, Configuration

            configuration = Configuration(access_token=self._channel_access_token)
            self._api_client = AsyncApiClient(configuration)
            self._api = AsyncMessagingApi(self._api_client)
        except ImportError:
            import httpx

            self._http = httpx.AsyncClient(
                base_url="https://api.line.me/v2",
                headers={
                    "Authorization": f"Bearer {self._channel_access_token}",
                    "Content-Type": "application/json",
                },
            )

        logger.info("LINE channel ready (webhook mode)")

    async def stop(self) -> None:
        if hasattr(self, "_api_client"):
            pass  # Cleanup handled by GC
        if hasattr(self, "_http"):
            await self._http.aclose()

    async def send(self, message: OutgoingMessage) -> None:
        if hasattr(self, "_api"):
            from linebot.v3.messaging import (
                ReplyMessageRequest,
                PushMessageRequest,
                TextMessage,
            )

            if message.reply_to:
                await self._api.reply_message(
                    ReplyMessageRequest(
                        reply_token=message.reply_to,
                        messages=[TextMessage(text=message.content)],
                    )
                )
            else:
                await self._api.push_message(
                    PushMessageRequest(
                        to=message.channel_id,
                        messages=[TextMessage(text=message.content)],
                    )
                )
        else:
            await self._http.post(
                "/bot/message/push",
                json={
                    "to": message.channel_id,
                    "messages": [{"type": "text", "text": message.content}],
                },
            )

    async def handle_webhook(self, payload: dict[str, Any]) -> None:
        """Process LINE webhook events."""
        for event in payload.get("events", []):
            if event.get("type") != "message":
                continue
            msg = event.get("message", {})
            if msg.get("type") != "text":
                continue

            source = event.get("source", {})
            incoming = IncomingMessage(
                channel_type="line",
                channel_id=source.get("userId", ""),
                user_id=source.get("userId", ""),
                thread_id=event.get("replyToken"),
                content=msg.get("text", ""),
                raw=event,
            )
            await self._dispatch(incoming)
