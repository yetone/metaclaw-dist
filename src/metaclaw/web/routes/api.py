"""REST API for administration and dashboard."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from metaclaw import __version__

router = APIRouter(tags=["api"])


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Get system status."""
    from metaclaw.config import get_config

    config = get_config()
    enabled_channels = [
        name for name, cfg in config.channels.items() if cfg.enabled
    ]
    return {
        "version": __version__,
        "model": config.llm.model,
        "enabled_channels": enabled_channels,
        "max_iterations": config.agent.max_iterations,
    }


@router.get("/skills")
async def list_skills() -> list[dict[str, str]]:
    """List all discovered skills."""
    from metaclaw.skills.discovery import discover_skills

    skills = discover_skills()
    return [
        {"name": s.name, "description": s.description, "source": s.source}
        for s in skills
    ]


@router.get("/channels")
async def list_channels() -> list[dict[str, Any]]:
    """List all channels and their configuration status."""
    from metaclaw.config import get_config

    config = get_config()
    all_channels = [
        "slack", "discord", "telegram", "wechat", "line",
        "whatsapp", "email", "webhook", "twilio",
        "google_chat", "teams", "zoom",
    ]
    return [
        {
            "name": ch,
            "enabled": config.channels.get(ch, None) is not None
            and config.channels[ch].enabled,
        }
        for ch in all_channels
    ]


@router.get("/sessions")
async def list_sessions() -> list[dict[str, Any]]:
    """List active sessions."""
    from metaclaw.sessions.store import SessionStore

    store = SessionStore()
    return store.list_sessions()


@router.post("/chat")
async def chat(message: dict[str, str]) -> dict[str, str]:
    """Send a message to the agent via HTTP API.

    Body: {"message": "your message here"}
    """
    text = message.get("message", "")
    if not text:
        return {"error": "No message provided"}

    from metaclaw.config import get_config
    from metaclaw.core.agent import Agent
    from metaclaw.core.context import Session

    config = get_config()
    agent = Agent(config)
    session = Session(session_id="api-session")

    response = await agent.run(session, text)
    return {"response": response}
