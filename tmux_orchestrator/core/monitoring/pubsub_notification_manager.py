"""
Pubsub-enabled notification management system.

This module provides high-performance notification delivery using the messaging daemon,
with fallback to direct tmux commands for reliability.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.messaging_daemon import DaemonClient
from tmux_orchestrator.utils.tmux import TMUXManager

from .types import IdleType, NotificationEvent, NotificationManagerInterface, NotificationType


class PubsubNotificationManager(NotificationManagerInterface):
    """High-performance notification system using pubsub daemon."""

    def __init__(self, tmux: TMUXManager, config: Config, logger: logging.Logger):
        """Initialize the pubsub-enabled notification manager."""
        super().__init__(tmux, config, logger)
        self._queued_notifications: List[NotificationEvent] = []
        self._pm_notifications: Dict[str, List[str]] = defaultdict(list)
        self._last_notification_times: Dict[str, datetime] = {}
        self._notification_cooldown = 300  # 5 minutes between duplicate notifications
        self._daemon_client: Optional[DaemonClient] = None
        self._use_daemon = True  # Toggle for daemon vs direct tmux

    def initialize(self) -> bool:
        """Initialize the notification manager and daemon client."""
        try:
            self.logger.info("Initializing PubsubNotificationManager")
            
            # Initialize daemon client
            self._daemon_client = DaemonClient()
            
            # Test daemon connectivity
            asyncio.run(self._test_daemon_connection())
            
            return True
        except Exception as e:
            self.logger.warning(f"Daemon client initialization failed, falling back to direct tmux: {e}")
            self._use_daemon = False
            return True

    async def _test_daemon_connection(self) -> bool:
        """Test if daemon is available."""
        try:
            response = await self._daemon_client.get_status()
            if response.get("status") == "active":
                self.logger.info("Daemon connection successful")
                return True
        except Exception:
            pass
        return False

    def cleanup(self) -> None:
        """Clean up notification manager resources."""
        self.logger.info("Cleaning up PubsubNotificationManager")
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
                self.logger.debug(
                    f"Throttling notification for {notification_key} "
                    f"(last sent {time_diff:.0f}s ago)"
                )
                return

        self._queued_notifications.append(event)
        self._last_notification_times[notification_key] = datetime.now()
        self.logger.debug(f"Queued notification: {event.type} for {event.target}")

    def send_queued_notifications(self) -> int:
        """
        Send all queued notifications using pubsub daemon for performance.

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

    def notify_agent_crash(self, target: str, error_type: str, session: str, metadata: Optional[Dict] = None) -> None:
        """Send high-priority agent crash notification."""
        if metadata is None:
            metadata = {}

        message = f"🚨 AGENT CRASH: {target} - {error_type}"

        event = NotificationEvent(
            type=NotificationType.AGENT_CRASH,
            target=target,
            message=message,
            timestamp=datetime.now(),
            session=session,
            metadata={**metadata, "error_type": error_type, "priority": "high"},
        )

        self.queue_notification(event)
        self.logger.warning(f"Agent crash notification queued for {target}: {error_type}")

    def notify_agent_idle(
        self, target: str, idle_type: IdleType, session: str, metadata: Optional[Dict] = None
    ) -> None:
        """Send low-priority agent idle notification."""
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
            metadata={**metadata, "idle_type": idle_type.value, "priority": "low"},
        )

        self.queue_notification(event)
        self.logger.info(f"Agent idle notification queued for {target}: {idle_type.value}")

    def notify_fresh_agent(self, target: str, session: str, metadata: Optional[Dict] = None) -> None:
        """Send normal-priority fresh agent notification."""
        if metadata is None:
            metadata = {}

        message = f"🌱 FRESH AGENT ALERT: {target} - Ready for briefing"

        event = NotificationEvent(
            type=NotificationType.AGENT_FRESH,
            target=target,
            message=message,
            timestamp=datetime.now(),
            session=session,
            metadata={**metadata, "priority": "normal"},
        )

        self.queue_notification(event)
        self.logger.info(f"Fresh agent notification queued for {target}")

    def notify_team_idle(self, session: str, agent_count: int, metadata: Optional[Dict] = None) -> None:
        """Send normal-priority team idle notification."""
        if metadata is None:
            metadata = {}

        message = f"😴 TEAM IDLE: {session} - {agent_count} agents idle"

        event = NotificationEvent(
            type=NotificationType.TEAM_IDLE,
            target=session,
            message=message,
            timestamp=datetime.now(),
            session=session,
            metadata={**metadata, "agent_count": agent_count, "priority": "normal"},
        )

        self.queue_notification(event)
        self.logger.warning(f"Team idle notification queued for {session}")

    def notify_recovery_needed(self, target: str, issue: str, session: str, metadata: Optional[Dict] = None) -> None:
        """Send critical-priority recovery needed notification."""
        if metadata is None:
            metadata = {}

        message = f"🔧 RECOVERY NEEDED: {target} - {issue}"

        event = NotificationEvent(
            type=NotificationType.RECOVERY_NEEDED,
            target=target,
            message=message,
            timestamp=datetime.now(),
            session=session,
            metadata={**metadata, "issue": issue, "priority": "critical"},
        )

        self.queue_notification(event)
        self.logger.warning(f"Recovery notification queued for {target}: {issue}")

    def _collect_notification_for_pm(self, event: NotificationEvent) -> None:
        """Collect notification for PM in the target session."""
        # Find PM in the session
        pm_target = self._find_pm_in_session(event.session)
        if not pm_target:
            self.logger.warning(f"No PM found in session {event.session} for notification")
            return

        # Add message to PM's collection with priority metadata
        self._pm_notifications[pm_target].append(event.formatted_message)
        self.logger.debug(f"Collected notification for PM {pm_target}: {event.message}")

    def _send_collected_notifications(self) -> int:
        """Send all collected notifications using pubsub daemon for performance."""
        sent_count = 0

        for pm_target, messages in self._pm_notifications.items():
            if not messages:
                continue

            try:
                # Build consolidated report
                timestamp = datetime.now().strftime("%H:%M:%S UTC")
                report_header = f"🔔 MONITORING REPORT - {timestamp}\\n"

                # Group messages by type and priority
                critical_messages = []
                high_priority = []
                normal_priority = []
                low_priority = []

                for msg in messages:
                    if "CRASH" in msg or "FAILURE" in msg:
                        critical_messages.append(msg)
                    elif "RECOVERY NEEDED" in msg:
                        high_priority.append(msg)
                    elif "FRESH AGENT" in msg or "TEAM IDLE" in msg:
                        normal_priority.append(msg)
                    elif "IDLE" in msg:
                        low_priority.append(msg)
                    else:
                        normal_priority.append(msg)

                # Build report sections
                report_sections = []

                if critical_messages:
                    report_sections.append("🚨 CRITICAL - Agent Crashes:\\n" + "\\n".join(critical_messages))

                if high_priority:
                    report_sections.append("🔧 HIGH PRIORITY - Recovery Needed:\\n" + "\\n".join(high_priority))

                if normal_priority:
                    report_sections.append("📋 NORMAL PRIORITY:\\n" + "\\n".join(normal_priority))

                if low_priority:
                    report_sections.append("💤 LOW PRIORITY - Idle Agents:\\n" + "\\n".join(low_priority))

                # Send consolidated report via pubsub or fallback
                if report_sections:
                    full_report = report_header + "\\n\\n".join(report_sections)
                    
                    # Determine priority based on content
                    priority = "normal"
                    if critical_messages:
                        priority = "critical"
                    elif high_priority:
                        priority = "high"
                    
                    success = self._send_notification(pm_target, full_report, priority)
                    if success:
                        sent_count += 1
                        self.logger.info(
                            f"Sent consolidated report to PM {pm_target} "
                            f"with {len(messages)} notifications via {'daemon' if self._use_daemon else 'tmux'}"
                        )

            except Exception as e:
                self.logger.error(f"Failed to send notifications to PM {pm_target}: {e}")

        # Clear sent notifications
        self._pm_notifications.clear()

        return sent_count

    def _send_notification(self, target: str, message: str, priority: str = "normal") -> bool:
        """Send notification using daemon with fallback to direct tmux."""
        if self._use_daemon and self._daemon_client:
            try:
                # Use asyncio.run for sync context
                response = asyncio.run(
                    self._daemon_client.publish(target, message, priority, ["monitoring", "notification"])
                )
                return response.get("status") == "queued"
            except Exception as e:
                self.logger.warning(f"Daemon send failed, falling back to direct tmux: {e}")
                self._use_daemon = False

        # Fallback to direct tmux
        return self.tmux.send_keys(target, message)

    def _find_pm_in_session(self, session: str) -> Optional[str]:
        """Find PM agent in the specified session."""
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

    def get_notification_stats(self) -> Dict[str, any]:
        """Get notification statistics including daemon performance."""
        stats = {
            "queued_notifications": len(self._queued_notifications),
            "pm_collections": len(self._pm_notifications),
            "total_pm_messages": sum(len(msgs) for msgs in self._pm_notifications.values()),
            "delivery_method": "daemon" if self._use_daemon else "direct_tmux",
        }
        
        # Add daemon stats if available
        if self._use_daemon and self._daemon_client:
            try:
                daemon_stats = asyncio.run(self._daemon_client.get_status())
                if daemon_stats.get("status") == "active":
                    stats["daemon_performance"] = {
                        "avg_delivery_ms": daemon_stats.get("avg_delivery_time_ms", "N/A"),
                        "messages_processed": daemon_stats.get("messages_processed", 0),
                        "queue_size": daemon_stats.get("queue_size", 0),
                    }
            except Exception:
                pass
                
        return stats