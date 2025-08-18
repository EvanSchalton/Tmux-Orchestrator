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
