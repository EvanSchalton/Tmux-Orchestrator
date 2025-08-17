"""PM-side integration for pubsub daemon coordination.

This module provides utilities for Project Managers to consume and respond to
daemon notifications through the pubsub messaging system.
"""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from tmux_orchestrator.utils.tmux import TMUXManager


class PMPubsubIntegration:
    """Handles PM integration with pubsub messaging system."""

    def __init__(self, session: str = "pm:0"):
        """Initialize PM pubsub integration.

        Args:
            session: PM session identifier (default: pm:0)
        """
        self.session = session
        self.tmux = TMUXManager()
        self.message_store = Path.home() / ".tmux-orchestrator" / "messages"

    def get_daemon_notifications(self, since_minutes: int = 30) -> List[Dict[str, Any]]:
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

    def get_management_broadcasts(self, priority: str = "high") -> List[Dict[str, Any]]:
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

    def check_for_recovery_actions(self) -> List[Dict[str, Any]]:
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
        ack_message = (
            f"PM ACK: {notification_id} - {action_taken} " f"by {self.session} at {datetime.now().isoformat()}"
        )

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

    def monitor_pubsub_health(self) -> Dict[str, Any]:
        """Check pubsub system health and message statistics.

        Returns:
            Dictionary with pubsub health information
        """
        try:
            result = subprocess.run(
                ["tmux-orc", "status", "--format", "json"], capture_output=True, text=True, check=True
            )

            if result.stdout:
                return json.loads(result.stdout)

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error checking pubsub health: {e}")

        return {}

    def _parse_daemon_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse and categorize daemon messages.

        Args:
            messages: Raw message list

        Returns:
            Parsed daemon notification messages
        """
        daemon_messages = []

        for msg in messages:
            # Look for daemon-related content in message text
            message_text = msg.get("message", "").lower()
            if any(keyword in message_text for keyword in ["daemon", "monitoring", "agent status", "health check"]):
                # Extract structured info from message
                parsed_msg = {
                    "id": msg.get("id"),
                    "timestamp": msg.get("timestamp"),
                    "priority": msg.get("priority"),
                    "tags": msg.get("tags", []),
                    "raw_message": msg.get("message"),
                    "sender": msg.get("sender", "unknown"),
                    "type": self._categorize_daemon_message(message_text),
                }
                daemon_messages.append(parsed_msg)

        return daemon_messages

    def _parse_recovery_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse recovery action messages.

        Args:
            messages: Raw message list

        Returns:
            Parsed recovery action messages
        """
        recovery_messages = []

        for msg in messages:
            if "recovery" in msg.get("tags", []) or "recovery" in msg.get("message", "").lower():
                parsed_msg = {
                    "id": msg.get("id"),
                    "timestamp": msg.get("timestamp"),
                    "priority": msg.get("priority"),
                    "action_required": True,
                    "message": msg.get("message"),
                    "recommended_response": self._suggest_recovery_response(msg.get("message", "")),
                }
                recovery_messages.append(parsed_msg)

        return recovery_messages

    def _categorize_daemon_message(self, message_text: str) -> str:
        """Categorize daemon message type based on content.

        Args:
            message_text: Message content

        Returns:
            Message category
        """
        if any(keyword in message_text for keyword in ["failed", "crashed", "down"]):
            return "failure"
        elif any(keyword in message_text for keyword in ["idle", "inactive"]):
            return "idle_alert"
        elif any(keyword in message_text for keyword in ["recovered", "restarted"]):
            return "recovery"
        elif any(keyword in message_text for keyword in ["health", "status"]):
            return "health_check"
        else:
            return "general"

    def _suggest_recovery_response(self, message: str) -> str:
        """Suggest appropriate recovery response based on message content.

        Args:
            message: Recovery message content

        Returns:
            Suggested response action
        """
        message_lower = message.lower()

        if "pm crash" in message_lower:
            return "Verify PM replacement spawned correctly, check session health"
        elif "agent idle" in message_lower:
            return "Send status request to agent, consider task reassignment"
        elif "timeout" in message_lower:
            return "Check agent responsiveness, may need restart"
        elif "failed" in message_lower:
            return "Investigate failure cause, restart if necessary"
        else:
            return "Review message details and take appropriate action"


def create_pm_monitoring_script() -> str:
    """Create a monitoring script for PMs to check daemon notifications.

    Returns:
        Path to created monitoring script
    """
    script_content = """#!/bin/bash
# PM Daemon Notification Monitor
# Run this periodically to check for daemon notifications

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PM_SESSION="${1:-pm:0}"

echo "🔍 Checking daemon notifications for $PM_SESSION..."

# Check for critical/high priority management messages
tmux-orc read --session "$PM_SESSION" --filter "CRITICAL\\|HIGH PRIORITY" --tail 5

echo -e "\\n📊 Pubsub System Status:"
tmux-orc status --format simple

echo -e "\\n🔄 Recent Recovery Actions:"
tmux-orc read --session "$PM_SESSION" --filter "recovery" --tail 3

echo -e "\\n✅ Monitoring check complete at $(date)"
"""

    script_path = Path("/tmp/pm_daemon_monitor.sh")
    script_path.write_text(script_content)
    script_path.chmod(0o755)

    return str(script_path)
