"""Abstract base class for channel adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable

from metaclaw.channels.message import IncomingMessage, OutgoingMessage


# Type for message callback
MessageCallback = Callable[[IncomingMessage], Awaitable[None]]


class BaseChannel(ABC):
    """Abstract base for all channel adapters.

    Each adapter translates between platform-specific events
    and the unified IncomingMessage/OutgoingMessage types.
    """

    def __init__(self, config: dict[str, Any]):
        self._config = config
        self._message_callback: MessageCallback | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel type name (e.g., 'slack', 'discord')."""
        ...

    @property
    @abstractmethod
    def connection_type(self) -> str:
        """Connection type: 'socket', 'polling', or 'webhook'."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the channel adapter (connect, authenticate, etc.)."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel adapter gracefully."""
        ...

    @abstractmethod
    async def send(self, message: OutgoingMessage) -> None:
        """Send a message through this channel."""
        ...

    def on_message(self, callback: MessageCallback) -> None:
        """Register a callback for incoming messages."""
        self._message_callback = callback

    async def _dispatch(self, message: IncomingMessage) -> None:
        """Dispatch an incoming message to the registered callback."""
        if self._message_callback:
            await self._message_callback(message)

    @property
    def is_webhook_based(self) -> bool:
        """Whether this channel requires webhook endpoints."""
        return self.connection_type == "webhook"
