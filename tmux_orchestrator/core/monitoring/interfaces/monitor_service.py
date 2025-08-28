"""Interface for the main monitoring service orchestrator."""

from abc import ABC, abstractmethod
from typing import Any

from ..types import MonitorStatus


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
