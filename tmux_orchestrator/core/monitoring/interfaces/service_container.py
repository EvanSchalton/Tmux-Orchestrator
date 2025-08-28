"""Interface for dependency injection container."""

from abc import ABC, abstractmethod
from typing import Any


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
