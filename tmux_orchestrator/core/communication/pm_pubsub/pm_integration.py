"""PM-specific pubsub integration operations."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from .message_types import MessageCategory, MessagePriority
from .notification_handler import NotificationHandler


class PMPubsubIntegration:
    """Main PM pubsub integration class combining all PM-specific functionality."""

    def __init__(self, session: str = "pm:0"):
        """Initialize PM pubsub integration.

        Args:
            session: PM session identifier (default: pm:0)
        """
        self.session = session
        self.notification_handler = NotificationHandler(session)
        self.message_store = Path.home() / ".tmux_orchestrator" / "messages"

    def get_daemon_notifications(self, since_minutes: int = 30) -> list[dict[str, Any]]:
        """Get daemon notifications from the last N minutes."""
        return self.notification_handler.get_daemon_notifications(since_minutes)

    def get_management_broadcasts(self, priority: str = "high") -> list[dict[str, Any]]:
        """Get management group broadcasts of specified priority."""
        return self.notification_handler.get_management_broadcasts(priority)

    def check_for_recovery_actions(self) -> list[dict[str, Any]]:
        """Check for daemon recovery action notifications."""
        return self.notification_handler.check_for_recovery_actions()

    def acknowledge_notification(self, notification_id: str, action_taken: str):
        """Acknowledge a daemon notification with action taken."""
        self.notification_handler.acknowledge_notification(notification_id, action_taken)

    def request_daemon_status(self) -> bool:
        """Request current daemon status update."""
        return self.notification_handler.request_daemon_status()

    def monitor_pubsub_health(self) -> dict[str, Any]:
        """Check pubsub system health and message statistics."""
        return self.notification_handler.monitor_pubsub_health()

    async def start_notification_monitoring(self, check_interval: int = 30):
        """Start async monitoring loop for notifications.

        Args:
            check_interval: How often to check for notifications (seconds)
        """
        print(f"PM {self.session} starting notification monitoring (every {check_interval}s)")

        while True:
            try:
                # Check for high-priority notifications
                notifications = self.get_daemon_notifications(since_minutes=5)
                high_priority_notifications = [
                    n
                    for n in notifications
                    if n.get("priority") in [MessagePriority.CRITICAL.value, MessagePriority.HIGH.value]
                ]

                if high_priority_notifications:
                    print(f"PM {self.session} received {len(high_priority_notifications)} high-priority notifications")
                    for notification in high_priority_notifications:
                        await self._handle_high_priority_notification(notification)

                # Check for recovery actions
                recovery_actions = self.check_for_recovery_actions()
                if recovery_actions:
                    print(f"PM {self.session} found {len(recovery_actions)} recovery actions")
                    for action in recovery_actions:
                        await self._handle_recovery_action(action)

            except Exception as e:
                print(f"Error in notification monitoring: {e}")

            await asyncio.sleep(check_interval)

    async def _handle_high_priority_notification(self, notification: dict[str, Any]):
        """Handle a high-priority notification.

        Args:
            notification: The notification to handle
        """
        notification_id = notification.get("id", "unknown")
        category = notification.get("category", "unknown")
        notification.get("content", "")

        print(f"PM {self.session} handling high-priority {category} notification: {notification_id}")

        # Basic notification handling logic
        if category == MessageCategory.HEALTH.value:
            action = "Reviewed health status and monitoring"
        elif category == MessageCategory.RECOVERY.value:
            action = "Initiated recovery coordination"
        elif category == MessageCategory.ESCALATION.value:
            action = "Escalated to project oversight"
        else:
            action = "Reviewed and acknowledged notification"

        self.acknowledge_notification(notification_id, action)

    async def _handle_recovery_action(self, action: dict[str, Any]):
        """Handle a recovery action notification.

        Args:
            action: The recovery action to handle
        """
        action_id = action.get("id", "unknown")
        action_required = action.get("action_required", "review_required")
        action.get("content", "")

        print(f"PM {self.session} handling recovery action {action_id}: {action_required}")

        # Basic recovery action logic
        if action_required == "restart_required":
            action_taken = "Coordinating agent restart"
        elif action_required == "kill_required":
            action_taken = "Coordinating agent termination"
        elif action_required == "spawn_required":
            action_taken = "Coordinating new agent spawn"
        else:
            action_taken = "Under review - action assessment in progress"

        self.acknowledge_notification(action_id, action_taken)

    def get_notification_summary(self) -> dict[str, Any]:
        """Get a summary of recent notifications and system status.

        Returns:
            Summary dictionary with notification counts and status
        """
        try:
            # Get recent notifications
            notifications = self.get_daemon_notifications(since_minutes=60)
            recovery_actions = self.check_for_recovery_actions()
            health_status = self.monitor_pubsub_health()

            # Count by priority
            priority_counts = {
                MessagePriority.CRITICAL.value: 0,
                MessagePriority.HIGH.value: 0,
                MessagePriority.NORMAL.value: 0,
                MessagePriority.LOW.value: 0,
            }

            for notification in notifications:
                priority = notification.get("priority", MessagePriority.NORMAL.value)
                if priority in priority_counts:
                    priority_counts[priority] += 1

            return {
                "session": self.session,
                "timestamp": datetime.now().isoformat(),
                "total_notifications": len(notifications),
                "recovery_actions": len(recovery_actions),
                "priority_breakdown": priority_counts,
                "pubsub_health": health_status,
                "unacknowledged_count": len([n for n in notifications if not n.get("acknowledged", False)]),
            }

        except Exception as e:
            print(f"Error generating notification summary: {e}")
            return {
                "session": self.session,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "total_notifications": 0,
                "recovery_actions": 0,
            }
