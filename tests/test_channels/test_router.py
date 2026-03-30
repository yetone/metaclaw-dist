"""Tests for message router."""

from __future__ import annotations

import pytest

from metaclaw.channels.message import IncomingMessage


def test_incoming_message_session_key():
    msg = IncomingMessage(
        channel_type="slack",
        channel_id="C123",
        user_id="U456",
        content="hello",
        thread_id="T789",
    )
    assert msg.session_key == "slack:C123:T789"


def test_session_key_without_thread():
    msg = IncomingMessage(
        channel_type="discord",
        channel_id="C123",
        user_id="U456",
        content="hello",
    )
    # Falls back to user_id when no thread
    assert msg.session_key == "discord:C123:U456"
