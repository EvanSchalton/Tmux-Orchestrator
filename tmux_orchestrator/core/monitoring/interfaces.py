"""
Service contracts and interfaces for monitoring components.

This module defines the abstract interfaces following Interface Segregation Principle
to ensure proper dependency inversion throughout the monitoring system.
"""

from abc import ABC, abstractmethod
from typing import Any

from .types import AgentInfo, MonitorStatus


class CrashDetectorInterface(ABC):
    """Interface for crash detection services."""

    @abstractmethod
    def detect_crash(
        self, agent_info: AgentInfo, window_content: list[str], idle_duration: float | None = None
    ) -> tuple[bool, str | None]:
        """Detect if an agent has crashed based on window content analysis.

        Args:
            agent_info: Information about the agent
            window_content: Recent lines from the agent's window
            idle_duration: How long the agent has been idle

        Returns:
            Tuple of (is_crashed, crash_reason)
        """
        pass

    @abstractmethod
    def detect_pm_crash(self, session_name: str) -> tuple[bool, str | None]:
        """Detect if a PM has crashed in a session.

        Args:
            session_name: Session to check

        Returns:
            Tuple of (is_crashed, pm_target)
        """
        pass


class PMRecoveryManagerInterface(ABC):
    """Interface for PM recovery management."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the recovery manager.

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    def check_pm_health(self, session_name: str) -> tuple[bool, str | None, str | None]:
        """Check PM health in a session.

        Args:
            session_name: Session to check

        Returns:
            Tuple of (is_healthy, pm_target, issue_description)
        """
        pass

    @abstractmethod
    def should_attempt_recovery(self, session_name: str) -> bool:
        """Determine if recovery should be attempted.

        Args:
            session_name: Session to check

        Returns:
            True if recovery should be attempted
        """
        pass

    @abstractmethod
    def recover_pm(self, session_name: str, crashed_target: str | None = None) -> bool:
        """Recover a crashed or missing PM.

        Args:
            session_name: Session needing PM recovery
            crashed_target: Target of crashed PM

        Returns:
            True if recovery successful
        """
        pass

    @abstractmethod
    def get_recovery_status(self) -> dict[str, Any]:
        """Get current recovery status.

        Returns:
            Dictionary with recovery status details
        """
        pass

    @abstractmethod
    def handle_recovery(self, session_name: str, issue_type: str) -> bool:
        """Handle PM recovery for a specific issue.

        Args:
            session_name: Session needing recovery
            issue_type: Type of issue detected

        Returns:
            True if recovery handled successfully
        """
        pass

    @abstractmethod
    def check_and_recover_if_needed(self, session_name: str) -> bool:
        """Check PM health and recover if needed.

        Args:
            session_name: Session to check and recover

        Returns:
            True if check completed (recovery may or may not have been needed)
        """
        pass


class DaemonManagerInterface(ABC):
    """Interface for daemon lifecycle management."""

    @abstractmethod
    def is_running(self) -> bool:
        """Check if daemon is running.

        Returns:
            True if daemon is running
        """
        pass

    @abstractmethod
    def get_pid(self) -> int | None:
        """Get daemon PID.

        Returns:
            PID if running, None otherwise
        """
        pass

    @abstractmethod
    def start_daemon(self, target_func: Any, args: tuple = ()) -> int:
        """Start the daemon process.

        Args:
            target_func: Function to run as daemon
            args: Arguments for target function

        Returns:
            PID of started daemon
        """
        pass

    @abstractmethod
    def stop_daemon(self, timeout: int = 10) -> bool:
        """Stop the daemon gracefully.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if stopped successfully
        """
        pass

    @abstractmethod
    def restart_daemon(self, target_func: Any, args: tuple = ()) -> int:
        """Restart the daemon.

        Args:
            target_func: Function to run as daemon
            args: Arguments for target function

        Returns:
            PID of restarted daemon
        """
        pass

    @abstractmethod
    def cleanup_stale_files(self) -> None:
        """Clean up stale PID and lock files."""
        pass

    @abstractmethod
    def should_shutdown(self) -> bool:
        """Check if daemon should shutdown.

        Returns:
            True if shutdown requested
        """
        pass

    @abstractmethod
    def get_daemon_info(self) -> dict:
        """Get daemon information.

        Returns:
            Dictionary with daemon details
        """
        pass

    @abstractmethod
    def start(self) -> bool:
        """Start the daemon.

        Returns:
            True if started successfully
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """Stop the daemon.

        Returns:
            True if stopped successfully
        """
        pass


class HealthCheckerInterface(ABC):
    """Interface for agent health checking."""

    @abstractmethod
    async def check_agent_health(self, target: str) -> tuple[bool, str | None]:
        """Check health of a specific agent.

        Args:
            target: Agent target (session:window)

        Returns:
            Tuple of (is_healthy, issue_description)
        """
        pass

    @abstractmethod
    async def get_health_metrics(self) -> dict[str, Any]:
        """Get overall health metrics.

        Returns:
            Dictionary with health metrics
        """
        pass


class MonitorServiceInterface(ABC):
    """Interface for the main monitoring service orchestrator."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the monitoring service.

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up monitoring resources."""
        pass

    @abstractmethod
    async def run_monitoring_cycle(self) -> MonitorStatus:
        """Run a single monitoring cycle.

        Returns:
            Status of the monitoring cycle
        """
        pass

    @abstractmethod
    def get_component(self, component_type: str) -> Any | None:
        """Get a specific monitoring component.

        Args:
            component_type: Type of component to retrieve

        Returns:
            Component instance or None
        """
        pass


