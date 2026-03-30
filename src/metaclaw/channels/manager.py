"""Channel lifecycle manager - starts/stops channel adapters based on config."""

from __future__ import annotations

import logging
from typing import Any

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.router import MessageRouter
from metaclaw.config import MetaClawConfig

logger = logging.getLogger(__name__)

# Lazy adapter imports to avoid requiring all channel dependencies
_ADAPTER_MAP: dict[str, str] = {
    "slack": "metaclaw.channels.adapters.slack.SlackChannel",
    "discord": "metaclaw.channels.adapters.discord.DiscordChannel",
    "telegram": "metaclaw.channels.adapters.telegram.TelegramChannel",
    "wechat": "metaclaw.channels.adapters.wechat.WeChatChannel",
    "line": "metaclaw.channels.adapters.line.LineChannel",
    "whatsapp": "metaclaw.channels.adapters.whatsapp.WhatsAppChannel",
    "email": "metaclaw.channels.adapters.email.EmailChannel",
    "webhook": "metaclaw.channels.adapters.webhook.WebhookChannel",
    "twilio": "metaclaw.channels.adapters.twilio.TwilioChannel",
    "google_chat": "metaclaw.channels.adapters.google_chat.GoogleChatChannel",
    "teams": "metaclaw.channels.adapters.teams.TeamsChannel",
    "zoom": "metaclaw.channels.adapters.zoom.ZoomChannel",
}


class ChannelManager:
    """Manages the lifecycle of channel adapters.

    Reads config, instantiates only enabled channels, and manages start/stop.
    """

    def __init__(self, config: MetaClawConfig, router: MessageRouter):
        self._config = config
        self._router = router
        self._channels: dict[str, BaseChannel] = {}

    def _load_adapter(self, channel_name: str) -> type[BaseChannel] | None:
        """Dynamically import a channel adapter class."""
        class_path = _ADAPTER_MAP.get(channel_name)
        if not class_path:
            logger.warning(f"Unknown channel: {channel_name}")
            return None

        module_path, class_name = class_path.rsplit(".", 1)
        try:
            import importlib

            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(
                f"Failed to load {channel_name} adapter: {e}. "
                f"Install with: pip install metaclaw[{channel_name}]"
            )
            return None

    async def start_all(self) -> list[str]:
        """Start all enabled channel adapters. Returns list of started channels."""
        started: list[str] = []

        for channel_name, channel_config in self._config.channels.items():
            if not channel_config.enabled:
                continue

            adapter_cls = self._load_adapter(channel_name)
            if adapter_cls is None:
                continue

            try:
                # Build adapter config dict
                config_dict = channel_config.model_dump()
                adapter = adapter_cls(config_dict)

                # Register with router
                self._router.register_channel(adapter)
                self._channels[channel_name] = adapter

                # Start adapter
                await adapter.start()
                started.append(channel_name)
                logger.info(f"Started channel: {channel_name}")

            except Exception as e:
                logger.error(f"Failed to start {channel_name}: {e}")

        return started

    async def stop_all(self) -> None:
        """Stop all running channel adapters."""
        for name, channel in self._channels.items():
            try:
                await channel.stop()
                logger.info(f"Stopped channel: {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")

        self._channels.clear()

    def get_running(self) -> list[str]:
        """Get list of running channel names."""
        return list(self._channels.keys())

    def get_webhook_channels(self) -> list[BaseChannel]:
        """Get channels that require webhook endpoints."""
        return [ch for ch in self._channels.values() if ch.is_webhook_based]
