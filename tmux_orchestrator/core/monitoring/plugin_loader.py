"""
Plugin loader for dynamic monitoring strategies.

This module provides a plugin system for loading and managing monitoring strategies,
allowing for extensible monitoring behaviors without modifying core components.
"""

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, Optional

from .interfaces import MonitoringStrategyInterface
from .types import PluginInfo, PluginStatus


class PluginLoader:
    """Loads and manages monitoring strategy plugins."""

    def __init__(self, logger: logging.Logger, plugin_dirs: Optional[list[Path]] = None):
        """Initialize the plugin loader.

        Args:
            logger: Logger instance
            plugin_dirs: List of directories to search for plugins
        """
        self.logger = logger
        self._plugins: dict[str, PluginInfo] = {}
        self._strategies: dict[str, MonitoringStrategyInterface] = {}

        # Default plugin directories
        if plugin_dirs is None:
            plugin_dirs = [
                Path(__file__).parent / "strategies",  # Built-in strategies
                Path.home() / ".tmux-orchestrator" / "plugins",  # User plugins
            ]

        self.plugin_dirs = []
        for dir_path in plugin_dirs:
            if dir_path.exists() and dir_path.is_dir():
                self.plugin_dirs.append(dir_path)
                self.logger.debug(f"Added plugin directory: {dir_path}")

    def discover_plugins(self) -> list[PluginInfo]:
        """Discover all available plugins.

        Returns:
            List of discovered PluginInfo objects
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            self.logger.info(f"Discovering plugins in {plugin_dir}")

            # Look for Python files in plugin directory
            for py_file in plugin_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue  # Skip private modules

                try:
                    plugin_info = self._inspect_plugin_file(py_file)
                    if plugin_info:
                        discovered.append(plugin_info)
                        self._plugins[plugin_info.name] = plugin_info
                        self.logger.info(f"Discovered plugin: {plugin_info.name}")
                except Exception as e:
                    self.logger.error(f"Error inspecting plugin {py_file}: {e}")

        return discovered

    def load_plugin(self, plugin_name: str) -> MonitoringStrategyInterface | None:
        """Load a specific plugin by name.

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            Loaded strategy instance or None if failed
        """
        if plugin_name in self._strategies:
            self.logger.debug(f"Plugin {plugin_name} already loaded")
            return self._strategies[plugin_name]

        if plugin_name not in self._plugins:
            self.logger.error(f"Plugin {plugin_name} not found")
            return None

        plugin_info = self._plugins[plugin_name]

        try:
            # Load the module
            module = self._load_module(plugin_info.file_path)

            # Find the strategy class
            strategy_class = None
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, MonitoringStrategyInterface)
                    and obj is not MonitoringStrategyInterface
                ):
                    strategy_class = obj
                    break

            if not strategy_class:
                raise ValueError(f"No MonitoringStrategyInterface implementation found in {plugin_info.file_path}")

            # Instantiate the strategy
            strategy = strategy_class()
            self._strategies[plugin_name] = strategy

            # Update plugin status
            plugin_info.status = PluginStatus.LOADED
            plugin_info.instance = strategy

            self.logger.info(f"Loaded plugin: {plugin_name}")
            return strategy

        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_name}: {e}")
            plugin_info.status = PluginStatus.FAILED
            plugin_info.error = str(e)
            return None

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            True if unloaded successfully
        """
        if plugin_name not in self._strategies:
            self.logger.warning(f"Plugin {plugin_name} not loaded")
            return False

        try:
            # Clean up the strategy instance
            strategy = self._strategies[plugin_name]
            if hasattr(strategy, "cleanup"):
                strategy.cleanup()

            # Remove from loaded strategies
            del self._strategies[plugin_name]

            # Update plugin status
            if plugin_name in self._plugins:
                self._plugins[plugin_name].status = PluginStatus.DISCOVERED
                self._plugins[plugin_name].instance = None

            self.logger.info(f"Unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False

    def get_loaded_strategies(self) -> dict[str, MonitoringStrategyInterface]:
        """Get all loaded strategies.

        Returns:
            Dictionary mapping plugin names to strategy instances
        """
        return self._strategies.copy()

    def get_plugin_info(self, plugin_name: str) -> PluginInfo | None:
        """Get information about a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            PluginInfo object or None if not found
        """
        return self._plugins.get(plugin_name)

    def get_all_plugins(self) -> list[PluginInfo]:
        """Get information about all discovered plugins.

        Returns:
            List of all PluginInfo objects
        """
        return list(self._plugins.values())

    def validate_plugin(self, plugin_name: str) -> tuple[bool, str | None]:
        """Validate a plugin's implementation.

        Args:
            plugin_name: Name of the plugin to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if plugin_name not in self._plugins:
            return False, f"Plugin {plugin_name} not found"

        # Try to load the plugin
        strategy = self.load_plugin(plugin_name)
        if not strategy:
            return False, f"Failed to load plugin {plugin_name}"

        try:
            # Validate required methods
            required_methods = ["get_name", "get_description", "execute", "get_required_components"]
            for method in required_methods:
                if not hasattr(strategy, method):
                    return False, f"Missing required method: {method}"

            # Validate method signatures
            name = strategy.get_name()
            if not isinstance(name, str):
                return False, "get_name() must return a string"

            description = strategy.get_description()
            if not isinstance(description, str):
                return False, "get_description() must return a string"

            components = strategy.get_required_components()
            if not isinstance(components, list):
                return False, "get_required_components() must return a list"

            return True, None

        except Exception as e:
            return False, f"Validation error: {e}"

    def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin (useful for development).

        Args:
            plugin_name: Name of the plugin to reload

        Returns:
            True if reloaded successfully
        """
        self.logger.info(f"Reloading plugin: {plugin_name}")

        # Unload if currently loaded
        if plugin_name in self._strategies:
            if not self.unload_plugin(plugin_name):
                return False

        # Re-discover the plugin
        if plugin_name in self._plugins:
            plugin_info = self._plugins[plugin_name]
            try:
                new_info = self._inspect_plugin_file(plugin_info.file_path)
                if new_info:
                    self._plugins[plugin_name] = new_info
                    # Load the refreshed plugin
                    return self.load_plugin(plugin_name) is not None
            except Exception as e:
                self.logger.error(f"Error reloading plugin {plugin_name}: {e}")

        return False

    def _inspect_plugin_file(self, file_path: Path) -> PluginInfo | None:
        """Inspect a plugin file and extract metadata.

        Args:
            file_path: Path to the plugin file

        Returns:
            PluginInfo object or None if not a valid plugin
        """
        try:
            # Load module spec
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            if not spec or not spec.loader:
                return None

            # Load the module
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for strategy class
            strategy_class = None
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, MonitoringStrategyInterface)
                    and obj is not MonitoringStrategyInterface
                ):
                    strategy_class = obj
                    break

            if not strategy_class:
                return None

            # Extract metadata
            plugin_info = PluginInfo(
                name=file_path.stem,
                file_path=file_path,
                module_name=file_path.stem,
                class_name=strategy_class.__name__,
                status=PluginStatus.DISCOVERED,
            )

            # Try to get description from class docstring
            if strategy_class.__doc__:
                plugin_info.description = strategy_class.__doc__.strip().split("\n")[0]

            return plugin_info

        except Exception as e:
            self.logger.debug(f"Failed to inspect {file_path}: {e}")
            return None

    def _load_module(self, file_path: Path) -> Any:
        """Load a Python module from file.

        Args:
            file_path: Path to the module file

        Returns:
            Loaded module object
        """
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load module from {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
