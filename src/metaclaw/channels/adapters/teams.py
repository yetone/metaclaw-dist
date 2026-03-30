"""Microsoft Teams channel adapter."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class TeamsChannel(BaseChannel):
    """Microsoft Teams adapter using Bot Framework webhook."""

    @property
    def name(self) -> str:
        return "teams"

    @property
    def connection_type(self) -> str:
        return "webhook"

    async def start(self) -> None:
        self._app_id = os.getenv(
            self._config.get("app_id_env", "TEAMS_APP_ID"), ""
        )
        self._app_password = os.getenv(
            self._config.get("app_password_env", "TEAMS_APP_PASSWORD"), ""
        )

        if not self._app_id or not self._app_password:
            raise ValueError("TEAMS_APP_ID and TEAMS_APP_PASSWORD must be set.")

        self._http = httpx.AsyncClient()
        self._token = ""
        await self._authenticate()
        logger.info("Teams channel ready (webhook mode)")

    async def _authenticate(self) -> None:
        """Get Bot Framework access token."""
        resp = await self._http.post(
            "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._app_id,
                "client_secret": self._app_password,
                "scope": "https://api.botframework.com/.default",
            },
        )
        data = resp.json()
        self._token = data.get("access_token", "")

    async def stop(self) -> None:
        if hasattr(self, "_http"):
            await self._http.aclose()

    async def send(self, message: OutgoingMessage) -> None:
        """Send a reply in Teams."""
        # channel_id stores the service URL + conversation reference
        service_url = message.raw.get("serviceUrl", "") if hasattr(message, "raw") else ""
        conversation_id = message.channel_id

        if not service_url:
            logger.error("No serviceUrl for Teams reply")
            return

        url = f"{service_url}/v3/conversations/{conversation_id}/activities"
        await self._http.post(
            url,
            json={
                "type": "message",
                "text": message.content,
            },
            headers={"Authorization": f"Bearer {self._token}"},
        )

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process incoming Teams Bot Framework activity."""
        activity_type = payload.get("type", "")

        if activity_type == "message":
            incoming = IncomingMessage(
                channel_type="teams",
                channel_id=payload.get("conversation", {}).get("id", ""),
                user_id=payload.get("from", {}).get("id", ""),
                user_name=payload.get("from", {}).get("name", ""),
                content=payload.get("text", ""),
                raw=payload,
            )
            await self._dispatch(incoming)

        return {"status": "ok"}
