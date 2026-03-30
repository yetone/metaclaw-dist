"""Telegram channel adapter using python-telegram-bot."""

from __future__ import annotations

import logging
import os
from typing import Any

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class TelegramChannel(BaseChannel):
    """Telegram adapter using long-polling (no public URL required)."""

    @property
    def name(self) -> str:
        return "telegram"

    @property
    def connection_type(self) -> str:
        return "polling"

    async def start(self) -> None:
        from telegram import Update
        from telegram.ext import (
            ApplicationBuilder,
            ContextTypes,
            MessageHandler,
            filters,
        )

        token = os.getenv(
            self._config.get("bot_token_env", "TELEGRAM_BOT_TOKEN"), ""
        )
        if not token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN must be set. "
                "Message @BotFather on Telegram to create a bot."
            )

        self._app = ApplicationBuilder().token(token).build()

        async def handle_message(
            update: Update, context: ContextTypes.DEFAULT_TYPE
        ) -> None:
            if not update.message or not update.message.text:
                return

            thread_id = None
            if update.message.reply_to_message:
                thread_id = str(update.message.reply_to_message.message_id)

            message = IncomingMessage(
                channel_type="telegram",
                channel_id=str(update.message.chat_id),
                user_id=str(update.message.from_user.id) if update.message.from_user else "",
                user_name=(
                    update.message.from_user.username or ""
                    if update.message.from_user
                    else ""
                ),
                thread_id=thread_id,
                content=update.message.text,
                raw={"message_id": update.message.message_id},
            )
            await self._dispatch(message)

        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        logger.info("Telegram channel connected via long-polling")

    async def stop(self) -> None:
        if hasattr(self, "_app"):
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def send(self, message: OutgoingMessage) -> None:
        # Telegram has a 4096 char limit
        content = message.content
        chat_id = int(message.channel_id)

        if len(content) > 4096:
            chunks = [content[i : i + 4096] for i in range(0, len(content), 4096)]
            for chunk in chunks:
                await self._app.bot.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    parse_mode="Markdown",
                )
        else:
            await self._app.bot.send_message(
                chat_id=chat_id,
                text=content,
                parse_mode="Markdown",
            )
