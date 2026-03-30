"""Channel bridging system for multi-platform communication."""

from metaclaw.channels.base import BaseChannel
from metaclaw.channels.message import IncomingMessage, OutgoingMessage, Attachment

__all__ = ["BaseChannel", "IncomingMessage", "OutgoingMessage", "Attachment"]
