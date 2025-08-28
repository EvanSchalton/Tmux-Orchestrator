"""Message types and enums for PM pubsub integration."""

from enum import Enum


class MessagePriority(Enum):
    """Message priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class MessageCategory(Enum):
    """Message categories."""

    HEALTH = "health"
    RECOVERY = "recovery"
    STATUS = "status"
    TASK = "task"
    ESCALATION = "escalation"
