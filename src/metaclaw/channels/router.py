"""Message router - connects channels to agent sessions."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage
from metaclaw.config import MetaClawConfig
from metaclaw.core.agent import Agent
from metaclaw.core.context import Session

logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes incoming messages from channels to agent sessions.

    Maintains a session per unique (channel_type, channel_id, thread/user).
    """

    def __init__(self, agent: Agent):
        self._agent = agent
        self._sessions: dict[str, Session] = {}
        self._channels: dict[str, BaseChannel] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def register_channel(self, channel: BaseChannel) -> None:
        """Register a channel and set up message routing."""
        self._channels[channel.name] = channel
        channel.on_message(self._handle_message)

    async def _handle_message(self, message: IncomingMessage) -> None:
        """Handle an incoming message from any channel."""
        session_key = message.session_key

        # Ensure sequential processing per session
        if session_key not in self._locks:
            self._locks[session_key] = asyncio.Lock()

        async with self._locks[session_key]:
            # Get or create session
            session = self._sessions.get(session_key)
            if session is None:
                session = Session(session_id=session_key)
                self._sessions[session_key] = session

            # Run agent
            try:
                response_text = await self._agent.run(session, message.content)
            except Exception as e:
                logger.error(f"Agent error for session {session_key}: {e}")
                response_text = f"Sorry, an error occurred: {e}"

            # Send response back through the channel
            channel = self._channels.get(message.channel_type)
            if channel:
                response = OutgoingMessage(
                    content=response_text,
                    channel_id=message.channel_id,
                    thread_id=message.thread_id,
                )
                try:
                    await channel.send(response)
                except Exception as e:
                    logger.error(
                        f"Failed to send response to {message.channel_type}: {e}"
                    )

    def get_session(self, session_key: str) -> Session | None:
        """Get an existing session by key."""
        return self._sessions.get(session_key)

    def clear_session(self, session_key: str) -> None:
        """Clear a session."""
        self._sessions.pop(session_key, None)
        self._locks.pop(session_key, None)
