"""Webhook endpoints for channel adapters that require HTTP callbacks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["webhooks"])

# Reference to channel manager (set by server startup)
_channel_manager = None


def set_channel_manager(manager: Any) -> None:
    """Set the channel manager reference for webhook routing."""
    global _channel_manager
    _channel_manager = manager


def _get_adapter(name: str) -> Any:
    """Get a channel adapter by name."""
    if _channel_manager is None:
        return None
    return _channel_manager._channels.get(name)


# -- Generic Webhook --


@router.post("/incoming")
async def webhook_incoming(request: Request) -> dict:
    """Generic webhook endpoint."""
    adapter = _get_adapter("webhook")
    if adapter is None:
        return {"error": "Webhook channel not enabled"}

    payload = await request.json()

    # Verify signature if provided
    signature = request.headers.get("X-Signature", "")
    if signature:
        body = await request.body()
        if not adapter.verify_signature(body, signature):
            return {"error": "Invalid signature"}

    await adapter.handle_incoming(payload)
    return {"status": "ok"}


# -- WhatsApp --


@router.get("/whatsapp")
async def whatsapp_verify(
    hub_mode: str = "",
    hub_verify_token: str = "",
    hub_challenge: str = "",
) -> Response:
    """WhatsApp webhook verification."""
    adapter = _get_adapter("whatsapp")
    if adapter is None:
        return Response(status_code=404)

    # Map query params (FastAPI auto-converts hub.mode -> hub_mode)
    challenge = adapter.verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    if challenge:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> dict:
    """WhatsApp incoming message webhook."""
    adapter = _get_adapter("whatsapp")
    if adapter is None:
        return {"error": "WhatsApp channel not enabled"}

    payload = await request.json()
    await adapter.handle_webhook(payload)
    return {"status": "ok"}


# -- WeChat --


@router.get("/wechat")
async def wechat_verify(
    signature: str = "",
    timestamp: str = "",
    nonce: str = "",
    echostr: str = "",
) -> Response:
    """WeChat server verification."""
    adapter = _get_adapter("wechat")
    if adapter is None:
        return Response(status_code=404)

    if adapter.verify_signature(signature, timestamp, nonce):
        return Response(content=echostr, media_type="text/plain")
    return Response(status_code=403)


@router.post("/wechat")
async def wechat_webhook(request: Request) -> Response:
    """WeChat incoming message webhook (XML)."""
    adapter = _get_adapter("wechat")
    if adapter is None:
        return Response(status_code=404)

    body = await request.body()
    result = await adapter.handle_webhook(body.decode("utf-8"))
    return Response(content=result, media_type="application/xml")


# -- LINE --


@router.post("/line")
async def line_webhook(request: Request) -> dict:
    """LINE incoming message webhook."""
    adapter = _get_adapter("line")
    if adapter is None:
        return {"error": "LINE channel not enabled"}

    payload = await request.json()
    await adapter.handle_webhook(payload)
    return {"status": "ok"}


# -- Twilio --


@router.post("/twilio")
async def twilio_webhook(request: Request) -> Response:
    """Twilio SMS/WhatsApp webhook."""
    adapter = _get_adapter("twilio")
    if adapter is None:
        return Response(status_code=404)

    form = await request.form()
    result = await adapter.handle_webhook(dict(form))
    return Response(content=result, media_type="application/xml")


# -- Google Chat --


@router.post("/google-chat")
async def google_chat_webhook(request: Request) -> dict:
    """Google Chat incoming event webhook."""
    adapter = _get_adapter("google_chat")
    if adapter is None:
        return {"error": "Google Chat channel not enabled"}

    payload = await request.json()
    return await adapter.handle_webhook(payload)


# -- Microsoft Teams --


@router.post("/teams")
async def teams_webhook(request: Request) -> dict:
    """Microsoft Teams Bot Framework webhook."""
    adapter = _get_adapter("teams")
    if adapter is None:
        return {"error": "Teams channel not enabled"}

    payload = await request.json()
    return await adapter.handle_webhook(payload)


# -- Zoom --


@router.post("/zoom")
async def zoom_webhook(request: Request) -> dict:
    """Zoom Chat webhook."""
    adapter = _get_adapter("zoom")
    if adapter is None:
        return {"error": "Zoom channel not enabled"}

    payload = await request.json()
    return await adapter.handle_webhook(payload)
