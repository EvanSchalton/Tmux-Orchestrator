"""Interface for pluggable monitoring strategies."""

from abc import ABC, abstractmethod
from typing import Any

from ..types import MonitorStatus


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
