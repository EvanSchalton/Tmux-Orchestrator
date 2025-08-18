"""
Plugin integration bridge for the monitoring system.

This module provides the integration layer between the plugin loader
and the service container, ensuring smooth plugin lifecycle management.
"""

import logging
from typing import Any

from .interfaces import MonitoringStrategyInterface, ServiceContainerInterface
from .plugin_loader import PluginLoader
from .types import PluginInfo, PluginStatus


class PluginIntegrationBridge:
    """Bridges the plugin system with the service container."""

    def __init__(self, container: ServiceContainerInterface, logger: logging.Logger):
        """Initialize the plugin integration bridge.

        Args:
            container: Service container for dependency injection
            logger: Logger instance
        """
        self.container = container
        self.logger = logger
        self.plugin_loader = PluginLoader(logger)
        self._active_strategy: str | None = None

    def discover_and_register_plugins(self) -> list[PluginInfo]:
        """Discover all plugins and register them with the container.

        Returns:
            List of discovered plugin information
        """
        # Discover all available plugins
        plugins = self.plugin_loader.discover_plugins()

        for plugin_info in plugins:
            try:
                # Load the plugin
                strategy = self.plugin_loader.load_plugin(plugin_info.name)

                if strategy:
                    # Register with container
                    metadata = {
                        "name": plugin_info.name,
                        "description": plugin_info.description,
                        "file_path": str(plugin_info.file_path),
                        "status": plugin_info.status.value,
                        "required_components": strategy.get_required_components(),
                    }

                    self.container.register_plugin(plugin_info.name, strategy, metadata)

                    self.logger.info(f"Registered plugin '{plugin_info.name}' with container")

            except Exception as e:
                self.logger.error(f"Failed to register plugin '{plugin_info.name}': {e}")
                plugin_info.status = PluginStatus.FAILED
                plugin_info.error = str(e)

        return plugins

    def set_active_strategy(self, strategy_name: str) -> bool:
        """Set the active monitoring strategy.

        Args:
            strategy_name: Name of the strategy to activate

        Returns:
            True if strategy activated successfully
        """
        # Check if strategy is registered
        strategy = self.container.get_plugin(strategy_name)

        if not strategy:
            # Try to load it
            strategy = self.plugin_loader.load_plugin(strategy_name)
            if not strategy:
                self.logger.error(f"Strategy '{strategy_name}' not found")
                return False

        # Validate required components
        if not self._validate_strategy_requirements(strategy):
            self.logger.error(f"Strategy '{strategy_name}' requirements not met")
            return False

        self._active_strategy = strategy_name
        self.logger.info(f"Activated strategy: {strategy_name}")
        return True

    def get_active_strategy(self) -> MonitoringStrategyInterface | None:
        """Get the currently active monitoring strategy.

        Returns:
            Active strategy instance or None
        """
        if not self._active_strategy:
            return None

        return self.container.get_plugin(self._active_strategy)

    def create_strategy_context(self) -> dict[str, Any]:
        """Create execution context for strategy.

        Returns:
            Dictionary with resolved components for strategy execution
        """
        from .interfaces import (
            AgentMonitorInterface,
            CrashDetectorInterface,
            NotificationManagerInterface,
            PMRecoveryManagerInterface,
            StateTrackerInterface,
        )

        context = {}

        # Resolve all standard monitoring components
        component_interfaces = [
            AgentMonitorInterface,
            StateTrackerInterface,
            CrashDetectorInterface,
            NotificationManagerInterface,
            PMRecoveryManagerInterface,
        ]

        for interface in component_interfaces:
            try:
                component = self.container.resolve(interface)
                # Add both by interface name and simple name
                context[interface.__name__] = component
                context[interface.__name__.replace("Interface", "").lower()] = component
            except Exception as e:
                self.logger.warning(f"Could not resolve {interface.__name__}: {e}")

        # Add logger and config
        context["logger"] = self.logger

        return context

    def _validate_strategy_requirements(self, strategy: MonitoringStrategyInterface) -> bool:
        """Validate that strategy requirements are met.

        Args:
            strategy: Strategy to validate

        Returns:
            True if all requirements are met
        """
        required_components = strategy.get_required_components()

        for component_type in required_components:
            if not self.container.has(component_type):
                self.logger.error(f"Missing required component: {component_type.__name__}")
                return False

        return True

    def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin (useful for development).

        Args:
            plugin_name: Name of plugin to reload

        Returns:
            True if reloaded successfully
        """
        # Remove from container
        if self.container.get_plugin(plugin_name):
            # If it's the active strategy, deactivate
            if self._active_strategy == plugin_name:
                self._active_strategy = None

        # Reload via plugin loader
        if self.plugin_loader.reload_plugin(plugin_name):
            # Re-register with container
            strategy = self.plugin_loader.get_loaded_strategies().get(plugin_name)
            if strategy:
                plugin_info = self.plugin_loader.get_plugin_info(plugin_name)
                metadata = {
                    "name": plugin_name,
                    "description": plugin_info.description if plugin_info else "",
                    "reloaded": True,
                }

                self.container.register_plugin(plugin_name, strategy, metadata)
                return True

        return False

    def get_available_strategies(self) -> dict[str, dict[str, Any]]:
        """Get all available monitoring strategies.

        Returns:
            Dictionary of strategy name to metadata
        """
        strategies = {}

        for plugin_name in self.container.get_all_plugins():
            metadata = self.container.get_plugin_metadata(plugin_name)
            if metadata:
                strategies[plugin_name] = metadata

        return strategies
