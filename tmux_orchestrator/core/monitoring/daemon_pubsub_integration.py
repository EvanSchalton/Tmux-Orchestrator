"""Daemon-side pubsub integration for structured messaging.

This module provides utilities for the monitoring daemon to send structured
notifications through the pubsub messaging system instead of direct tmux commands.
"""

import asyncio
import json
import subprocess
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class MessagePriority(Enum):
    """Message priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class MessageCategory(Enum):
    """Message categories for daemon notifications."""

    HEALTH = "health"
    RECOVERY = "recovery"
    STATUS = "status"
    TASK = "task"
    ESCALATION = "escalation"


class DaemonPubsubIntegration:
    """Handles daemon integration with pubsub messaging system."""

    def __init__(self):
        """Initialize daemon pubsub integration."""
        self.source_id = "daemon-monitor"

    async def send_health_alert(
        self,
        agent_target: str,
        issue_type: str,
        details: Dict[str, Any],
        priority: MessagePriority = MessagePriority.HIGH,
    ) -> bool:
        """Send structured health alert through pubsub.

        Args:
            agent_target: Target agent (e.g., "backend-dev:2")
            issue_type: Type of issue (idle, crashed, unresponsive)
            details: Additional context about the issue
            priority: Message priority level

        Returns:
            True if message sent successfully
        """
        # Build structured message
        message = self._build_message(
            msg_type="notification",
            category=MessageCategory.HEALTH,
            priority=priority,
            subject=f"Agent {issue_type.title()} Alert: {agent_target}",
            body=self._format_health_issue(agent_target, issue_type, details),
            context={
                "agent": agent_target,
                "issue_type": issue_type,
                "timestamp": datetime.now().isoformat(),
                **details,
            },
            actions=self._suggest_health_actions(issue_type),
            tags=["monitoring", "health", issue_type],
            requires_ack=priority in [MessagePriority.CRITICAL, MessagePriority.HIGH],
        )

        # Determine target PM
        pm_target = self._get_pm_target(agent_target)

        # Send via pubsub
        return await self._send_pubsub_message(pm_target, message, priority)

    async def send_recovery_notification(
        self,
        target: str,
        recovery_type: str,
        recovery_details: Dict[str, Any],
    ) -> bool:
        """Send recovery action notification.

        Args:
            target: Recovery target (agent or PM)
            recovery_type: Type of recovery (restart, spawn, replace)
            recovery_details: Details about recovery action

        Returns:
            True if message sent successfully
        """
        message = self._build_message(
            msg_type="notification",
            category=MessageCategory.RECOVERY,
            priority=MessagePriority.CRITICAL,
            subject=f"{recovery_type.title()} Recovery: {target}",
            body=self._format_recovery_message(target, recovery_type, recovery_details),
            context={
                "target": target,
                "recovery_type": recovery_type,
                "timestamp": datetime.now().isoformat(),
                **recovery_details,
            },
            actions=["verify", "monitor"],
            tags=["monitoring", "recovery", recovery_type],
            requires_ack=True,
        )

        # For recovery, notify both PM and orchestrator
        pm_target = self._get_pm_target(target)
        orchestrator_target = self._get_orchestrator_target(target)

        # Send to PM
        pm_result = await self._send_pubsub_message(pm_target, message, MessagePriority.CRITICAL)

        # Send to orchestrator if different from PM
        if orchestrator_target != pm_target:
            await self._send_pubsub_message(orchestrator_target, message, MessagePriority.CRITICAL)

        return pm_result

    async def send_status_update(
        self,
        session: str,
        status_type: str,
        status_data: Dict[str, Any],
    ) -> bool:
        """Send periodic status update.

        Args:
            session: Session name
            status_type: Type of status (team_health, monitoring_summary)
            status_data: Status information

        Returns:
            True if message sent successfully
        """
        message = self._build_message(
            msg_type="notification",
            category=MessageCategory.STATUS,
            priority=MessagePriority.LOW,
            subject=f"Status Update: {status_type.replace('_', ' ').title()}",
            body=self._format_status_message(status_type, status_data),
            context={
                "session": session,
                "status_type": status_type,
                "timestamp": datetime.now().isoformat(),
                **status_data,
            },
            tags=["monitoring", "status", status_type],
            requires_ack=False,
        )

        pm_target = f"{session}:1"
        return await self._send_pubsub_message(pm_target, message, MessagePriority.LOW)

    async def request_pm_action(
        self,
        pm_target: str,
        action_type: str,
        action_context: Dict[str, Any],
    ) -> bool:
        """Request specific action from PM.

        Args:
            pm_target: Target PM
            action_type: Type of action requested
            action_context: Context for the action

        Returns:
            True if request sent successfully
        """
        message = self._build_message(
            msg_type="request",
            category=MessageCategory.TASK,
            priority=MessagePriority.HIGH,
            subject=f"Action Required: {action_type.replace('_', ' ').title()}",
            body=self._format_action_request(action_type, action_context),
            context={
                "action_type": action_type,
                "timestamp": datetime.now().isoformat(),
                **action_context,
            },
            tags=["monitoring", "request", action_type],
            requires_ack=True,
        )

        return await self._send_pubsub_message(pm_target, message, MessagePriority.HIGH)

    def _build_message(
        self,
        msg_type: str,
        category: MessageCategory,
        priority: MessagePriority,
        subject: str,
        body: str,
        context: Dict[str, Any],
        tags: List[str] = None,
        actions: List[str] = None,
        requires_ack: bool = False,
    ) -> Dict[str, Any]:
        """Build structured message format.

        Args:
            msg_type: Message type (notification, request, response)
            category: Message category
            priority: Message priority
            subject: Brief subject line
            body: Detailed message body
            context: Additional context data
            tags: Message tags for filtering
            actions: Suggested actions
            requires_ack: Whether acknowledgment is required

        Returns:
            Structured message dictionary
        """
        message_id = f"daemon-{uuid4().hex[:8]}"

        return {
            "id": message_id,
            "timestamp": datetime.now().isoformat(),
            "source": {
                "type": "daemon",
                "identifier": self.source_id,
            },
            "message": {
                "type": msg_type,
                "category": category.value,
                "priority": priority.value,
                "content": {
                    "subject": subject,
                    "body": body,
                    "context": context,
                    "actions": [{"id": action, "label": action.replace("_", " ").title()} for action in (actions or [])],
                },
            },
            "metadata": {
                "tags": tags or [],
                "ttl": 3600,  # 1 hour TTL
                "requires_ack": requires_ack,
            },
        }

    async def _send_pubsub_message(
        self,
        target: str,
        message: Dict[str, Any],
        priority: MessagePriority,
    ) -> bool:
        """Send message through pubsub system.

        Args:
            target: Target session:window
            message: Structured message
            priority: Message priority

        Returns:
            True if sent successfully
        """
        try:
            # Serialize message
            message_json = json.dumps(message)

            # Build tmux-orc publish command
            cmd = [
                "tmux-orc",
                "pubsub",
                "publish",
                message_json,
                "--target",
                target,
                "--priority",
                priority.value,
            ]

            # Add tags
            for tag in message["metadata"]["tags"]:
                cmd.extend(["--tag", tag])

            # Send via subprocess (async would require daemon client)
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return "queued" in result.stdout

        except (subprocess.CalledProcessError, json.JSONEncodeError) as e:
            print(f"Error sending pubsub message: {e}")
            return False

    def _get_pm_target(self, agent_target: str) -> str:
        """Get PM target for given agent.

        Args:
            agent_target: Agent session:window

        Returns:
            PM target session:window
        """
        session = agent_target.split(":")[0]
        return f"{session}:1"  # Standard PM window

    def _get_orchestrator_target(self, target: str) -> str:
        """Get orchestrator target for notifications.

        Args:
            target: Original target

        Returns:
            Orchestrator target
        """
        session = target.split(":")[0]
        # Check if this is the main orchestrator session
        if session in ["orchestrator", "main"]:
            return f"{session}:0"
        # Otherwise, PM is the escalation point
        return self._get_pm_target(target)

    def _format_health_issue(
        self,
        agent: str,
        issue_type: str,
        details: Dict[str, Any],
    ) -> str:
        """Format health issue message body.

        Args:
            agent: Agent identifier
            issue_type: Type of health issue
            details: Issue details

        Returns:
            Formatted message body
        """
        if issue_type == "idle":
            duration = details.get("idle_duration", 0) // 60
            return f"Agent {agent} has been idle for {duration} minutes. Last activity: {details.get('last_activity', 'Unknown')}"
        elif issue_type == "crashed":
            return f"Agent {agent} has crashed. Claude interface not responding."
        elif issue_type == "unresponsive":
            return f"Agent {agent} is unresponsive to health checks."
        else:
            return f"Agent {agent} reported {issue_type}: {details}"

    def _format_recovery_message(
        self,
        target: str,
        recovery_type: str,
        details: Dict[str, Any],
    ) -> str:
        """Format recovery notification message.

        Args:
            target: Recovery target
            recovery_type: Type of recovery
            details: Recovery details

        Returns:
            Formatted message body
        """
        if recovery_type == "pm_crash":
            return f"PM in {target} crashed. Spawning replacement PM. Team agents notified."
        elif recovery_type == "agent_restart":
            return f"Restarted unresponsive agent {target}. Verify agent is operational."
        elif recovery_type == "session_recovery":
            return f"Recovered session {target} after system issue. All agents being checked."
        else:
            return f"Recovery action {recovery_type} completed for {target}"

    def _format_status_message(
        self,
        status_type: str,
        data: Dict[str, Any],
    ) -> str:
        """Format status update message.

        Args:
            status_type: Type of status
            data: Status data

        Returns:
            Formatted message body
        """
        if status_type == "team_health":
            active = data.get("active_agents", 0)
            idle = data.get("idle_agents", 0)
            total = active + idle
            return f"Team Status: {active}/{total} agents active, {idle} idle. Monitoring stable."
        elif status_type == "monitoring_summary":
            return f"Monitoring Summary: Checked {data.get('agents_checked', 0)} agents, {data.get('issues_found', 0)} issues found."
        else:
            return f"Status Update: {status_type} - {data}"

    def _format_action_request(
        self,
        action_type: str,
        context: Dict[str, Any],
    ) -> str:
        """Format action request message.

        Args:
            action_type: Type of action
            context: Action context

        Returns:
            Formatted message body
        """
        if action_type == "investigate_agent":
            return f"Please investigate {context.get('agent', 'unknown')} - {context.get('reason', 'unspecified issue')}"
        elif action_type == "redistribute_tasks":
            return f"Agent {context.get('failed_agent', 'unknown')} failed. Please redistribute tasks to active agents."
        else:
            return f"Action required: {action_type} - {context}"

    def _suggest_health_actions(self, issue_type: str) -> List[str]:
        """Suggest appropriate actions for health issues.

        Args:
            issue_type: Type of health issue

        Returns:
            List of suggested actions
        """
        if issue_type == "idle":
            return ["restart", "investigate", "reassign_tasks"]
        elif issue_type == "crashed":
            return ["restart", "check_logs", "replace_agent"]
        elif issue_type == "unresponsive":
            return ["force_restart", "investigate", "escalate"]
        else:
            return ["investigate", "monitor"]

    def _determine_priority(self, issue_type: str, duration: Optional[int] = None) -> MessagePriority:
        """Determine message priority based on issue type and duration.

        Args:
            issue_type: Type of issue
            duration: Duration in seconds (for idle issues)

        Returns:
            Appropriate message priority
        """
        if issue_type == "crashed":
            return MessagePriority.CRITICAL
        elif issue_type == "unresponsive":
            return MessagePriority.HIGH
        elif issue_type == "idle":
            if duration and duration > 1800:  # 30 minutes
                return MessagePriority.HIGH
            else:
                return MessagePriority.NORMAL
        else:
            return MessagePriority.NORMAL