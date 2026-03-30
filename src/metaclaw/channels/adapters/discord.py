"""Discord channel adapter using discord.py gateway."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class DiscordChannel(BaseChannel):
    """Discord adapter using discord.py gateway (no public URL required)."""

    @property
    def name(self) -> str:
        return "discord"

    @property
    def connection_type(self) -> str:
        return "socket"

    async def start(self) -> None:
        import discord

        token = os.getenv(
            self._config.get("bot_token_env", "DISCORD_BOT_TOKEN"), ""
        )
        if not token:
            raise ValueError(
                "DISCORD_BOT_TOKEN must be set. "
                "See: https://discord.com/developers/applications"
            )

        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        self._client = discord.Client(intents=intents)
        self._token = token
        self._channel_map: dict[str, Any] = {}  # channel_id -> discord channel

        @self._client.event
        async def on_ready() -> None:
            logger.info(f"Discord connected as {self._client.user}")

        @self._client.event
        async def on_message(msg: discord.Message) -> None:
            # Ignore own messages
            if msg.author == self._client.user:
                return
            # Ignore bot messages
            if msg.author.bot:
                return

            self._channel_map[str(msg.channel.id)] = msg.channel

            thread_id = None
            if hasattr(msg, "thread") and msg.thread:
                thread_id = str(msg.thread.id)

            message = IncomingMessage(
                channel_type="discord",
                channel_id=str(msg.channel.id),
                user_id=str(msg.author.id),
                user_name=str(msg.author),
                thread_id=thread_id,
                content=msg.content,
                raw={"message_id": msg.id},
            )
            await self._dispatch(message)

        # Start in background task
        self._task = asyncio.create_task(self._client.start(self._token))

    async def stop(self) -> None:
        if hasattr(self, "_client"):
            await self._client.close()
        if hasattr(self, "_task"):
            self._task.cancel()

    async def send(self, message: OutgoingMessage) -> None:
        channel = self._channel_map.get(message.channel_id)
        if channel is None:
            channel = await self._client.fetch_channel(int(message.channel_id))
            self._channel_map[message.channel_id] = channel

        # Discord has a 2000 char limit
        content = message.content
        if len(content) > 2000:
            # Split into chunks
            chunks = [content[i : i + 2000] for i in range(0, len(content), 2000)]
            for chunk in chunks:
                await channel.send(chunk)
        else:
            await channel.send(content)
