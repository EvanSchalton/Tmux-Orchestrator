"""
Base monitoring strategy implementation.

This module provides the abstract base class for all monitoring strategies,
enabling pluggable monitoring behaviors.
"""

from abc import abstractmethod
from typing import Any

from ..interfaces import MonitoringStrategyInterface
from ..types import MonitorStatus


class BaseMonitoringStrategy(MonitoringStrategyInterface):
    """Base class for monitoring strategies with common functionality."""

    def __init__(self, name: str, description: str):
        """Initialize the base strategy.

        Args:
            name: Strategy name
            description: Strategy description
        """
        self._name = name
        self._description = description
        self._required_components: list[type] = []

    def get_name(self) -> str:
        """Get strategy name.

        Returns:
            Strategy name
        """
        return self._name

    def get_description(self) -> str:
        """Get strategy description.

        Returns:
            Strategy description
        """
        return self._description

    def get_required_components(self) -> list[type]:
        """Get required component interfaces.

        Returns:
            List of required interface types
        """
        return self._required_components

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> MonitorStatus:
        """Execute the monitoring strategy.

        Args:
            context: Execution context with components

        Returns:
            Monitoring status
        """
        pass

    def validate_context(self, context: dict[str, Any]) -> bool:
        """Validate that context contains required components.

        Args:
            context: Execution context to validate

        Returns:
            True if context is valid
        """
        for component_type in self._required_components:
            component_name = component_type.__name__
            if component_name not in context:
                return False

        return True

    def add_required_component(self, component_type: type) -> None:
        """Add a required component type.

        Args:
            component_type: Interface type that this strategy requires
        """
        if component_type not in self._required_components:
            self._required_components.append(component_type)
