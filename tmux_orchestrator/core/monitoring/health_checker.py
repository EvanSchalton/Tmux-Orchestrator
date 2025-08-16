"""Health checking component for monitoring agent health status."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitor_helpers import (
    _has_crash_indicators,
    _has_error_indicators,
    is_claude_interface_present,
)
from tmux_orchestrator.core.monitoring.types import MonitorComponent
from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class AgentHealthStatus:
    """Agent health status data."""

    target: str
    last_heartbeat: datetime
    last_response: datetime
    consecutive_failures: int
    is_responsive: bool
    last_content_hash: str
    status: str  # 'healthy', 'warning', 'critical', 'unresponsive'
    is_idle: bool
    activity_changes: int


class HealthChecker(MonitorComponent):
    """Monitors and checks agent health status."""

    def __init__(self, tmux: TMUXManager, config: Config, logger: logging.Logger):
        """Initialize the health checker.

        Args:
            tmux: TMUX manager instance
            config: Configuration object
            logger: Logger instance
        """
        super().__init__(tmux, config, logger)
        self.agent_status: Dict[str, AgentHealthStatus] = {}
        self.recent_recoveries: Dict[str, datetime] = {}

        # Configuration from config
        self.max_failures = getattr(config, "max_failures", 3)
        self.recovery_cooldown = getattr(config, "recovery_cooldown", 300)  # 5 minutes
        self.response_timeout = getattr(config, "response_timeout", 60)  # 1 minute
        self.idle_monitor = None  # Will be injected by MonitorService

    def initialize(self) -> bool:
        """Initialize component."""
        self.logger.info("HealthChecker initialized")
        return True

    def cleanup(self) -> None:
        """Clean up component resources."""
        self.agent_status.clear()
        self.recent_recoveries.clear()

    def set_idle_monitor(self, idle_monitor) -> None:
        """Set the idle monitor instance.

        Args:
            idle_monitor: Idle monitor instance to use for idle detection
        """
        self.idle_monitor = idle_monitor

    def register_agent(self, target: str) -> None:
        """Register a new agent for health monitoring.

        Args:
            target: Target identifier (session:window)
        """
        if target not in self.agent_status:
            now = datetime.now()
            self.agent_status[target] = AgentHealthStatus(
                target=target,
                last_heartbeat=now,
                last_response=now,
                consecutive_failures=0,
                is_responsive=True,
                last_content_hash="",
                status="healthy",
                is_idle=False,
                activity_changes=0,
            )
            self.logger.info(f"Registered agent for health monitoring: {target}")

    def unregister_agent(self, target: str) -> None:
        """Unregister an agent from health monitoring.

        Args:
            target: Target identifier (session:window)
        """
        if target in self.agent_status:
            del self.agent_status[target]
            self.logger.info(f"Unregistered agent from health monitoring: {target}")

    def check_agent_health(self, target: str) -> AgentHealthStatus:
        """Check agent health using improved idle detection.

        Args:
            target: Target identifier (session:window)

        Returns:
            AgentHealthStatus object with current health information
        """
        if target not in self.agent_status:
            self.register_agent(target)

        status = self.agent_status[target]
        now = datetime.now()

        try:
            # Use the idle monitor if available
            if self.idle_monitor:
                is_idle = self.idle_monitor.is_agent_idle(target)
                status.is_idle = is_idle
            else:
                status.is_idle = False

            # Capture current content for change detection
            content = self.tmux.capture_pane(target, lines=50)
            content_hash = str(hash(content))

            # Track activity changes
            if content_hash != status.last_content_hash:
                status.activity_changes += 1
                status.last_content_hash = content_hash
                status.last_heartbeat = now

            # Check responsiveness
            is_responsive = self._check_agent_responsiveness(target, content, status.is_idle)

            # Update status based on responsiveness
            if is_responsive:
                status.is_responsive = True
                status.consecutive_failures = 0
                status.last_response = now
                status.status = "healthy"
            else:
                status.is_responsive = False
                status.consecutive_failures += 1

                # Determine status level
                if status.consecutive_failures >= self.max_failures:
                    status.status = "critical"
                elif status.consecutive_failures >= 2:
                    status.status = "warning"
                else:
                    status.status = "unresponsive"

        except Exception as e:
            self.logger.error(f"Error checking health for {target}: {e}")
            status.consecutive_failures += 1
            status.is_responsive = False
            status.status = "critical"

        return status

    def _check_agent_responsiveness(self, target: str, content: str, is_idle: bool) -> bool:
        """Enhanced responsiveness check.

        Args:
            target: Target identifier
            content: Current pane content
            is_idle: Whether agent is idle

        Returns:
            True if agent is responsive, False otherwise
        """
        # If agent is actively working, it's responsive
        if not is_idle:
            return True

        # Check for normal Claude interface elements
        if self._has_normal_claude_interface(content):
            return True

        # Check for error conditions
        if self._has_critical_errors(content):
            return False

        # If idle but with normal interface, it's responsive
        return True

    def _has_normal_claude_interface(self, content: str) -> bool:
        """Check if content shows normal Claude interface.

        Args:
            content: Pane content to check

        Returns:
            True if normal interface is present
        """
        return is_claude_interface_present(content)

    def _has_critical_errors(self, content: str) -> bool:
        """Check for critical error states.

        Args:
            content: Pane content to check

        Returns:
            True if critical errors are detected
        """
        return _has_crash_indicators(content) or _has_error_indicators(content)

    def should_attempt_recovery(self, target: str, status: Optional[AgentHealthStatus] = None) -> bool:
        """Determine if recovery should be attempted.

        Args:
            target: Target identifier
            status: Optional pre-computed health status

        Returns:
            True if recovery should be attempted
        """
        # Get status if not provided
        if status is None:
            if target not in self.agent_status:
                return False
            status = self.agent_status[target]

        # Don't recover if recently recovered
        if target in self.recent_recoveries:
            time_since_recovery = datetime.now() - self.recent_recoveries[target]
            if time_since_recovery < timedelta(seconds=self.recovery_cooldown):
                return False

        # Recover if critical with multiple failures
        if status.status == "critical" and status.consecutive_failures >= self.max_failures:
            return True

        # Recover if unresponsive for too long
        time_since_response = datetime.now() - status.last_response
        if time_since_response > timedelta(seconds=self.response_timeout * 3):
            return True

        return False

    def mark_recovery_attempted(self, target: str) -> None:
        """Mark that recovery was attempted for an agent.

        Args:
            target: Target identifier
        """
        self.recent_recoveries[target] = datetime.now()
        self.logger.info(f"Marked recovery attempt for {target}")

    def get_all_agent_statuses(self) -> Dict[str, AgentHealthStatus]:
        """Get all current agent health statuses.

        Returns:
            Dictionary mapping targets to their health status
        """
        return self.agent_status.copy()

    def is_agent_healthy(self, target: str) -> bool:
        """Quick check if an agent is healthy.

        Args:
            target: Target identifier

        Returns:
            True if agent is healthy
        """
        if target not in self.agent_status:
            return False
        return self.agent_status[target].status == "healthy"
