"""
Service container for dependency injection.

This module provides a simple but powerful dependency injection container
that supports singleton and factory patterns for managing component lifecycles.
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, Optional, TypeVar

from .interfaces import ServiceContainerInterface

T = TypeVar("T")


class ServiceContainer(ServiceContainerInterface):
    """Dependency injection container for managing service instances."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the service container.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._services: dict[type, Any] = {}
        self._factories: dict[type, Callable] = {}
        self._singletons: dict[type, Any] = {}
        self._singleton_flags: dict[type, bool] = {}
        self._plugins: dict[str, Any] = {}  # Plugin registry
        self._plugin_metadata: dict[str, dict[str, Any]] = {}  # Plugin metadata
        self._async_factories: dict[type, Callable] = {}  # Async factory functions
        self._async_singletons: dict[type, Any] = {}  # Async singleton instances

    def register(self, interface_type: type[T], implementation: T | Callable[..., T], singleton: bool = True) -> None:
        """Register a service implementation.

        Args:
            interface_type: Interface type to register
            implementation: Implementation instance or factory function
            singleton: Whether to use singleton pattern
        """
        self._singleton_flags[interface_type] = singleton

        if callable(implementation) and not isinstance(implementation, type):
            # It's a factory function
            self._factories[interface_type] = implementation
            self.logger.debug(f"Registered factory for {interface_type.__name__}")
        else:
            # It's an instance
            self._services[interface_type] = implementation
            if singleton:
                self._singletons[interface_type] = implementation
            self.logger.debug(f"Registered instance for {interface_type.__name__}")

    def register_factory(self, interface_type: type[T], factory: Callable[..., T], singleton: bool = True) -> None:
        """Register a factory function for creating services.

        Args:
            interface_type: Interface type to register
            factory: Factory function that creates instances
            singleton: Whether to cache created instances
        """
        self._factories[interface_type] = factory
        self._singleton_flags[interface_type] = singleton
        self.logger.debug(f"Registered factory for {interface_type.__name__}")

    def resolve(self, interface_type: type[T]) -> T:
        """Resolve a service by interface type.

        Args:
            interface_type: Interface type to resolve

        Returns:
            Service implementation instance

        Raises:
            ValueError: If service not registered
        """
        # Check if we have a singleton instance
        if interface_type in self._singletons:
            return self._singletons[interface_type]

        # Check if we have a direct service registration
        if interface_type in self._services:
            service = self._services[interface_type]
            if self._singleton_flags.get(interface_type, True):
                self._singletons[interface_type] = service
            return service

        # Check if we have a factory
        if interface_type in self._factories:
            factory = self._factories[interface_type]

            # Auto-inject dependencies into factory
            service = self._call_with_injection(factory)

            # Cache if singleton
            if self._singleton_flags.get(interface_type, True):
                self._singletons[interface_type] = service

            return service

        # Try to auto-resolve if it's a concrete class
        if inspect.isclass(interface_type) and not inspect.isabstract(interface_type):
            try:
                service = self._auto_resolve(interface_type)
                if self._singleton_flags.get(interface_type, True):
                    self._singletons[interface_type] = service
                return service
            except Exception as e:
                self.logger.debug(f"Auto-resolution failed for {interface_type.__name__}: {e}")

        raise ValueError(f"No service registered for {interface_type.__name__}")

    def has(self, interface_type: type) -> bool:
        """Check if service is registered.

        Args:
            interface_type: Interface type to check

        Returns:
            True if registered
        """
        return (
            interface_type in self._services or interface_type in self._factories or interface_type in self._singletons
        )

    def clear(self) -> None:
        """Clear all registrations and instances."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._singleton_flags.clear()
        self._plugins.clear()
        self._plugin_metadata.clear()
        self._async_factories.clear()
        self._async_singletons.clear()
        self.logger.debug("Cleared all service registrations")

    def register_async(self, interface_type: type[T], factory: Callable[..., T], singleton: bool = True) -> None:
        """Register an async factory for a service.

        Args:
            interface_type: Interface type to register
            factory: Async factory function
            singleton: Whether to cache the instance
        """
        if not asyncio.iscoroutinefunction(factory):
            raise ValueError(f"Factory for {interface_type.__name__} must be async")

        self._async_factories[interface_type] = factory
        self._singleton_flags[interface_type] = singleton
        self.logger.debug(f"Registered async factory for {interface_type.__name__}")

    async def resolve_async(self, interface_type: type[T]) -> T:
        """Resolve a service asynchronously.

        Args:
            interface_type: Interface type to resolve

        Returns:
            Service implementation instance
        """
        # Check async singletons first
        if interface_type in self._async_singletons:
            return self._async_singletons[interface_type]

        # Check if we have an async factory
        if interface_type in self._async_factories:
            factory = self._async_factories[interface_type]
            instance = await self._call_async_with_injection(factory)

            # Cache if singleton
            if self._singleton_flags.get(interface_type, True):
                self._async_singletons[interface_type] = instance

            return instance

        # Fall back to sync resolution
        return self.resolve(interface_type)

    def register_plugin(
        self, plugin_name: str, plugin_instance: Any, metadata: Optional[dict[str, Any]] = None
    ) -> None:
        """Register a plugin with the container.

        Args:
            plugin_name: Name of the plugin
            plugin_instance: Plugin instance
            metadata: Optional plugin metadata
        """
        self._plugins[plugin_name] = plugin_instance
        if metadata:
            self._plugin_metadata[plugin_name] = metadata
        self.logger.info(f"Registered plugin: {plugin_name}")

    def get_plugin(self, plugin_name: str) -> Any | None:
        """Get a registered plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin instance or None
        """
        return self._plugins.get(plugin_name)

    def get_all_plugins(self) -> dict[str, Any]:
        """Get all registered plugins.

        Returns:
            Dictionary of plugin name to instance
        """
        return self._plugins.copy()

    def get_plugin_metadata(self, plugin_name: str) -> dict[str, Any] | None:
        """Get metadata for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin metadata or None
        """
        return self._plugin_metadata.get(plugin_name)

    def _call_with_injection(self, factory: Callable) -> Any:
        """Call a factory function with automatic dependency injection.

        Args:
            factory: Factory function to call

        Returns:
            Created instance
        """
        # Check if it's an async factory
        if asyncio.iscoroutinefunction(factory):
            return self._call_async_with_injection(factory)

        sig = inspect.signature(factory)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            if param.annotation == inspect.Parameter.empty:
                continue

            # Try to resolve the parameter type
            param_type = param.annotation

            # Skip basic types
            if param_type in (str, int, float, bool, dict, list, tuple, set):
                continue

            try:
                # Try to resolve from container
                if self.has(param_type):
                    kwargs[param_name] = self.resolve(param_type)
            except Exception as e:
                self.logger.debug(f"Could not inject {param_name}: {e}")

        return factory(**kwargs)

    async def _call_async_with_injection(self, factory: Callable) -> Any:
        """Call an async factory function with automatic dependency injection.

        Args:
            factory: Async factory function to call

        Returns:
            Created instance
        """
        sig = inspect.signature(factory)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            if param.annotation == inspect.Parameter.empty:
                continue

            # Try to resolve the parameter type
            param_type = param.annotation

            # Skip basic types
            if param_type in (str, int, float, bool, dict, list, tuple, set):
                continue

            try:
                # Try to resolve from container
                if self.has(param_type):
                    resolved = self.resolve(param_type)
                    # If the resolved value is a coroutine, await it
                    if asyncio.iscoroutine(resolved):
                        kwargs[param_name] = await resolved
                    else:
                        kwargs[param_name] = resolved
            except Exception as e:
                self.logger.debug(f"Could not inject {param_name}: {e}")

        return await factory(**kwargs)

    def _auto_resolve(self, cls: type[T]) -> T:
        """Attempt to auto-resolve a concrete class.

        Args:
            cls: Class to instantiate

        Returns:
            Created instance
        """
        if not hasattr(cls, "__init__"):
            return cls()

        sig = inspect.signature(cls.__init__)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            if param.annotation == inspect.Parameter.empty:
                continue

            param_type = param.annotation

            # Skip basic types
            if param_type in (str, int, float, bool, dict, list, tuple, set):
                continue

            try:
                # Try to resolve from container
                if self.has(param_type):
                    kwargs[param_name] = self.resolve(param_type)
                elif param.default == inspect.Parameter.empty:
                    # Required parameter we can't resolve
                    raise ValueError(f"Cannot resolve required parameter {param_name}")
            except Exception as e:
                self.logger.debug(f"Could not inject {param_name}: {e}")
                if param.default == inspect.Parameter.empty:
                    raise

        return cls(**kwargs)


class ServiceBuilder:
    """Fluent builder for configuring services in the container."""

    def __init__(self, container: ServiceContainer):
        """Initialize the builder.

        Args:
            container: Service container instance
        """
        self.container = container
        self._interface_type: type | None = None
        self._implementation: Any | None = None
        self._singleton: bool = True

    def add(self, interface_type: type) -> "ServiceBuilder":
        """Start building a service registration.

        Args:
            interface_type: Interface type to register

        Returns:
            Self for chaining
        """
        self._interface_type = interface_type
        return self

    def use(self, implementation: Any | Callable) -> "ServiceBuilder":
        """Set the implementation or factory.

        Args:
            implementation: Implementation instance or factory

        Returns:
            Self for chaining
        """
        self._implementation = implementation
        return self

    def as_singleton(self) -> "ServiceBuilder":
        """Configure as singleton.

        Returns:
            Self for chaining
        """
        self._singleton = True
        return self

    def as_transient(self) -> "ServiceBuilder":
        """Configure as transient (new instance each time).

        Returns:
            Self for chaining
        """
        self._singleton = False
        return self

    def build(self) -> None:
        """Build and register the service."""
        if not self._interface_type or self._implementation is None:
            raise ValueError("Both interface type and implementation must be set")

        self.container.register(self._interface_type, self._implementation, self._singleton)
