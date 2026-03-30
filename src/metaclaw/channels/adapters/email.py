"""Email channel adapter using IMAP for receiving and SMTP for sending."""

from __future__ import annotations

import asyncio
import email as email_lib
import logging
import os
from email.mime.text import MIMEText
from typing import Any

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class EmailChannel(BaseChannel):
    """Email adapter using IMAP polling and SMTP sending."""

    @property
    def name(self) -> str:
        return "email"

    @property
    def connection_type(self) -> str:
        return "polling"

    async def start(self) -> None:
        self._smtp_host = os.getenv("EMAIL_SMTP_HOST", "")
        self._smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self._imap_host = os.getenv("EMAIL_IMAP_HOST", "")
        self._username = os.getenv("EMAIL_USERNAME", "")
        self._password = os.getenv("EMAIL_PASSWORD", "")

        if not all([self._smtp_host, self._imap_host, self._username, self._password]):
            raise ValueError(
                "EMAIL_SMTP_HOST, EMAIL_IMAP_HOST, EMAIL_USERNAME, "
                "and EMAIL_PASSWORD must be set."
            )

        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info(f"Email channel started, polling {self._imap_host}")

    async def stop(self) -> None:
        self._running = False
        if hasattr(self, "_poll_task"):
            self._poll_task.cancel()

    async def _poll_loop(self) -> None:
        """Poll IMAP for new messages."""
        import imaplib

        poll_interval = self._config.get("poll_interval", 30)

        while self._running:
            try:
                imap = imaplib.IMAP4_SSL(self._imap_host)
                imap.login(self._username, self._password)
                imap.select("INBOX")

                # Search for unseen messages
                _, msg_nums = imap.search(None, "UNSEEN")
                for num in msg_nums[0].split():
                    _, data = imap.fetch(num, "(RFC822)")
                    if data[0] is None:
                        continue

                    raw_email = data[0][1]
                    msg = email_lib.message_from_bytes(raw_email)

                    # Extract text content
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(
                                    errors="replace"
                                )
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="replace")

                    sender = msg.get("From", "")
                    subject = msg.get("Subject", "")
                    message_id = msg.get("Message-ID", "")

                    incoming = IncomingMessage(
                        channel_type="email",
                        channel_id=sender,
                        user_id=sender,
                        user_name=sender,
                        thread_id=message_id,
                        content=f"Subject: {subject}\n\n{body}",
                        raw={"message_id": message_id, "subject": subject},
                    )
                    await self._dispatch(incoming)

                    # Mark as seen
                    imap.store(num, "+FLAGS", "\\Seen")

                imap.logout()

            except Exception as e:
                logger.error(f"Email poll error: {e}")

            await asyncio.sleep(poll_interval)

    async def send(self, message: OutgoingMessage) -> None:
        """Send an email reply."""
        import aiosmtplib

        msg = MIMEText(message.content)
        msg["From"] = self._username
        msg["To"] = message.channel_id
        msg["Subject"] = f"Re: MetaClaw"

        if message.reply_to:
            msg["In-Reply-To"] = message.reply_to
            msg["References"] = message.reply_to

        await aiosmtplib.send(
            msg,
            hostname=self._smtp_host,
            port=self._smtp_port,
            username=self._username,
            password=self._password,
            use_tls=True,
        )
