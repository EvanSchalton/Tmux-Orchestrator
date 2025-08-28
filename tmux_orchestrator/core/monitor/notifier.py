"""Notification system for monitoring events and PM communication."""

import logging
from datetime import datetime

from tmux_orchestrator.core.monitor_helpers import is_pm_busy
from tmux_orchestrator.utils.tmux import TMUXManager


class MonitorNotifier:
    """Handles all notification functionality for the monitoring system."""

    def __init__(self) -> None:
        """Initialize the notifier."""
        self._pm_message_queues: dict[str, list[str]] = {}

    def notify_crash(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Notify PM about crashed Claude agent.

        Args:
            tmux: TMUXManager instance
            target: Crashed agent target
            logger: Logger instance
            pm_notifications: PM notifications dictionary
        """
        try:
            # Find PM target IN THE SAME SESSION
            session_name = target.split(":")[0]
            session_logger = self._get_session_logger(session_name)
            pm_target = self._find_pm_in_session(tmux, session_name)
            if not pm_target:
                session_logger.warning(f"No PM found in session {session_name} to notify about crash")
                return

            # Get current time for cooldown check
            datetime.now()

            # Create crash notification
            message = f"🚨 AGENT CRASH ALERT: Agent {target} has crashed and needs immediate attention. Please check and restart if needed."

            # Add to PM notifications
            if pm_target not in pm_notifications:
                pm_notifications[pm_target] = []
            pm_notifications[pm_target].append(message)

            session_logger.info(f"Queued crash notification for PM {pm_target} about agent {target}")

        except Exception as e:
            logger.error(f"Failed to notify crash for {target}: {e}")

    def notify_fresh_agent(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Notify PM about fresh agent needing briefing.

        Args:
            tmux: TMUXManager instance
            target: Fresh agent target
            logger: Logger instance
            pm_notifications: PM notifications dictionary
        """
        try:
            session_name = target.split(":")[0]
            session_logger = self._get_session_logger(session_name)
            pm_target = self._find_pm_in_session(tmux, session_name)

            if not pm_target:
                session_logger.warning(f"No PM found in session {session_name} to notify about fresh agent")
                return

            message = f"🆕 FRESH AGENT: Agent {target} is ready for briefing and task assignment. Please provide context and initial instructions."

            if pm_target not in pm_notifications:
                pm_notifications[pm_target] = []
            pm_notifications[pm_target].append(message)

            session_logger.info(f"Queued fresh agent notification for PM {pm_target} about agent {target}")

        except Exception as e:
            logger.error(f"Failed to notify fresh agent {target}: {e}")

    def notify_recovery_needed(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Notify about agent recovery needed.

        Args:
            tmux: TMUXManager instance
            target: Agent target needing recovery
            logger: Logger instance
        """
        try:
            session_name = target.split(":")[0]
            session_logger = self._get_session_logger(session_name)
            pm_target = self._find_pm_in_session(tmux, session_name)

            if not pm_target:
                session_logger.warning(f"No PM found in session {session_name} to notify about recovery")
                return

            message = f"⚠️ RECOVERY NEEDED: Agent {target} requires manual recovery or restart. Please investigate and take corrective action."
            self.queue_pm_message(pm_target, message, session_logger)

        except Exception as e:
            logger.error(f"Failed to notify recovery needed for {target}: {e}")

    def check_idle_notification(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Check and send idle notification for agent.

        Args:
            tmux: TMUXManager instance
            target: Idle agent target
            logger: Logger instance
            pm_notifications: PM notifications dictionary
        """
        try:
            session_name = target.split(":")[0]
            session_logger = self._get_session_logger(session_name)
            pm_target = self._find_pm_in_session(tmux, session_name)

            if not pm_target:
                session_logger.warning(f"No PM found in session {session_name} to notify about idle agent")
                return

            message = f"💤 AGENT IDLE: Agent {target} has completed current tasks and is ready for new assignments."

            if pm_target not in pm_notifications:
                pm_notifications[pm_target] = []
            pm_notifications[pm_target].append(message)

            session_logger.info(f"Queued idle notification for PM {pm_target} about agent {target}")

        except Exception as e:
            logger.error(f"Failed to send idle notification for {target}: {e}")

    def send_simple_restart_notification(
        self, tmux: TMUXManager, target: str, failure_reason: str, logger: logging.Logger
    ) -> None:
        """Send simple restart notification with one-command solution.

        Args:
            tmux: TMUXManager instance
            target: Failed agent target
            failure_reason: Reason for failure
            logger: Logger instance
        """
        try:
            session_name = target.split(":")[0]
            session_logger = self._get_session_logger(session_name)
            pm_target = self._find_pm_in_session(tmux, session_name)

            if not pm_target:
                session_logger.warning(f"No PM found in session {session_name} for restart notification")
                return

            # Create ready-to-use restart command
            window_index = target.split(":")[1]
            restart_command = f"tmux-orc spawn agent {session_name}:{window_index}"

            message = f"""🔄 AGENT RESTART NEEDED: {failure_reason}

Agent: {target}
Status: Crashed/Failed

One-command fix:
{restart_command}

Copy and paste the command above to restart the agent."""

            self.queue_pm_message(pm_target, message, session_logger)
            session_logger.info(f"Sent restart notification for {target} to PM {pm_target}")

        except Exception as e:
            logger.error(f"Failed to send restart notification for {target}: {e}")

    def notify_team_of_pm_recovery(self, session_name: str, pm_target: str) -> None:
        """Notify team of PM recovery.

        Args:
            session_name: Session where PM was recovered
            pm_target: New PM target
        """
        try:
            logger = self._get_session_logger(session_name)
            logger.info(f"PM recovery completed for session {session_name} at {pm_target}")
            # This could be extended to send notifications to team members

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to notify team of PM recovery: {e}")

    def send_collected_notifications(
        self, tmux: TMUXManager, pm_notifications: dict[str, list[str]], logger: logging.Logger
    ) -> None:
        """Send collected notifications to PMs.

        Args:
            tmux: TMUXManager instance
            pm_notifications: Dictionary of PM targets to their notification lists
            logger: Logger instance
        """
        try:
            for pm_target, messages in pm_notifications.items():
                if not messages:
                    continue

                # Combine messages into a single notification
                combined_message = "📊 MONITORING UPDATE:\n\n" + "\n\n".join(messages)

                # Send to PM with busy check
                self._send_pm_message_with_busy_check(tmux, pm_target, combined_message, logger)

        except Exception as e:
            logger.error(f"Failed to send collected notifications: {e}")

    def queue_pm_message(self, pm_target: str, message: str, logger: logging.Logger) -> None:
        """Queue a message for PM delivery.

        Args:
            pm_target: PM target identifier
            message: Message to queue
            logger: Logger instance
        """
        try:
            if pm_target not in self._pm_message_queues:
                self._pm_message_queues[pm_target] = []

            self._pm_message_queues[pm_target].append(message)
            logger.debug(f"Queued message for PM {pm_target}")

        except Exception as e:
            logger.error(f"Failed to queue PM message: {e}")

    def process_pm_message_queues(self, tmux: TMUXManager, logger: logging.Logger) -> None:
        """Process queued PM messages.

        Args:
            tmux: TMUXManager instance
            logger: Logger instance
        """
        try:
            for pm_target, messages in list(self._pm_message_queues.items()):
                if not messages:
                    continue

                # Combine messages
                combined_message = "\n\n".join(messages)

                # Send with busy check
                success = self._send_pm_message_with_busy_check(tmux, pm_target, combined_message, logger)

                if success:
                    # Clear sent messages
                    self._pm_message_queues[pm_target] = []
                    logger.info(f"Sent {len(messages)} queued messages to PM {pm_target}")

        except Exception as e:
            logger.error(f"Failed to process PM message queues: {e}")

    def _send_pm_message_with_busy_check(
        self, tmux: TMUXManager, pm_target: str, message: str, logger: logging.Logger
    ) -> bool:
        """Send message to PM with busy check.

        Args:
            tmux: TMUXManager instance
            pm_target: PM target identifier
            message: Message to send
            logger: Logger instance

        Returns:
            bool: True if message was sent successfully
        """
        try:
            # Check if PM is busy
            content = tmux.capture_pane(pm_target, lines=50)

            if is_pm_busy(content):
                logger.debug(f"PM {pm_target} is busy, deferring message")
                return False

            # Send message
            tmux.send_keys(pm_target, message, literal=True)
            tmux.send_keys(pm_target, "Enter")

            logger.info(f"Sent message to PM {pm_target}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message to PM {pm_target}: {e}")
            return False

    def notify_agent(self, target: str, message: str) -> None:
        """Send notification to specific agent.

        Args:
            target: Agent target identifier
            message: Message to send
        """
        try:
            logger = logging.getLogger(__name__)
            logger.info(f"Notification to {target}: {message}")
            # This could be extended to actually send the message to the agent

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to notify agent {target}: {e}")

    # Helper methods that need to be connected to other components
    def _find_pm_in_session(self, tmux: TMUXManager, session: str) -> str | None:
        """Find PM agent in specific session - placeholder."""
        # This would need to be connected to the actual PM finding logic
        return None

    def _get_session_logger(self, session_name: str) -> logging.Logger:
        """Get session-specific logger."""
        return logging.getLogger(f"notifier.{session_name}")
