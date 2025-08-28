"""Notification handling for PM pubsub integration."""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from tmux_orchestrator.utils.tmux import TMUXManager


class NotificationHandler:
    """Handles PM notification processing and daemon communication."""

    def __init__(self, session: str = "pm:0"):
        """Initialize notification handler.

        Args:
            session: PM session identifier (default: pm:0)
        """
        self.session = session
        self.tmux = TMUXManager()
        self.message_store = Path.home() / ".tmux_orchestrator" / "messages"

    def get_daemon_notifications(self, since_minutes: int = 30) -> list[dict[str, Any]]:
        """Get daemon notifications from the last N minutes.

        Args:
            since_minutes: How many minutes back to check

        Returns:
            List of daemon notification messages
        """
        try:
            since_time = datetime.now() - timedelta(minutes=since_minutes)
            since_iso = since_time.isoformat()

            # Use tmux-orc read to get messages with daemon filter
            result = subprocess.run(
                ["tmux-orc", "read", "--session", self.session, "--since", since_iso, "--filter", "daemon", "--json"],
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout:
                data = json.loads(result.stdout)
                return self._parse_daemon_messages(data.get("stored_messages", []))

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error retrieving daemon notifications: {e}")

        return []

    def get_management_broadcasts(self, priority: str = "high") -> list[dict[str, Any]]:
        """Get management group broadcasts of specified priority.

        Args:
            priority: Message priority to filter (critical, high, normal, low)

        Returns:
            List of management broadcast messages
        """
        try:
            # Read management group messages
            session_file = self.message_store / f"{self.session.replace(':', '_')}.json"

            if not session_file.exists():
                return []

            with open(session_file) as f:
                messages = json.load(f)

            # Filter for management messages with specified priority
            filtered_messages = []
            for msg in messages:
                if msg.get("priority") == priority and any(
                    tag in ["monitoring", "management", "recovery"] for tag in msg.get("tags", [])
                ):
                    filtered_messages.append(msg)

            return filtered_messages[-10:]  # Last 10 messages

        except (json.JSONDecodeError, OSError) as e:
            print(f"Error reading management broadcasts: {e}")

        return []

    def check_for_recovery_actions(self) -> list[dict[str, Any]]:
        """Check for daemon recovery action notifications.

        Returns:
            List of recovery action messages requiring PM attention
        """
        try:
            result = subprocess.run(
                ["tmux-orc", "read", "--session", self.session, "--filter", "recovery", "--tail", "20", "--json"],
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout:
                data = json.loads(result.stdout)
                return self._parse_recovery_messages(data.get("stored_messages", []))

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error checking recovery actions: {e}")

        return []

    def acknowledge_notification(self, notification_id: str, action_taken: str):
        """Acknowledge a daemon notification with action taken.

        Args:
            notification_id: ID of the notification being acknowledged
            action_taken: Description of action taken by PM
        """
        ack_message = f"PM ACK: {notification_id} - {action_taken} by {self.session} at {datetime.now().isoformat()}"

        try:
            subprocess.run(
                [
                    "tmux-orc",
                    "publish",
                    "--group",
                    "management",
                    "--priority",
                    "normal",
                    "--tag",
                    "acknowledgment",
                    "--tag",
                    "pm-response",
                    ack_message,
                ],
                check=True,
            )

        except subprocess.CalledProcessError as e:
            print(f"Error sending acknowledgment: {e}")

    def request_daemon_status(self) -> bool:
        """Request current daemon status update.

        Returns:
            True if request sent successfully
        """
        try:
            subprocess.run(
                [
                    "tmux-orc",
                    "publish",
                    "--group",
                    "management",
                    "--priority",
                    "normal",
                    "--tag",
                    "status-request",
                    "PM requesting daemon status update",
                ],
                check=True,
            )
            return True

        except subprocess.CalledProcessError as e:
            print(f"Error requesting daemon status: {e}")
            return False

    def monitor_pubsub_health(self) -> dict[str, Any]:
        """Check pubsub system health and message statistics.

        Returns:
            Dictionary with pubsub health information
        """
        try:
            result = subprocess.run(["tmux-orc", "health", "--json"], capture_output=True, text=True, check=True)

            if result.stdout:
                health_data = json.loads(result.stdout)
                return {
                    "daemon_running": health_data.get("daemon_running", False),
                    "message_count": health_data.get("message_count", 0),
                    "last_activity": health_data.get("last_activity"),
                    "pubsub_active": health_data.get("pubsub_active", False),
                }

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error checking pubsub health: {e}")

        return {"daemon_running": False, "message_count": 0, "pubsub_active": False}

    def _parse_daemon_messages(self, messages: list[dict]) -> list[dict[str, Any]]:
        """Parse raw daemon messages into structured format.

        Args:
            messages: Raw message data from daemon

        Returns:
            Parsed daemon messages
        """
        parsed = []
        for msg in messages:
            try:
                parsed_msg = {
                    "id": msg.get("id", "unknown"),
                    "timestamp": msg.get("timestamp", "unknown"),
                    "priority": msg.get("priority", "normal"),
                    "category": msg.get("category", "status"),
                    "content": msg.get("content", ""),
                    "tags": msg.get("tags", []),
                    "source": "daemon",
                }
                parsed.append(parsed_msg)
            except (KeyError, TypeError):
                continue

        return parsed

    def _parse_recovery_messages(self, messages: list[dict]) -> list[dict[str, Any]]:
        """Parse recovery action messages.

        Args:
            messages: Raw recovery messages

        Returns:
            Parsed recovery messages
        """
        parsed = []
        for msg in messages:
            try:
                if "recovery" in msg.get("tags", []) or "recovery" in msg.get("content", "").lower():
                    parsed_msg = {
                        "id": msg.get("id", "unknown"),
                        "timestamp": msg.get("timestamp", "unknown"),
                        "action_required": self._extract_recovery_action(msg.get("content", "")),
                        "priority": msg.get("priority", "normal"),
                        "content": msg.get("content", ""),
                    }
                    parsed.append(parsed_msg)
            except (KeyError, TypeError):
                continue

        return parsed

    def _extract_recovery_action(self, content: str) -> str:
        """Extract specific recovery action from message content.

        Args:
            content: Message content

        Returns:
            Extracted recovery action or "review_required"
        """
        content_lower = content.lower()
        if "restart" in content_lower:
            return "restart_required"
        elif "kill" in content_lower:
            return "kill_required"
        elif "spawn" in content_lower:
            return "spawn_required"
        elif "notify" in content_lower:
            return "notification_required"
        else:
            return "review_required"
