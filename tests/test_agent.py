"""Tests for agent context and session management."""

from __future__ import annotations

from metaclaw.core.context import Session


def test_session_messages():
    session = Session()
    session.add_system_message("You are a helpful assistant.")
    session.add_user_message("Hello")
    session.add_assistant_message("Hi there!")

    messages = session.get_messages()
    assert len(messages) == 3
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"


def test_session_tool_result():
    session = Session()
    session.add_user_message("Read a file")
    session.add_assistant_message(
        "",
        tool_calls=[{
            "id": "tc1",
            "type": "function",
            "function": {"name": "ReadFile", "arguments": "{}"},
        }],
    )
    session.add_tool_result("tc1", "ReadFile", "file contents here")

    messages = session.get_messages()
    assert len(messages) == 3
    assert messages[2]["role"] == "tool"
    assert messages[2]["tool_call_id"] == "tc1"


def test_session_compact():
    session = Session()
    session.add_system_message("system")

    # Add many messages
    for i in range(50):
        session.add_user_message(f"Message {i}" * 100)
        session.add_assistant_message(f"Response {i}" * 100)

    original_count = len(session.messages)
    session.compact(max_tokens=1000)

    # Should have fewer messages after compaction
    assert len(session.messages) < original_count
    # System message should be preserved
    assert session.messages[0].role == "system"


def test_session_active_skills():
    session = Session()
    session.active_skills.add("test-skill")
    assert "test-skill" in session.active_skills
