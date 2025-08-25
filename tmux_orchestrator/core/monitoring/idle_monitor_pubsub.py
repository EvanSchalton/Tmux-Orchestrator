"""
Enhanced IdleMonitor with pubsub integration.

This module provides an updated IdleMonitor that uses the pubsub messaging
system for notifications while maintaining backward compatibility.
"""

import logging
import time
from datetime import datetime
from typing import Any

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

from .monitor_pubsub_integration import MonitorPubsubIntegration


class IdleMonitorWithPubsub:
    """Enhanced idle monitor using pubsub for notifications."""

    def __init__(self, tmux: TMUXManager, config: Config, logger: logging.Logger):
        """Initialize the idle monitor with pubsub support.

        Args:
            tmux: TMUX manager instance
            config: Configuration object
            logger: Logger instance
        """
        self.tmux = tmux
        self.config = config
        self.logger = logger

        # Initialize pubsub integration
        self.pubsub = MonitorPubsubIntegration(session="idle-monitor", logger=logger)

        # Tracking state
        self._agent_idle_start: dict[str, float] = {}
        self._notified_agents: set[str] = set()
        self._fresh_agents: set[str] = set()
        self._last_flush_time = time.time()
        self._flush_interval = 60  # Flush queued messages every minute

    def check_agent_idle(self, agent: str, content: str, session_name: str, has_claude_interface: bool) -> str | None:
        """Check if agent is idle and send appropriate notifications.

        Args:
            agent: Agent identifier (session:window)
            content: Current pane content
            session_name: Session containing the agent
            has_claude_interface: Whether Claude interface is present

        Returns:
            Idle status message if idle, None otherwise
        """
        current_time = time.time()

        # Check for various idle conditions
        is_idle, idle_type = self._detect_idle_state(content, has_claude_interface)

        if is_idle:
            # Track idle start time
            if agent not in self._agent_idle_start:
                self._agent_idle_start[agent] = current_time
                self.logger.info(f"Agent {agent} entered idle state: {idle_type}")

            idle_duration = int(current_time - self._agent_idle_start[agent])

            # Send notification if threshold reached and not already notified
            if idle_duration > 300 and agent not in self._notified_agents:  # 5 minutes
                self._send_idle_notification(agent, idle_duration, session_name, idle_type)
                self._notified_agents.add(agent)

            return f"Idle ({idle_type}) for {idle_duration}s"

        else:
            # Agent is active, reset tracking
            if agent in self._agent_idle_start:
                idle_duration = int(current_time - self._agent_idle_start[agent])
                self.logger.info(f"Agent {agent} became active after {idle_duration}s")
                del self._agent_idle_start[agent]
                self._notified_agents.discard(agent)

            return None

    def check_fresh_agent(self, agent: str, content: str, session_name: str, window_name: str) -> bool:
        """Check if agent is fresh and needs briefing.

        Args:
            agent: Agent identifier
            content: Current pane content
            session_name: Session containing the agent
            window_name: Window name

        Returns:
            True if fresh agent detected
        """
        # Check for fresh agent indicators
        is_fresh = (
            "Welcome to Claude" in content
            or "I'll help you" in content
            and len(content.split("\n")) < 20
            or content.strip().endswith("Human:")
            and len(content.split("\n")) < 10
        )

        if is_fresh and agent not in self._fresh_agents:
            self.logger.info(f"Fresh agent detected: {agent}")
            self.pubsub.publish_fresh_agent(agent, session_name, window_name)
            self._fresh_agents.add(agent)
            return True

        elif not is_fresh and agent in self._fresh_agents:
            # Agent is no longer fresh
            self._fresh_agents.discard(agent)

        return False

    def check_agent_crash(self, agent: str, content: str, session_name: str) -> str | None:
        """Check if agent has crashed and send notification.

        Args:
            agent: Agent identifier
            content: Current pane content
            session_name: Session containing the agent

        Returns:
            Crash type if detected, None otherwise
        """
        crash_indicators = {
            "Segmentation fault": "segfault",
            "ERROR": "error",
            "FATAL": "fatal",
            "Traceback": "python_error",
            "panic:": "panic",
            "core dumped": "core_dump",
        }

        for indicator, crash_type in crash_indicators.items():
            if indicator in content:
                self.logger.warning(f"Crash detected in {agent}: {crash_type}")
                self.pubsub.publish_agent_crash(agent, crash_type, session_name, requires_restart=True)
                return crash_type

        return None

    def check_recovery_needed(self, agent: str, session_name: str, issue: str) -> None:
        """Check if agent needs recovery and send notification.

        Args:
            agent: Agent identifier
            session_name: Session containing the agent
            issue: Description of the issue
        """
        self.logger.warning(f"Recovery needed for {agent}: {issue}")
        self.pubsub.publish_recovery_needed(agent, issue, session_name, recovery_type="restart")

    def check_team_idle(self, session_name: str, agents: list[str], idle_agents: list[str]) -> None:
        """Check if team is idle and send escalation.

        Args:
            session_name: Session name
            agents: All agents in team
            idle_agents: List of idle agents
        """
        if len(idle_agents) >= len(agents) * 0.5:  # 50% or more idle
            self.logger.warning(f"Team idle detected in {session_name}")
            self.pubsub.publish_team_idle(session_name, idle_agents, len(agents))

    def send_monitoring_report(self, session_name: str, agent_statuses: dict[str, str]) -> None:
        """Send periodic monitoring report.

        Args:
            session_name: Session name
            agent_statuses: dict of agent statuses
        """
        summary = {
            "active": sum(1 for s in agent_statuses.values() if s == "active"),
            "idle": sum(1 for s in agent_statuses.values() if "idle" in s.lower()),
            "crashed": sum(1 for s in agent_statuses.values() if "crash" in s.lower()),
            "total": len(agent_statuses),
        }

        issues = []
        for agent, status in agent_statuses.items():
            if "crash" in status.lower() or "error" in status.lower():
                issues.append({"agent": agent, "status": status, "severity": "high"})

        # Cast issues to expected type for pubsub integration
        issues_typed: list[dict[Any, Any] | None] | None = issues  # type: ignore[assignment]
        self.pubsub.publish_monitoring_report(session_name, summary, issues_typed)

    def flush_notifications(self) -> None:
        """Flush any queued notifications."""
        current_time = time.time()
        if current_time - self._last_flush_time >= self._flush_interval:
            flushed = self.pubsub.flush_message_queue()
            if flushed > 0:
                self.logger.info(f"Flushed {flushed} queued messages")
            self._last_flush_time = current_time

    def _detect_idle_state(self, content: str, has_claude_interface: bool) -> tuple[bool, str]:
        """Detect if agent is idle and determine idle type.

        Args:
            content: Pane content
            has_claude_interface: Whether Claude interface is present

        Returns:
            Tuple of (is_idle, idle_type)
        """
        # No Claude interface = definitely idle
        if not has_claude_interface:
            return True, "no_claude_interface"

        # Check for waiting state
        if content.strip().endswith("Human:"):
            return True, "waiting_for_input"

        # Check for common idle patterns
        idle_patterns = [
            ("Thinking...", "thinking"),
            ("Please wait", "waiting"),
            ("Loading", "loading"),
            ("Press any key to continue", "paused"),
        ]

        for pattern, idle_type in idle_patterns:
            if pattern in content:
                return True, idle_type

        # Check for no recent activity
        lines = content.split("\n")
        if len(lines) > 0:
            # Simple heuristic: if last line hasn't changed in a while
            # (would need to track this across calls in real implementation)
            last_line = lines[-1].strip()
            if last_line in ["Human:", "Assistant:", ""]:
                return True, "no_activity"

        return False, ""

    def _send_idle_notification(self, agent: str, idle_duration: int, session_name: str, idle_type: str) -> None:
        """Send idle notification through pubsub.

        Args:
            agent: Agent identifier
            idle_duration: Seconds agent has been idle
            session_name: Session name
            idle_type: Type of idle state
        """
        self.pubsub.publish_agent_idle(agent, idle_duration, session_name, idle_type)

    def handle_rate_limit(self, session_name: str, reset_time: datetime | None = None) -> None:
        """Handle rate limit detection.

        Args:
            session_name: Affected session
            reset_time: When rate limit resets
        """
        # Get list of agents in session
        agents = []
        try:
            windows = self.tmux.list_windows(session_name)
            agents = [f"{session_name}:{w['index']}" for w in windows]
        except Exception as e:
            self.logger.error(f"Failed to list agents: {e}")

        # Cast agents to expected type
        agents_typed: list[str | None] | None = agents  # type: ignore[assignment]
        self.pubsub.publish_rate_limit(session_name, reset_time, agents_typed)


# Utility functions for integration with existing monitor


def create_pubsub_idle_monitor(tmux: TMUXManager, config: Config, logger: logging.Logger) -> IdleMonitorWithPubsub:
    """Factory function to create pubsub-enabled idle monitor.

    Args:
        tmux: TMUX manager instance
        config: Configuration object
        logger: Logger instance

    Returns:
        IdleMonitorWithPubsub instance
    """
    return IdleMonitorWithPubsub(tmux, config, logger)


def migrate_to_pubsub_notifications(existing_monitor) -> None:
    """Helper to migrate existing monitor to use pubsub.

    Args:
        existing_monitor: Existing monitor instance to migrate
    """
    # This would contain logic to seamlessly migrate an existing
    # monitor instance to use pubsub notifications
    # Implementation depends on the existing monitor structure
    pass
