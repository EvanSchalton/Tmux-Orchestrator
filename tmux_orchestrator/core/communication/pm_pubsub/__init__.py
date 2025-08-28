"""PM pubsub integration module with backwards compatibility.

This module provides decomposed PM pubsub functionality following SRP principles
while maintaining backwards compatibility with the original pm_pubsub_integration.py file.
"""

from .message_types import MessageCategory, MessagePriority
from .notification_handler import NotificationHandler
from .pm_integration import PMPubsubIntegration
from .script_generator import create_pm_monitoring_script

# Backwards compatibility - re-export main class and function
__all__ = [
    "PMPubsubIntegration",
    "MessagePriority",
    "MessageCategory",
    "NotificationHandler",
    "create_pm_monitoring_script",
]
