"""Unified message types for cross-channel communication."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Attachment:
    """A file or media attachment."""

    filename: str
    content_type: str  # MIME type
    url: str = ""
    data: bytes = b""
    size: int = 0


@dataclass
class IncomingMessage:
    """A message received from any channel."""

    channel_type: str  # "slack", "discord", "telegram", etc.
    channel_id: str  # Channel/room/group identifier
    user_id: str  # Sender identifier
    content: str  # Text content
    thread_id: str | None = None  # Thread/reply chain identifier
    user_name: str = ""
    attachments: list[Attachment] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def session_key(self) -> str:
        """Generate a unique session key for this message context."""
        thread = self.thread_id or self.user_id
        return f"{self.channel_type}:{self.channel_id}:{thread}"


@dataclass
class OutgoingMessage:
    """A message to send to a channel."""

    content: str
    channel_id: str
    thread_id: str | None = None
    attachments: list[Attachment] = field(default_factory=list)
    format: str = "markdown"  # "text", "markdown", "html"
    reply_to: str | None = None  # Message ID to reply to
