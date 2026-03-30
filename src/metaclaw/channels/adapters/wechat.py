"""WeChat Official Account / Mini Program channel adapter."""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class WeChatChannel(BaseChannel):
    """WeChat adapter using the Official Account API."""

    @property
    def name(self) -> str:
        return "wechat"

    @property
    def connection_type(self) -> str:
        return "webhook"

    async def start(self) -> None:
        self._app_id = os.getenv(
            self._config.get("app_id_env", "WECHAT_APP_ID"), ""
        )
        self._app_secret = os.getenv(
            self._config.get("app_secret_env", "WECHAT_APP_SECRET"), ""
        )
        self._token = os.getenv(
            self._config.get("token_env", "WECHAT_TOKEN"), ""
        )

        if not all([self._app_id, self._app_secret, self._token]):
            raise ValueError(
                "WECHAT_APP_ID, WECHAT_APP_SECRET, and WECHAT_TOKEN must be set."
            )

        try:
            from wechatpy import WeChatClient

            self._client = WeChatClient(self._app_id, self._app_secret)
        except ImportError:
            import httpx

            self._http_client = httpx.AsyncClient()
            self._access_token = ""
            await self._refresh_token()

        logger.info("WeChat channel ready (webhook mode)")

    async def _refresh_token(self) -> None:
        """Refresh WeChat access token."""
        if hasattr(self, "_http_client"):
            resp = await self._http_client.get(
                "https://api.weixin.qq.com/cgi-bin/token",
                params={
                    "grant_type": "client_credential",
                    "appid": self._app_id,
                    "secret": self._app_secret,
                },
            )
            data = resp.json()
            self._access_token = data.get("access_token", "")

    async def stop(self) -> None:
        if hasattr(self, "_http_client"):
            await self._http_client.aclose()

    async def send(self, message: OutgoingMessage) -> None:
        """Send a text message to a WeChat user."""
        if hasattr(self, "_client"):
            self._client.message.send_text(message.channel_id, message.content)
        elif hasattr(self, "_http_client"):
            await self._http_client.post(
                f"https://api.weixin.qq.com/cgi-bin/message/custom/send"
                f"?access_token={self._access_token}",
                json={
                    "touser": message.channel_id,
                    "msgtype": "text",
                    "text": {"content": message.content},
                },
            )

    async def handle_webhook(self, xml_data: str) -> str:
        """Process incoming WeChat message (XML format)."""
        try:
            from wechatpy import parse_message

            msg = parse_message(xml_data)
        except ImportError:
            # Parse XML manually
            import xml.etree.ElementTree as ET

            root = ET.fromstring(xml_data)
            msg_type = root.findtext("MsgType", "")
            if msg_type != "text":
                return "success"

            incoming = IncomingMessage(
                channel_type="wechat",
                channel_id=root.findtext("FromUserName", ""),
                user_id=root.findtext("FromUserName", ""),
                content=root.findtext("Content", ""),
                raw={"xml": xml_data},
            )
            await self._dispatch(incoming)
            return "success"

        if msg.type != "text":
            return "success"

        incoming = IncomingMessage(
            channel_type="wechat",
            channel_id=msg.source,
            user_id=msg.source,
            content=msg.content,
            raw={"msg_id": msg.id},
        )
        await self._dispatch(incoming)
        return "success"

    def verify_signature(self, signature: str, timestamp: str, nonce: str) -> bool:
        """Verify WeChat server callback signature."""
        params = sorted([self._token, timestamp, nonce])
        digest = hashlib.sha1("".join(params).encode()).hexdigest()
        return digest == signature
