"""Communication module for agent messaging."""

from .broadcast_message import broadcast_message
from .send_message import send_message

__all__ = ["send_message", "broadcast_message"]
