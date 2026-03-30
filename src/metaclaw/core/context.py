"""Conversation context and session management for the agent loop."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to the format expected by LLM APIs."""
        msg: dict[str, Any] = {"role": self.role, "content": self.content}

        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls

        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id

        if self.name and self.role == "tool":
            msg["name"] = self.name

        return msg


class Session:
    """Manages conversation state for a single agent session."""

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.messages: list[Message] = []
        self.metadata: dict[str, Any] = {}
        self.active_skills: set[str] = set()
        self.created_at: float = time.time()

    def add_system_message(self, content: str) -> None:
        """Add or update the system message."""
        # Remove existing system messages
        self.messages = [m for m in self.messages if m.role != "system"]
        # Insert at the beginning
        self.messages.insert(0, Message(role="system", content=content))

    def add_user_message(self, content: str) -> None:
        self.messages.append(Message(role="user", content=content))

    def add_assistant_message(
        self, content: str, tool_calls: list[dict[str, Any]] | None = None
    ) -> None:
        self.messages.append(
            Message(role="assistant", content=content, tool_calls=tool_calls)
        )

    def add_tool_result(
        self, tool_call_id: str, tool_name: str, result: str
    ) -> None:
        self.messages.append(
            Message(
                role="tool",
                content=result,
                tool_call_id=tool_call_id,
                name=tool_name,
            )
        )

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all messages in LLM API format."""
        return [m.to_dict() for m in self.messages]

    def get_token_estimate(self) -> int:
        """Rough token estimate for the session (~4 chars per token)."""
        total = sum(len(m.content or "") for m in self.messages)
        return total // 4

    def compact(self, max_tokens: int, protected_roles: set[str] | None = None) -> None:
        """Compact old messages when approaching token limits.

        Preserves system messages, recent messages, and optionally protected roles.
        Summarizes older conversation turns.
        """
        if self.get_token_estimate() <= max_tokens:
            return

        protected = protected_roles or {"system"}

        # Keep system messages and the last N messages
        keep_recent = 10
        system_msgs = [m for m in self.messages if m.role in protected]
        recent_msgs = self.messages[-keep_recent:]
        middle_msgs = [
            m for m in self.messages
            if m not in system_msgs and m not in recent_msgs
        ]

        if not middle_msgs:
            return

        # Summarize middle messages
        summary_parts = []
        for m in middle_msgs:
            if m.role == "user":
                summary_parts.append(f"[User asked: {m.content[:100]}...]")
            elif m.role == "assistant" and not m.tool_calls:
                summary_parts.append(f"[Assistant responded: {m.content[:100]}...]")
            elif m.role == "tool":
                summary_parts.append(f"[Tool {m.name} was called]")

        summary = Message(
            role="user",
            content=(
                "[Previous conversation summary]\n" + "\n".join(summary_parts)
            ),
        )

        self.messages = system_msgs + [summary] + recent_msgs
