"""Twilio SMS/WhatsApp channel adapter."""

from __future__ import annotations

import logging
import os
from typing import Any

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class TwilioChannel(BaseChannel):
    """Twilio adapter for SMS and WhatsApp via Twilio."""

    @property
    def name(self) -> str:
        return "twilio"

    @property
    def connection_type(self) -> str:
        return "webhook"

    async def start(self) -> None:
        self._account_sid = os.getenv(
            self._config.get("account_sid_env", "TWILIO_ACCOUNT_SID"), ""
        )
        self._auth_token = os.getenv(
            self._config.get("auth_token_env", "TWILIO_AUTH_TOKEN"), ""
        )
        self._phone_number = os.getenv(
            self._config.get("phone_number_env", "TWILIO_PHONE_NUMBER"), ""
        )

        if not all([self._account_sid, self._auth_token, self._phone_number]):
            raise ValueError(
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and "
                "TWILIO_PHONE_NUMBER must be set."
            )

        try:
            from twilio.rest import Client

            self._client = Client(self._account_sid, self._auth_token)
        except ImportError:
            import httpx

            self._http = httpx.AsyncClient(
                base_url=f"https://api.twilio.com/2010-04-01/Accounts/{self._account_sid}",
                auth=(self._account_sid, self._auth_token),
            )

        logger.info("Twilio channel ready (webhook mode)")

    async def stop(self) -> None:
        if hasattr(self, "_http"):
            await self._http.aclose()

    async def send(self, message: OutgoingMessage) -> None:
        if hasattr(self, "_client"):
            self._client.messages.create(
                body=message.content,
                from_=self._phone_number,
                to=message.channel_id,
            )
        else:
            await self._http.post(
                "/Messages.json",
                data={
                    "Body": message.content,
                    "From": self._phone_number,
                    "To": message.channel_id,
                },
            )

    async def handle_webhook(self, form_data: dict[str, str]) -> str:
        """Process incoming Twilio webhook (form-encoded)."""
        incoming = IncomingMessage(
            channel_type="twilio",
            channel_id=form_data.get("From", ""),
            user_id=form_data.get("From", ""),
            content=form_data.get("Body", ""),
            raw=form_data,
        )
        await self._dispatch(incoming)

        # Return TwiML response (empty for now, response sent async)
        return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
