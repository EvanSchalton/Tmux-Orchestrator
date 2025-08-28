"""Interface for notification management."""

from abc import ABC, abstractmethod
from typing import Any


class NotificationManagerInterface(ABC):
    """Interface for notification management."""

    @abstractmethod
    def send_notification(self, event_type: str, message: str, details: dict[str, Any] | None = None) -> bool:
        """Send a notification.

        Args:
            event_type: Type of notification event
            message: Notification message
            details: Optional additional details

        Returns:
            True if notification sent successfully
        """
        pass

    @abstractmethod
    def should_notify(self, event_type: str, target: str) -> bool:
        """Check if notification should be sent.

        Args:
            event_type: Type of event
            target: Target of the event

        Returns:
            True if notification should be sent
        """
        pass

    @abstractmethod
    def notify_agent_crash(self, agent_target: str, error_message: str, session: str) -> None:
        """Notify about agent crash.

        Args:
            agent_target: Target of crashed agent
            error_message: Error description
            session: Session name
        """
        pass

    @abstractmethod
    def notify_fresh_agent(self, agent_target: str) -> None:
        """Notify about fresh agent detection.

        Args:
            agent_target: Target of fresh agent
        """
        pass

    @abstractmethod
    def notify_recovery_needed(self, agent_target: str, reason: str) -> None:
        """Notify about recovery needed.

        Args:
            agent_target: Target needing recovery
            reason: Recovery reason
        """
        pass
