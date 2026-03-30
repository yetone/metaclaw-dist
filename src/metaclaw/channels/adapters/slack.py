"""Slack channel adapter using Socket Mode (no public URL required)."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class SlackChannel(BaseChannel):
    """Slack adapter using Socket Mode for easy setup."""

    @property
    def name(self) -> str:
        return "slack"

    @property
    def connection_type(self) -> str:
        return "socket"

    async def start(self) -> None:
        from slack_sdk.web.async_client import AsyncWebClient
        from slack_sdk.socket_mode.aiohttp import SocketModeClient
        from slack_sdk.socket_mode.request import SocketModeRequest
        from slack_sdk.socket_mode.response import SocketModeResponse

        bot_token = os.getenv(
            self._config.get("bot_token_env", "SLACK_BOT_TOKEN"), ""
        )
        app_token = os.getenv(
            self._config.get("app_token_env", "SLACK_APP_TOKEN"), ""
        )

        if not bot_token or not app_token:
            raise ValueError(
                "SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set. "
                "See: https://api.slack.com/apis/connections/socket"
            )

        self._web_client = AsyncWebClient(token=bot_token)
        self._socket_client = SocketModeClient(
            app_token=app_token, web_client=self._web_client
        )

        # Get bot user ID to ignore own messages
        auth = await self._web_client.auth_test()
        self._bot_user_id = auth["user_id"]

        async def handle_event(client: SocketModeClient, req: SocketModeRequest) -> None:
            # Acknowledge immediately
            await client.send_socket_mode_response(
                SocketModeResponse(envelope_id=req.envelope_id)
            )

            if req.type != "events_api":
                return

            event = req.payload.get("event", {})
            event_type = event.get("type", "")

            if event_type not in ("message", "app_mention"):
                return

            # Ignore bot's own messages
            if event.get("user") == self._bot_user_id:
                return
            if event.get("bot_id"):
                return

            text = event.get("text", "").strip()
            if not text:
                return

            message = IncomingMessage(
                channel_type="slack",
                channel_id=event.get("channel", ""),
                user_id=event.get("user", ""),
                thread_id=event.get("thread_ts") or event.get("ts"),
                content=text,
                raw=event,
            )
            await self._dispatch(message)

        self._socket_client.socket_mode_request_listeners.append(handle_event)
        await self._socket_client.connect()
        logger.info("Slack channel connected via Socket Mode")

    async def stop(self) -> None:
        if hasattr(self, "_socket_client"):
            await self._socket_client.disconnect()

    async def send(self, message: OutgoingMessage) -> None:
        from metaclaw.utils.formatting import markdown_to_slack

        text = markdown_to_slack(message.content)

        kwargs: dict[str, Any] = {
            "channel": message.channel_id,
            "text": text,
        }
        if message.thread_id:
            kwargs["thread_ts"] = message.thread_id

        await self._web_client.chat_postMessage(**kwargs)
