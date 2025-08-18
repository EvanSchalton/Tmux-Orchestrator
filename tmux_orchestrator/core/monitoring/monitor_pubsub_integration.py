"""
Monitor daemon integration with pubsub messaging system.

This module provides the daemon-side integration for publishing monitoring
notifications through the pubsub system with proper priorities and categories.
"""

import json
import logging
import subprocess
from datetime import datetime

from tmux_orchestrator.core.communication.pm_pubsub_integration import MessageCategory, MessagePriority


class MonitorPubsubIntegration:
    """Handles monitor daemon integration with pubsub messaging."""

    def __init__(self, session: str = "monitoring-daemon", logger: logging.Logger | None = None):
        """Initialize monitor pubsub integration.

        Args:
            session: Monitor daemon session identifier
            logger: Optional logger instance
        """
        self.session = session
        self.logger = logger or logging.getLogger(__name__)
        self._message_queue: list[dict] = []
        self._batch_threshold = 10  # Batch low priority messages

    def publish_agent_crash(
        self, agent: str, error_type: str, session_name: str, requires_restart: bool = True
    ) -> bool:
        """Publish agent crash notification with critical priority.

        Args:
            agent: Agent identifier (e.g., "backend-dev:2")
            error_type: Type of crash detected
            session_name: Session containing the agent
            requires_restart: Whether agent needs restart

        Returns:
            Success status
        """
        message = self._build_structured_message(
            message_type="notification",
            category=MessageCategory.HEALTH,
            priority=MessagePriority.CRITICAL,
            subject=f"Agent Crash Detected: {agent}",
            body=f"Agent {agent} crashed with error: {error_type}",
            context={
                "agent": agent,
                "issue_type": "crashed",
                "error_type": error_type,
                "session": session_name,
                "requires_restart": requires_restart,
                "timestamp": datetime.now().isoformat(),
            },
            requires_ack=True,
        )

        return self._publish_message(
            target=self._get_pm_target(session_name),
            message=json.dumps(message),
            priority=MessagePriority.CRITICAL.value,
            tags=["monitoring", "health", "crash", "critical"],
        )

    def publish_agent_idle(
        self, agent: str, idle_duration: int, session_name: str, idle_type: str = "no_activity"
    ) -> bool:
        """Publish agent idle notification with appropriate priority.

        Args:
            agent: Agent identifier
            idle_duration: Seconds agent has been idle
            session_name: Session containing the agent
            idle_type: Type of idle state

        Returns:
            Success status
        """
        # Determine priority based on idle duration
        if idle_duration > 1800:  # 30 minutes
            priority = MessagePriority.HIGH
        elif idle_duration > 900:  # 15 minutes
            priority = MessagePriority.NORMAL
        else:
            priority = MessagePriority.LOW

        message = self._build_structured_message(
            message_type="notification",
            category=MessageCategory.HEALTH,
            priority=priority,
            subject=f"Agent Idle Alert: {agent}",
            body=f"Agent {agent} has been idle for {idle_duration//60} minutes",
            context={
                "agent": agent,
                "issue_type": "idle",
                "idle_type": idle_type,
                "idle_duration": idle_duration,
                "session": session_name,
                "timestamp": datetime.now().isoformat(),
            },
            requires_ack=(priority in [MessagePriority.HIGH, MessagePriority.CRITICAL]),
        )

        # Batch low priority messages
        if priority == MessagePriority.LOW:
            self._queue_message(message, agent, session_name)
            return True
        else:
            return self._publish_message(
                target=self._get_pm_target(session_name),
                message=json.dumps(message),
                priority=priority.value,
                tags=["monitoring", "health", "idle", priority.value],
            )

    def publish_recovery_needed(
        self, agent: str, issue: str, session_name: str, recovery_type: str = "restart"
    ) -> bool:
        """Publish recovery needed notification with high priority.

        Args:
            agent: Agent identifier
            issue: Description of the issue
            session_name: Session containing the agent
            recovery_type: Type of recovery needed

        Returns:
            Success status
        """
        message = self._build_structured_message(
            message_type="request",
            category=MessageCategory.RECOVERY,
            priority=MessagePriority.HIGH,
            subject=f"Recovery Action Required: {agent}",
            body=f"Agent {agent} requires {recovery_type} due to: {issue}",
            context={
                "agent": agent,
                "issue": issue,
                "recovery_type": recovery_type,
                "session": session_name,
                "action_required": recovery_type,
                "timestamp": datetime.now().isoformat(),
            },
            requires_ack=True,
        )

        return self._publish_message(
            target=self._get_pm_target(session_name),
            message=json.dumps(message),
            priority=MessagePriority.HIGH.value,
            tags=["monitoring", "recovery", "action_required", "high"],
        )

    def publish_fresh_agent(self, agent: str, session_name: str, window_name: str) -> bool:
        """Publish fresh agent notification requiring briefing.

        Args:
            agent: Agent identifier
            session_name: Session containing the agent
            window_name: Window name for the agent

        Returns:
            Success status
        """
        message = self._build_structured_message(
            message_type="notification",
            category=MessageCategory.STATUS,
            priority=MessagePriority.NORMAL,
            subject=f"Fresh Agent Ready: {agent}",
            body=f"New agent {agent} is ready for briefing in {window_name}",
            context={
                "agent": agent,
                "session": session_name,
                "window_name": window_name,
                "status": "fresh",
                "needs_briefing": True,
                "timestamp": datetime.now().isoformat(),
            },
            requires_ack=False,
        )

        return self._publish_message(
            target=self._get_pm_target(session_name),
            message=json.dumps(message),
            priority=MessagePriority.NORMAL.value,
            tags=["monitoring", "status", "fresh_agent", "normal"],
        )

    def publish_team_idle(self, session_name: str, idle_agents: list[str], total_agents: int) -> bool:
        """Publish team-wide idle notification with high priority.

        Args:
            session_name: Session with idle team
            idle_agents: List of idle agent identifiers
            total_agents: Total number of agents in team

        Returns:
            Success status
        """
        idle_percentage = (len(idle_agents) / total_agents) * 100 if total_agents > 0 else 0

        message = self._build_structured_message(
            message_type="escalation",
            category=MessageCategory.ESCALATION,
            priority=MessagePriority.HIGH,
            subject=f"Team Idle Alert: {session_name}",
            body=f"{len(idle_agents)} of {total_agents} agents idle ({idle_percentage:.0f}%)",
            context={
                "session": session_name,
                "idle_agents": idle_agents,
                "total_agents": total_agents,
                "idle_percentage": idle_percentage,
                "timestamp": datetime.now().isoformat(),
            },
            requires_ack=True,
        )

        return self._publish_message(
            target=self._get_pm_target(session_name),
            message=json.dumps(message),
            priority=MessagePriority.HIGH.value,
            tags=["monitoring", "escalation", "team_idle", "high"],
        )

    def publish_rate_limit(
        self, session_name: str, reset_time: datetime | None = None, affected_agents: list[str | None] = None
    ) -> bool:
        """Publish rate limit notification with critical priority.

        Args:
            session_name: Affected session
            reset_time: When rate limit resets
            affected_agents: List of affected agents

        Returns:
            Success status
        """
        message = self._build_structured_message(
            message_type="escalation",
            category=MessageCategory.ESCALATION,
            priority=MessagePriority.CRITICAL,
            subject="Rate Limit Detected",
            body="Claude API rate limit reached. Agents may be unresponsive.",
            context={
                "session": session_name,
                "rate_limit": True,
                "reset_time": reset_time.isoformat() if reset_time else None,
                "affected_agents": affected_agents or [],
                "timestamp": datetime.now().isoformat(),
            },
            requires_ack=True,
        )

        return self._publish_message(
            target=self._get_pm_target(session_name),
            message=json.dumps(message),
            priority=MessagePriority.CRITICAL.value,
            tags=["monitoring", "escalation", "rate_limit", "critical"],
        )

    def publish_monitoring_report(
        self, session_name: str, summary: dict[str, int], issues: list[dict | None] = None
    ) -> bool:
        """Publish periodic monitoring status report.

        Args:
            session_name: Session being monitored
            summary: Status summary (active, idle, crashed counts)
            issues: List of current issues

        Returns:
            Success status
        """
        message = self._build_structured_message(
            message_type="report",
            category=MessageCategory.STATUS,
            priority=MessagePriority.LOW,
            subject=f"Monitoring Report: {session_name}",
            body=f"Active: {summary.get('active', 0)}, Idle: {summary.get('idle', 0)}, Issues: {len(issues or [])}",
            context={
                "session": session_name,
                "summary": summary,
                "issues": issues or [],
                "timestamp": datetime.now().isoformat(),
            },
            requires_ack=False,
        )

        # Always batch low priority reports
        self._queue_message(message, "monitoring", session_name)
        return True

    def flush_message_queue(self) -> int:
        """Flush any queued low-priority messages.

        Returns:
            Number of messages flushed
        """
        if not self._message_queue:
            return 0

        # Group messages by target
        messages_by_target: dict[str, list[dict]] = {}
        for msg_info in self._message_queue:
            target = msg_info["target"]
            if target not in messages_by_target:
                messages_by_target[target] = []
            messages_by_target[target].append(msg_info["message"])

        flushed = 0
        for target, messages in messages_by_target.items():
            # Create batch message
            batch_message = {
                "id": f"monitor-batch-{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "source": {"type": "monitoring-daemon", "identifier": self.session},
                "message": {
                    "type": "batch_report",
                    "category": MessageCategory.STATUS.value,
                    "priority": MessagePriority.LOW.value,
                    "content": {
                        "subject": f"Batched Monitoring Updates ({len(messages)} messages)",
                        "body": "Low priority monitoring updates batched for efficiency",
                        "messages": messages,
                    },
                },
                "metadata": {"batch_size": len(messages), "tags": ["monitoring", "batch", "low_priority"]},
            }

            if self._publish_message(
                target=target,
                message=json.dumps(batch_message),
                priority=MessagePriority.LOW.value,
                tags=["monitoring", "batch", "status"],
            ):
                flushed += len(messages)

        self._message_queue.clear()
        return flushed

    def _build_structured_message(
        self,
        message_type: str,
        category: MessageCategory,
        priority: MessagePriority,
        subject: str,
        body: str,
        context: dict,
        requires_ack: bool = False,
    ) -> dict:
        """Build a structured message following the defined format.

        Args:
            message_type: Type of message (notification, request, etc.)
            category: Message category
            priority: Message priority
            subject: Message subject
            body: Message body
            context: Additional context
            requires_ack: Whether acknowledgment is required

        Returns:
            Structured message dict
        """
        return {
            "id": f"monitor-{message_type}-{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "source": {"type": "monitoring-daemon", "identifier": self.session},
            "message": {
                "type": message_type,
                "category": category.value,
                "priority": priority.value,
                "content": {"subject": subject, "body": body, "context": context},
            },
            "metadata": {
                "requires_ack": requires_ack,
                "tags": ["monitoring", category.value, priority.value],
                "correlation_id": context.get("session", "unknown"),
            },
        }

    def _publish_message(self, target: str, message: str, priority: str, tags: list[str]) -> bool:
        """Publish message through pubsub system.

        Args:
            target: Target for message (PM session:window)
            message: Message content (JSON string)
            priority: Message priority level
            tags: Message tags

        Returns:
            Success status
        """
        try:
            cmd = ["tmux-orc", "pubsub", "publish", message, "--target", target, "--priority", priority]

            for tag in tags:
                cmd.extend(["--tag", tag])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            self.logger.debug(f"Published {priority} message to {target}")
            return "queued" in result.stdout.lower()

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to publish message: {e}")
            self.logger.error(f"stderr: {e.stderr}")
            return False

    def _queue_message(self, message: dict, agent: str, session_name: str) -> None:
        """Queue low-priority message for batching.

        Args:
            message: Message to queue
            agent: Agent identifier
            session_name: Session name
        """
        self._message_queue.append(
            {
                "message": message,
                "agent": agent,
                "target": self._get_pm_target(session_name),
                "timestamp": datetime.now(),
            }
        )

        # Auto-flush if threshold reached
        if len(self._message_queue) >= self._batch_threshold:
            self.logger.info(f"Auto-flushing {len(self._message_queue)} queued messages")
            self.flush_message_queue()

    def _get_pm_target(self, session_name: str) -> str:
        """Get PM target for a session.

        Args:
            session_name: Session name

        Returns:
            PM target identifier (assumes PM is in window 0)
        """
        # In a real implementation, would discover actual PM window
        # For now, assume PM is always in window 0
        return f"{session_name}:0"
