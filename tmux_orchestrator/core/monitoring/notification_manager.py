"""
Notification management system.

This module handles notification queuing, batching, and delivery.
Extracted from the monolithic monitor.py to improve maintainability and testability.
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

from .types import IdleType, NotificationEvent, NotificationManagerInterface, NotificationType


class NotificationManager(NotificationManagerInterface):
    """Centralized notification and alerting system."""

    def __init__(self, tmux: TMUXManager, config: Config, logger: logging.Logger):
        """Initialize the notification manager."""
        super().__init__(tmux, config, logger)
        self._queued_notifications: list[NotificationEvent] = []
        self._pm_notifications: dict[str, list[str]] = defaultdict(list)
        self._last_notification_times: dict[str, datetime] = {}
        self._notification_cooldown = 300  # 5 minutes between duplicate notifications

    def initialize(self) -> bool:
        """Initialize the notification manager."""
        try:
            self.logger.info("Initializing NotificationManager")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize NotificationManager: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up notification manager resources."""
        self.logger.info("Cleaning up NotificationManager")
        self._queued_notifications.clear()
        self._pm_notifications.clear()
        self._last_notification_times.clear()

    def queue_notification(self, event: NotificationEvent) -> None:
        """
        Queue a notification for sending.

        Args:
            event: NotificationEvent to queue
        """
        # Check if we should throttle this notification
        notification_key = f"{event.type.value}:{event.target}"
        last_time = self._last_notification_times.get(notification_key)

        if last_time:
            time_diff = (datetime.now() - last_time).total_seconds()
            if time_diff < self._notification_cooldown:
                self.logger.debug(f"Throttling notification for {notification_key} (last sent {time_diff:.0f}s ago)")
                return

        self._queued_notifications.append(event)
        self._last_notification_times[notification_key] = datetime.now()
        self.logger.debug(f"Queued notification: {event.type} for {event.target}")

    def send_queued_notifications(self) -> int:
        """
        Send all queued notifications.

        Returns:
            Number of notifications sent
        """
        if not self._queued_notifications:
            return 0

        # Group notifications by PM/session for batching
        for event in self._queued_notifications:
            self._collect_notification_for_pm(event)

        # Send batched notifications to PMs
        sent_count = self._send_collected_notifications()

        # Clear processed notifications
        self._queued_notifications.clear()

        return sent_count

    def notify_agent_crash(self, target: str, error_type: str, session: str, metadata: Optional[dict] = None) -> None:
        """
        Send agent crash notification.

        Args:
            target: Agent target identifier
            error_type: Type of error detected
            session: Session name
            metadata: Additional notification metadata
        """
        if metadata is None:
            metadata = {}

        message = f"🚨 AGENT CRASH: {target} - {error_type}"

        event = NotificationEvent(
            type=NotificationType.AGENT_CRASH,
            target=target,
            message=message,
            timestamp=datetime.now(),
            session=session,
            metadata={**metadata, "error_type": error_type},
        )

        self.queue_notification(event)
        self.logger.warning(f"Agent crash notification queued for {target}: {error_type}")

    def notify_agent_idle(
        self, target: str, idle_type: IdleType, session: str, metadata: Optional[dict] = None
    ) -> None:
        """
        Send agent idle notification.

        Args:
            target: Agent target identifier
            idle_type: Type of idle state
            session: Session name
            metadata: Additional notification metadata
        """
        if metadata is None:
            metadata = {}

        # Skip notifications for certain idle types
        if idle_type in [IdleType.COMPACTION_STATE]:
            self.logger.debug(f"Skipping notification for {target} - compaction state")
            return

        message = f"💤 AGENT IDLE: {target} - {idle_type.value}"

        event = NotificationEvent(
            type=NotificationType.AGENT_IDLE,
            target=target,
            message=message,
            timestamp=datetime.now(),
            session=session,
            metadata={**metadata, "idle_type": idle_type.value},
        )

        self.queue_notification(event)
        self.logger.info(f"Agent idle notification queued for {target}: {idle_type.value}")

    def notify_fresh_agent(self, target: str, session: str, metadata: Optional[dict] = None) -> None:
        """
        Send fresh agent notification.

        Args:
            target: Agent target identifier
            session: Session name
            metadata: Additional notification metadata
        """
        if metadata is None:
            metadata = {}

        message = f"🌱 FRESH AGENT ALERT: {target} - Ready for briefing"

        event = NotificationEvent(
            type=NotificationType.AGENT_FRESH,
            target=target,
            message=message,
            timestamp=datetime.now(),
            session=session,
            metadata=metadata,
        )

        self.queue_notification(event)
        self.logger.info(f"Fresh agent notification queued for {target}")

    def notify_team_idle(self, session: str, agent_count: int, metadata: Optional[dict] = None) -> None:
        """
        Send team idle notification.

        Args:
            session: Session name
            agent_count: Number of idle agents
            metadata: Additional notification metadata
        """
        if metadata is None:
            metadata = {}

        message = f"😴 TEAM IDLE: {session} - {agent_count} agents idle"

        event = NotificationEvent(
            type=NotificationType.TEAM_IDLE,
            target=session,
            message=message,
            timestamp=datetime.now(),
            session=session,
            metadata={**metadata, "agent_count": agent_count},
        )

        self.queue_notification(event)
        self.logger.warning(f"Team idle notification queued for {session}")

    def notify_recovery_needed(self, target: str, issue: str, session: str, metadata: Optional[dict] = None) -> None:
        """
        Send recovery needed notification.

        Args:
            target: Agent target identifier
            issue: Issue description
            session: Session name
            metadata: Additional notification metadata
        """
        if metadata is None:
            metadata = {}

        message = f"🔧 RECOVERY NEEDED: {target} - {issue}"

        event = NotificationEvent(
            type=NotificationType.RECOVERY_NEEDED,
            target=target,
            message=message,
            timestamp=datetime.now(),
            session=session,
            metadata={**metadata, "issue": issue},
        )

        self.queue_notification(event)
        self.logger.warning(f"Recovery notification queued for {target}: {issue}")

    def _collect_notification_for_pm(self, event: NotificationEvent) -> None:
        """
        Collect notification for PM in the target session.

        Args:
            event: NotificationEvent to collect
        """
        # Find PM in the session
        pm_target = self._find_pm_in_session(event.session)
        if not pm_target:
            self.logger.warning(f"No PM found in session {event.session} for notification")
            return

        # Add message to PM's collection
        self._pm_notifications[pm_target].append(event.formatted_message)
        self.logger.debug(f"Collected notification for PM {pm_target}: {event.message}")

    def _send_collected_notifications(self) -> int:
        """
        Send all collected notifications as consolidated reports to PMs.

        Returns:
            Number of notifications sent
        """
        sent_count = 0

        for pm_target, messages in self._pm_notifications.items():
            if not messages:
                continue

            try:
                # Build consolidated report
                timestamp = datetime.now().strftime("%H:%M:%S UTC")
                report_header = f"🔔 MONITORING REPORT - {timestamp}\\n"

                # Group messages by type
                crashed_agents = []
                fresh_agents = []
                idle_agents = []
                missing_agents = []
                recovery_needed = []
                other_messages = []

                for msg in messages:
                    if "CRASH" in msg or "FAILURE" in msg:
                        crashed_agents.append(msg)
                    elif "FRESH AGENT ALERT" in msg:
                        fresh_agents.append(msg)
                    elif "IDLE" in msg:
                        idle_agents.append(msg)
                    elif "MISSING" in msg:
                        missing_agents.append(msg)
                    elif "RECOVERY NEEDED" in msg:
                        recovery_needed.append(msg)
                    else:
                        other_messages.append(msg)

                # Build report sections
                report_sections = []

                if crashed_agents:
                    report_sections.append("🚨 CRITICAL - Agent Crashes:\\n" + "\\n".join(crashed_agents))

                if recovery_needed:
                    report_sections.append("🔧 RECOVERY NEEDED:\\n" + "\\n".join(recovery_needed))

                if fresh_agents:
                    report_sections.append("🌱 Fresh Agents (Need Briefing):\\n" + "\\n".join(fresh_agents))

                if idle_agents:
                    report_sections.append("💤 Idle Agents:\\n" + "\\n".join(idle_agents))

                if missing_agents:
                    report_sections.append("❌ Missing Agents:\\n" + "\\n".join(missing_agents))

                if other_messages:
                    report_sections.append("ℹ️ Other Alerts:\\n" + "\\n".join(other_messages))

                # Send consolidated report
                if report_sections:
                    full_report = report_header + "\\n\\n".join(report_sections)
                    self.tmux.send_keys(pm_target, full_report)
                    sent_count += 1
                    self.logger.info(f"Sent consolidated report to PM {pm_target} with {len(messages)} notifications")

            except Exception as e:
                self.logger.error(f"Failed to send notifications to PM {pm_target}: {e}")

        # Clear sent notifications
        self._pm_notifications.clear()

        return sent_count

    def _find_pm_in_session(self, session: str) -> Optional[str]:
        """
        Find PM agent in the specified session.

        Args:
            session: Session name to search

        Returns:
            PM target identifier or None if not found
        """
        try:
            windows = self.tmux.list_windows(session)
            for window in windows:
                window_name = window.get("name", "").lower()
                if "pm" in window_name or "project-manager" in window_name:
                    window_idx = window.get("index", "0")
                    return f"{session}:{window_idx}"
            return None

        except Exception as e:
            self.logger.error(f"Error finding PM in session {session}: {e}")
            return None

    def get_notification_stats(self) -> dict[str, int]:
        """Get notification statistics."""
        return {
            "queued_notifications": len(self._queued_notifications),
            "pm_collections": len(self._pm_notifications),
            "total_pm_messages": sum(len(msgs) for msgs in self._pm_notifications.values()),
        }
