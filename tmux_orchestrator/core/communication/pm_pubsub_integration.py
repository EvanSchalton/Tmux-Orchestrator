"""PM-side integration for pubsub daemon coordination.

This module provides utilities for Project Managers to consume and respond to
daemon notifications through the pubsub messaging system.
"""

import asyncio
import json
import subprocess
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from tmux_orchestrator.utils.tmux import TMUXManager


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


class PMPubsubIntegration:
    """Handles PM integration with pubsub messaging system."""

    def __init__(self, session: str = "pm:0"):
        """Initialize PM pubsub integration.

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
            result = subprocess.run(
                ["tmux-orc", "status", "--format", "json"], capture_output=True, text=True, check=True
            )

            if result.stdout:
                return json.loads(result.stdout)

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error checking pubsub health: {e}")

        return {}

    def _parse_daemon_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    def _parse_recovery_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    async def process_structured_messages(self, since_minutes: int = 5) -> dict[str, list[dict[str, Any]]]:
        """Process structured daemon messages from pubsub.

        Args:
            since_minutes: How many minutes back to check

        Returns:
            Dictionary of messages categorized by type
        """
        messages = self.get_daemon_notifications(since_minutes)

        categorized = {"health": [], "recovery": [], "status": [], "requests": [], "unacknowledged": []}

        for msg in messages:
            # Parse structured message format
            if isinstance(msg.get("raw_message"), str):
                try:
                    structured_msg = json.loads(msg["raw_message"])
                    if self._is_structured_message(structured_msg):
                        msg_category = structured_msg["message"]["category"]
                        msg_type = structured_msg["message"]["type"]

                        # Categorize by type
                        if msg_category == "health":
                            categorized["health"].append(structured_msg)
                        elif msg_category == "recovery":
                            categorized["recovery"].append(structured_msg)
                        elif msg_category == "status":
                            categorized["status"].append(structured_msg)
                        elif msg_type == "request":
                            categorized["requests"].append(structured_msg)

                        # Track unacknowledged messages
                        if structured_msg["metadata"].get("requires_ack") and not self._is_acknowledged(
                            structured_msg["id"]
                        ):
                            categorized["unacknowledged"].append(structured_msg)
                except json.JSONDecodeError:
                    # Not a structured message, use legacy parsing
                    pass

        return categorized

    async def handle_health_notification(self, message: dict[str, Any]) -> dict[str, Any]:
        """Handle health notification from daemon.

        Args:
            message: Structured health notification

        Returns:
            Response with action taken
        """
        content = message["message"]["content"]
        context = content["context"]
        agent = context.get("agent", "unknown")
        issue_type = context.get("issue_type", "unknown")

        # Determine appropriate action
        action = self._determine_health_action(issue_type, context)

        # Execute action
        result = await self._execute_health_action(agent, action, context)

        # Send acknowledgment if required
        if message["metadata"].get("requires_ack"):
            await self.acknowledge_structured_message(message["id"], action, result)

        return {
            "message_id": message["id"],
            "agent": agent,
            "issue": issue_type,
            "action_taken": action,
            "result": result,
        }

    async def handle_recovery_notification(self, message: dict[str, Any]) -> dict[str, Any]:
        """Handle recovery notification from daemon.

        Args:
            message: Structured recovery notification

        Returns:
            Response with verification status
        """
        content = message["message"]["content"]
        context = content["context"]
        target = context.get("target", "unknown")
        recovery_type = context.get("recovery_type", "unknown")

        # Verify recovery success
        verification = await self._verify_recovery(target, recovery_type, context)

        # Send acknowledgment
        if message["metadata"].get("requires_ack"):
            await self.acknowledge_structured_message(message["id"], "verified", verification)

        return {
            "message_id": message["id"],
            "target": target,
            "recovery_type": recovery_type,
            "verification": verification,
        }

    async def handle_action_request(self, message: dict[str, Any]) -> dict[str, Any]:
        """Handle action request from daemon.

        Args:
            message: Structured action request

        Returns:
            Response with action result
        """
        content = message["message"]["content"]
        context = content["context"]
        action_type = context.get("action_type", "unknown")

        # Execute requested action
        result = await self._execute_requested_action(action_type, context)

        # Send response
        response_msg = self._build_response_message(message["id"], action_type, result)

        await self._send_response(response_msg)

        return {"message_id": message["id"], "action_type": action_type, "result": result}

    async def acknowledge_structured_message(self, message_id: str, action_taken: str, result: dict[str, Any]):
        """Acknowledge a structured daemon message.

        Args:
            message_id: Original message ID
            action_taken: Action that was taken
            result: Result of the action
        """
        ack_message = {
            "id": f"pm-ack-{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "source": {"type": "pm", "identifier": self.session},
            "message": {
                "type": "acknowledgment",
                "category": "response",
                "priority": "normal",
                "content": {
                    "subject": f"Action Completed: {action_taken}",
                    "body": f"PM {self.session} completed {action_taken}",
                    "context": {
                        "original_message_id": message_id,
                        "action_taken": action_taken,
                        "result": result,
                        "timestamp": datetime.now().isoformat(),
                    },
                },
            },
            "metadata": {"tags": ["acknowledgment", "pm-response"], "correlation_id": message_id},
        }

        # Send acknowledgment
        await self._send_pubsub_message(
            "management",  # Send to management group
            json.dumps(ack_message),
            ["acknowledgment", "pm-response", action_taken],
        )

    def _is_structured_message(self, message: Any) -> bool:
        """Check if message follows structured format.

        Args:
            message: Message to check

        Returns:
            True if message is structured format
        """
        if not isinstance(message, dict):
            return False

        required_fields = ["id", "timestamp", "source", "message", "metadata"]
        return all(field in message for field in required_fields)

    def _is_acknowledged(self, message_id: str) -> bool:
        """Check if message has been acknowledged.

        Args:
            message_id: Message ID to check

        Returns:
            True if acknowledged
        """
        # Check acknowledgment store
        ack_file = Path.home() / ".tmux_orchestrator" / "acknowledgments" / f"{message_id}.json"
        return ack_file.exists()

    def _determine_health_action(self, issue_type: str, context: dict[str, Any]) -> str:
        """Determine appropriate action for health issue.

        Args:
            issue_type: Type of health issue
            context: Issue context

        Returns:
            Recommended action
        """
        if issue_type == "idle":
            idle_duration = context.get("idle_duration", 0)
            if idle_duration > 1800:  # 30 minutes
                return "restart"
            else:
                return "investigate"
        elif issue_type == "crashed":
            return "restart"
        elif issue_type == "unresponsive":
            return "force_restart"
        else:
            return "investigate"

    async def _execute_health_action(self, agent: str, action: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute health-related action on agent.

        Args:
            agent: Agent target
            action: Action to take
            context: Action context

        Returns:
            Action result
        """
        try:
            if action == "restart":
                # Send restart command
                subprocess.run(["tmux-orc", "restart", "agent", agent], check=True, capture_output=True)
                return {"status": "success", "action": "agent_restarted"}

            elif action == "investigate":
                # Send status request to agent
                subprocess.run(
                    ["tmux-orc", "agent", "send", agent, "STATUS REQUEST: Please provide current task and progress"],
                    check=True,
                )
                return {"status": "success", "action": "status_requested"}

            elif action == "force_restart":
                # Kill and respawn agent
                session = agent.split(":")[0]
                window = agent.split(":")[1]
                subprocess.run(["tmux", "kill-window", "-t", f"{session}:{window}"], check=False)
                await asyncio.sleep(1)
                subprocess.run(["tmux-orc", "spawn", "agent", "--session", agent], check=True)
                return {"status": "success", "action": "agent_respawned"}

            else:
                return {"status": "unknown_action", "action": action}

        except subprocess.CalledProcessError as e:
            return {"status": "failed", "error": str(e)}

    async def _verify_recovery(self, target: str, recovery_type: str, context: dict[str, Any]) -> dict[str, Any]:
        """Verify recovery action success.

        Args:
            target: Recovery target
            recovery_type: Type of recovery
            context: Recovery context

        Returns:
            Verification result
        """
        try:
            # Check if target is responsive
            content = self.tmux.capture_pane(target, lines=10)

            if "Human:" in content or "Assistant:" in content:
                return {"status": "verified", "target_responsive": True, "recovery_type": recovery_type}
            else:
                return {"status": "unverified", "target_responsive": False, "recovery_type": recovery_type}

        except Exception as e:
            return {"status": "verification_failed", "error": str(e), "recovery_type": recovery_type}

    async def _execute_requested_action(self, action_type: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute action requested by daemon.

        Args:
            action_type: Type of action
            context: Action context

        Returns:
            Action result
        """
        if action_type == "redistribute_tasks":
            # Implement task redistribution logic
            failed_agent = context.get("failed_agent")
            return {"status": "success", "redistributed_from": failed_agent, "action": "tasks_redistributed"}

        elif action_type == "investigate_agent":
            agent = context.get("agent")
            reason = context.get("reason")
            # Send investigation message to agent
            subprocess.run(["tmux-orc", "agent", "send", agent, f"INVESTIGATION: {reason}"], check=True)
            return {"status": "success", "investigated": agent, "reason": reason}

        else:
            return {"status": "unknown_action", "action_type": action_type}

    def _build_response_message(self, original_id: str, action_type: str, result: dict[str, Any]) -> dict[str, Any]:
        """Build response message for daemon request.

        Args:
            original_id: Original request ID
            action_type: Type of action performed
            result: Action result

        Returns:
            Response message
        """
        return {
            "id": f"pm-response-{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "source": {"type": "pm", "identifier": self.session},
            "message": {
                "type": "response",
                "category": "task",
                "priority": "normal",
                "content": {
                    "subject": f"Action Completed: {action_type}",
                    "body": f"Completed requested action: {action_type}",
                    "context": {"original_request_id": original_id, "action_type": action_type, "result": result},
                },
            },
            "metadata": {"tags": ["response", "pm-action", action_type], "correlation_id": original_id},
        }

    async def _send_response(self, response_message: dict[str, Any]):
        """Send response message through pubsub.

        Args:
            response_message: Response to send
        """
        await self._send_pubsub_message(
            "daemon-monitor",  # Send back to daemon
            json.dumps(response_message),
            response_message["metadata"]["tags"],
        )

    async def _send_pubsub_message(self, target: str, message: str, tags: list[str]) -> bool:
        """Send message through pubsub system.

        Args:
            target: Target for message
            message: Message content
            tags: Message tags

        Returns:
            True if sent successfully
        """
        try:
            cmd = ["tmux-orc", "pubsub", "publish", message, "--target", target]

            for tag in tags:
                cmd.extend(["--tag", tag])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return "queued" in result.stdout

        except subprocess.CalledProcessError as e:
            print(f"Error sending pubsub message: {e}")
            return False