class ServiceContainerInterface(ABC):
    """Interface for dependency injection container."""

    @abstractmethod
    def register(self, interface_type: type, implementation: Any, singleton: bool = True) -> None:
        """Register a service implementation.

        Args:
            interface_type: Interface type to register
            implementation: Implementation instance or factory
            singleton: Whether to use singleton pattern
        """
        pass

    @abstractmethod
    def resolve(self, interface_type: type) -> Any:
        """Resolve a service by interface type.

        Args:
            interface_type: Interface type to resolve

        Returns:
            Service implementation instance
        """
        pass

    @abstractmethod
    def has(self, interface_type: type) -> bool:
        """Check if service is registered.

        Args:
            interface_type: Interface type to check

        Returns:
            True if registered
        """
        pass

    @abstractmethod
    def register_plugin(self, plugin_name: str, plugin_instance: Any) -> None:
        """Register a plugin.

        Args:
            plugin_name: Name of the plugin
            plugin_instance: Plugin implementation
        """
        pass

    @abstractmethod
    def get_plugin(self, plugin_name: str) -> Any:
        """Get a plugin by name.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin instance or None if not found
        """
        pass

    @abstractmethod
    def get_all_plugins(self) -> dict[str, Any]:
        """Get all registered plugins.

        Returns:
            Dictionary mapping plugin names to instances
        """
        pass

    @abstractmethod
    def get_plugin_metadata(self, plugin_name: str) -> dict[str, Any]:
        """Get plugin metadata.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin metadata dictionary
        """
        pass


class MonitoringStrategyInterface(ABC):
    """Interface for pluggable monitoring strategies."""

    @abstractmethod
    def get_name(self) -> str:
        """Get strategy name.

        Returns:
            Strategy name
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get strategy description.

        Returns:
            Strategy description
        """
        pass

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> MonitorStatus:
        """Execute the monitoring strategy.

        Args:
            context: Execution context with components

        Returns:
            Monitoring status
        """
        pass

    @abstractmethod
    def get_required_components(self) -> list[type]:
        """Get required component interfaces.

        Returns:
            List of required interface types
        """
        pass


class MonitorComponent(ABC):
    """Base interface for monitoring system components."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the component.

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up component resources."""
        pass


class AgentMonitorInterface(ABC):
    """Interface for agent monitoring operations."""

    @abstractmethod
    def check_agent(self, agent_info: AgentInfo) -> tuple[bool, str | None]:
        """Check an agent's health status.

        Args:
            agent_info: Information about the agent to check

        Returns:
            Tuple of (is_healthy, issue_description)
        """
        pass

    @abstractmethod
    def get_agent_status(self, target: str) -> dict[str, Any]:
        """Get detailed status for a specific agent.

        Args:
            target: Agent target identifier

        Returns:
            Dictionary with agent status details
        """
        pass

    @abstractmethod
    def discover_agents(self) -> list[AgentInfo]:
        """Discover all active agents.

        Returns:
            List of active agent information
        """
        pass

    @abstractmethod
    def analyze_agent_content(self, content: str, agent_info: AgentInfo) -> dict[str, Any]:
        """Analyze agent terminal content.

        Args:
            content: Terminal content to analyze
            agent_info: Agent information

        Returns:
            Analysis results dictionary
        """
        pass


class NotificationManagerInterface(ABC):
    """Interface for notification management."""

    @abstractmethod
    def send_notification(self, event_type: str, message: str, details: dict[str, Any] | None = None) -> bool:
        """Send a notification.

        Args:
            event_type: Type of notification event
            message: Notification message
            details: Optional additional details

        Returns:
            True if notification sent successfully
        """
        pass

    @abstractmethod
    def should_notify(self, event_type: str, target: str) -> bool:
        """Check if notification should be sent.

        Args:
            event_type: Type of event
            target: Target of the event

        Returns:
            True if notification should be sent
        """
        pass

    @abstractmethod
    def notify_agent_crash(self, agent_target: str, error_message: str, session: str) -> None:
        """Notify about agent crash.

        Args:
            agent_target: Target of crashed agent
            error_message: Error description
            session: Session name
        """
        pass

    @abstractmethod
    def notify_fresh_agent(self, agent_target: str) -> None:
        """Notify about fresh agent detection.

        Args:
            agent_target: Target of fresh agent
        """
        pass

    @abstractmethod
    def notify_recovery_needed(self, agent_target: str, reason: str) -> None:
        """Notify about recovery needed.

        Args:
            agent_target: Target needing recovery
            reason: Recovery reason
        """
        pass


class StateTrackerInterface(ABC):
    """Interface for state tracking operations."""

    @abstractmethod
    def update_state(self, key: str, value: Any) -> None:
        """Update tracked state.

        Args:
            key: State key
            value: State value
        """
        pass

    @abstractmethod
    def update_agent_discovered(self, agent_target: str) -> None:
        """Update agent discovery state.

        Args:
            agent_target: Target of discovered agent
        """
        pass

    @abstractmethod
    def get_state(self, key: str) -> Any | None:
        """Get tracked state.

        Args:
            key: State key

        Returns:
            State value or None if not found
        """
        pass

    @abstractmethod
    def clear_state(self, key: str | None = None) -> None:
        """Clear tracked state.

        Args:
            key: Optional specific key to clear, or None to clear all
        """
        pass

    @abstractmethod
    def get_agent_state(self, agent_id: str) -> dict[str, Any] | None:
        """Get state for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent state dictionary or None if not found
        """
        pass

    @abstractmethod
    def get_idle_duration(self, agent_id: str) -> float | None:
        """Get idle duration for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Idle duration in seconds or None if unknown
        """
        pass

    @abstractmethod
    def update_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Update agent state.

        Args:
            agent_id: Agent identifier
            state: State dictionary to update
        """
        pass
