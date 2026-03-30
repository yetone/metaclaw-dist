"""Message formatting utilities for cross-channel content translation."""

from __future__ import annotations

import re


def markdown_to_slack(text: str) -> str:
    """Convert standard markdown to Slack's mrkdwn format.

    Key differences:
    - Bold: **text** -> *text*
    - Italic: *text* -> _text_
    - Code blocks stay the same (```)
    - Links: [text](url) -> <url|text>
    """
    # Links: [text](url) -> <url|text>
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", text)

    # Bold: **text** -> *text*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

    # Italic: _text_ stays the same, *text* -> _text_
    # Be careful not to double-convert
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"_\1_", text)

    return text


def markdown_to_telegram(text: str) -> str:
    """Convert standard markdown to Telegram MarkdownV2 format.

    Escapes special characters required by MarkdownV2.
    """
    # Characters that need escaping in MarkdownV2
    escape_chars = r"_[]()~`>#+-=|{}.!"

    # Don't escape inside code blocks
    parts = text.split("```")
    for i in range(0, len(parts), 2):  # Even indices are outside code blocks
        if i < len(parts):
            # Escape special characters (but not markdown formatting)
            for char in escape_chars:
                parts[i] = parts[i].replace(char, f"\\{char}")

    return "```".join(parts)


def markdown_to_plain(text: str) -> str:
    """Strip markdown formatting to plain text."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).strip("`"), text)

    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Remove bold/italic
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)

    # Remove links, keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Remove headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    return text


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length, adding suffix if truncated."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix
