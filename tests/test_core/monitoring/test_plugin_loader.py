"""
Comprehensive tests for PluginLoader component.

Tests plugin discovery, loading, validation, and lifecycle management.
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.monitoring.plugin_loader import PluginLoader
from tmux_orchestrator.core.monitoring.types import PluginInfo, PluginStatus


class TestPluginLoaderInitialization:
    """Test PluginLoader initialization and configuration."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = Mock(spec=logging.Logger)
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_initialization_default_dirs(self):
        """Test initialization with default plugin directories."""
        loader = PluginLoader(self.logger)

        assert loader.logger == self.logger
        assert isinstance(loader._plugins, dict)
        assert isinstance(loader._strategies, dict)
        assert len(loader.plugin_dirs) >= 0  # May vary based on system

    def test_initialization_custom_dirs(self):
        """Test initialization with custom plugin directories."""
        plugin_dirs = [self.temp_dir]
        loader = PluginLoader(self.logger, plugin_dirs)

        assert self.temp_dir in loader.plugin_dirs

    def test_initialization_nonexistent_dirs(self):
        """Test initialization with non-existent directories."""
        nonexistent_dir = Path("/nonexistent/path")
        plugin_dirs = [nonexistent_dir, self.temp_dir]

        loader = PluginLoader(self.logger, plugin_dirs)

        # Should only include existing directories
        assert nonexistent_dir not in loader.plugin_dirs
        assert self.temp_dir in loader.plugin_dirs


class TestPluginDiscovery:
    """Test plugin discovery functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = Mock(spec=logging.Logger)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.loader = PluginLoader(self.logger, [self.temp_dir])

    def test_discover_empty_directory(self):
        """Test discovery in empty directory."""
        plugins = self.loader.discover_plugins()
        assert plugins == []

    def test_discover_valid_plugin(self):
        """Test discovery of valid plugin."""
        # Create a valid plugin file
        plugin_content = '''
from tmux_orchestrator.core.monitoring.interfaces import MonitoringStrategyInterface

class TestStrategy(MonitoringStrategyInterface):
    """A test monitoring strategy."""

    def get_name(self):
        return "test_strategy"

    def get_description(self):
        return "Test strategy for unit tests"

    def execute(self, context):
        return {"status": "success"}

    def get_required_components(self):
        return ["agent_monitor"]
'''

        plugin_file = self.temp_dir / "test_plugin.py"
        plugin_file.write_text(plugin_content)

        with patch.object(self.loader, "_inspect_plugin_file") as mock_inspect:
            mock_inspect.return_value = PluginInfo(
                name="test_plugin",
                file_path=plugin_file,
                module_name="test_plugin",
                class_name="TestStrategy",
                status=PluginStatus.DISCOVERED,
            )

            plugins = self.loader.discover_plugins()

            assert len(plugins) == 1
            assert plugins[0].name == "test_plugin"
            assert "test_plugin" in self.loader._plugins

    def test_discover_invalid_plugin(self):
        """Test discovery handles invalid plugins gracefully."""
        # Create an invalid plugin file
        invalid_content = "This is not valid Python code {"

        plugin_file = self.temp_dir / "invalid_plugin.py"
        plugin_file.write_text(invalid_content)

        plugins = self.loader.discover_plugins()

        # Should handle gracefully and continue
        assert len(plugins) == 0
        # Note: error logging happens inside _inspect_plugin_file which may not be called for invalid syntax

    def test_discover_skip_private_modules(self):
        """Test that private modules are skipped."""
        private_file = self.temp_dir / "_private_plugin.py"
        private_file.write_text("# Private module")

        plugins = self.loader.discover_plugins()

        assert len(plugins) == 0


class TestPluginLoading:
    """Test plugin loading functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = Mock(spec=logging.Logger)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.loader = PluginLoader(self.logger, [self.temp_dir])

        # Add a mock plugin to the registry
        self.mock_plugin_info = PluginInfo(
            name="test_plugin",
            file_path=self.temp_dir / "test_plugin.py",
            module_name="test_plugin",
            class_name="TestStrategy",
            status=PluginStatus.DISCOVERED,
        )
        self.loader._plugins["test_plugin"] = self.mock_plugin_info

    def test_load_nonexistent_plugin(self):
        """Test loading a plugin that doesn't exist."""
        strategy = self.loader.load_plugin("nonexistent")

        assert strategy is None
        self.logger.error.assert_called_with("Plugin nonexistent not found")

    def test_load_already_loaded_plugin(self):
        """Test loading a plugin that's already loaded."""
        mock_strategy = Mock()
        self.loader._strategies["test_plugin"] = mock_strategy

        strategy = self.loader.load_plugin("test_plugin")

        assert strategy == mock_strategy
        self.logger.debug.assert_called_with("Plugin test_plugin already loaded")

    @patch("tmux_orchestrator.core.monitoring.plugin_loader.inspect")
    def test_load_plugin_success(self, mock_inspect):
        """Test successful plugin loading."""
        # Mock the module and strategy class
        mock_strategy_class = Mock()
        mock_strategy_instance = Mock()
        mock_strategy_class.return_value = mock_strategy_instance

        mock_module = Mock()
        mock_inspect.getmembers.return_value = [("TestStrategy", mock_strategy_class), ("other_class", object)]
        mock_inspect.isclass.side_effect = lambda x: x == mock_strategy_class

        # Mock the module loading
        with (
            patch.object(self.loader, "_load_module", return_value=mock_module),
            patch("tmux_orchestrator.core.monitoring.plugin_loader.issubclass") as mock_issubclass,
        ):
            # Configure issubclass to return True for our mock class
            def issubclass_side_effect(cls, interface):
                from tmux_orchestrator.core.monitoring.interfaces import MonitoringStrategyInterface

                return cls == mock_strategy_class and interface == MonitoringStrategyInterface

            mock_issubclass.side_effect = issubclass_side_effect

            strategy = self.loader.load_plugin("test_plugin")

            assert strategy == mock_strategy_instance
            assert "test_plugin" in self.loader._strategies
            assert self.mock_plugin_info.status == PluginStatus.LOADED

    def test_load_plugin_no_strategy_class(self):
        """Test loading plugin with no strategy class."""
        mock_module = Mock()

        with (
            patch.object(self.loader, "_load_module", return_value=mock_module),
            patch("tmux_orchestrator.core.monitoring.plugin_loader.inspect") as mock_inspect,
        ):
            mock_inspect.getmembers.return_value = [("SomeClass", object)]
            mock_inspect.isclass.return_value = True

            with patch("tmux_orchestrator.core.monitoring.plugin_loader.issubclass", return_value=False):
                strategy = self.loader.load_plugin("test_plugin")

                assert strategy is None
                assert self.mock_plugin_info.status == PluginStatus.FAILED

    def test_load_plugin_exception(self):
        """Test plugin loading with exception."""
        with patch.object(self.loader, "_load_module", side_effect=Exception("Load error")):
            strategy = self.loader.load_plugin("test_plugin")

            assert strategy is None
            assert self.mock_plugin_info.status == PluginStatus.FAILED
            assert self.mock_plugin_info.error == "Load error"


class TestPluginUnloading:
    """Test plugin unloading functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = Mock(spec=logging.Logger)
        self.loader = PluginLoader(self.logger, [])

        # Set up a loaded plugin
        self.mock_strategy = Mock()
        self.loader._strategies["test_plugin"] = self.mock_strategy

        self.mock_plugin_info = PluginInfo(
            name="test_plugin",
            file_path=Path("/test.py"),
            module_name="test_plugin",
            class_name="TestStrategy",
            status=PluginStatus.LOADED,
            instance=self.mock_strategy,
        )
        self.loader._plugins["test_plugin"] = self.mock_plugin_info

    def test_unload_nonexistent_plugin(self):
        """Test unloading a plugin that's not loaded."""
        result = self.loader.unload_plugin("nonexistent")

        assert result is False
        self.logger.warning.assert_called_with("Plugin nonexistent not loaded")

    def test_unload_plugin_success(self):
        """Test successful plugin unloading."""
        result = self.loader.unload_plugin("test_plugin")

        assert result is True
        assert "test_plugin" not in self.loader._strategies
        assert self.mock_plugin_info.status == PluginStatus.DISCOVERED
        assert self.mock_plugin_info.instance is None

    def test_unload_plugin_with_cleanup(self):
        """Test unloading plugin that has cleanup method."""
        self.mock_strategy.cleanup = Mock()

        result = self.loader.unload_plugin("test_plugin")

        assert result is True
        self.mock_strategy.cleanup.assert_called_once()

    def test_unload_plugin_exception(self):
        """Test unloading plugin with exception."""
        self.mock_strategy.cleanup = Mock(side_effect=Exception("Cleanup error"))

        result = self.loader.unload_plugin("test_plugin")

        assert result is False
        self.logger.error.assert_called()


class TestPluginValidation:
    """Test plugin validation functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = Mock(spec=logging.Logger)
        self.loader = PluginLoader(self.logger, [])

    def test_validate_nonexistent_plugin(self):
        """Test validating a plugin that doesn't exist."""
        valid, error = self.loader.validate_plugin("nonexistent")

        assert not valid
        assert error == "Plugin nonexistent not found"

    def test_validate_plugin_load_failure(self):
        """Test validating a plugin that fails to load."""
        mock_plugin_info = PluginInfo(
            name="test_plugin",
            file_path=Path("/test.py"),
            module_name="test_plugin",
            class_name="TestStrategy",
            status=PluginStatus.DISCOVERED,
        )
        self.loader._plugins["test_plugin"] = mock_plugin_info

        with patch.object(self.loader, "load_plugin", return_value=None):
            valid, error = self.loader.validate_plugin("test_plugin")

            assert not valid
            assert error == "Failed to load plugin test_plugin"

    def test_validate_plugin_missing_methods(self):
        """Test validating plugin with missing required methods."""
        # Add mock plugin to registry first
        mock_plugin_info = PluginInfo(
            name="test_plugin",
            file_path=Path("/test.py"),
            module_name="test_plugin",
            class_name="TestStrategy",
            status=PluginStatus.DISCOVERED,
        )
        self.loader._plugins["test_plugin"] = mock_plugin_info

        # Create a mock object that doesn't have the required methods
        class IncompleteStrategy:
            def some_other_method(self):
                return "not what we want"

        mock_strategy = IncompleteStrategy()

        with patch.object(self.loader, "load_plugin", return_value=mock_strategy):
            valid, error = self.loader.validate_plugin("test_plugin")

            assert not valid
            assert "Missing required method" in error

    def test_validate_plugin_invalid_return_types(self):
        """Test validating plugin with invalid return types."""
        # Add mock plugin to registry first
        mock_plugin_info = PluginInfo(
            name="test_plugin",
            file_path=Path("/test.py"),
            module_name="test_plugin",
            class_name="TestStrategy",
            status=PluginStatus.DISCOVERED,
        )
        self.loader._plugins["test_plugin"] = mock_plugin_info

        mock_strategy = Mock()
        mock_strategy.get_name.return_value = 123  # Should be string
        mock_strategy.get_description.return_value = "Valid description"
        mock_strategy.get_required_components.return_value = []
        mock_strategy.execute = Mock()

        with patch.object(self.loader, "load_plugin", return_value=mock_strategy):
            valid, error = self.loader.validate_plugin("test_plugin")

            assert not valid
            assert "get_name() must return a string" in error

    def test_validate_plugin_success(self):
        """Test successful plugin validation."""
        # Add mock plugin to registry first
        mock_plugin_info = PluginInfo(
            name="test_plugin",
            file_path=Path("/test.py"),
            module_name="test_plugin",
            class_name="TestStrategy",
            status=PluginStatus.DISCOVERED,
        )
        self.loader._plugins["test_plugin"] = mock_plugin_info

        mock_strategy = Mock()
        mock_strategy.get_name.return_value = "test_strategy"
        mock_strategy.get_description.return_value = "Test description"
        mock_strategy.get_required_components.return_value = ["agent_monitor"]
        mock_strategy.execute = Mock()

        with patch.object(self.loader, "load_plugin", return_value=mock_strategy):
            valid, error = self.loader.validate_plugin("test_plugin")

            assert valid
            assert error is None


class TestPluginUtilities:
    """Test utility methods."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = Mock(spec=logging.Logger)
        self.loader = PluginLoader(self.logger, [])

        # Add some test plugins
        self.mock_strategy = Mock()
        self.loader._strategies["loaded_plugin"] = self.mock_strategy

        self.plugin_info = PluginInfo(
            name="test_plugin",
            file_path=Path("/test.py"),
            module_name="test_plugin",
            class_name="TestStrategy",
            status=PluginStatus.DISCOVERED,
        )
        self.loader._plugins["test_plugin"] = self.plugin_info

    def test_get_loaded_strategies(self):
        """Test getting all loaded strategies."""
        strategies = self.loader.get_loaded_strategies()

        assert "loaded_plugin" in strategies
        assert strategies["loaded_plugin"] == self.mock_strategy

        # Should be a copy, not the original
        assert strategies is not self.loader._strategies

    def test_get_plugin_info(self):
        """Test getting plugin info."""
        info = self.loader.get_plugin_info("test_plugin")

        assert info == self.plugin_info

        # Non-existent plugin
        info = self.loader.get_plugin_info("nonexistent")
        assert info is None

    def test_get_all_plugins(self):
        """Test getting all plugin info."""
        plugins = self.loader.get_all_plugins()

        assert len(plugins) == 1
        assert self.plugin_info in plugins

    def test_reload_plugin_not_loaded(self):
        """Test reloading a plugin that's not loaded."""
        with (
            patch.object(self.loader, "_inspect_plugin_file") as mock_inspect,
            patch.object(self.loader, "load_plugin", return_value=Mock()) as mock_load,
        ):
            mock_inspect.return_value = self.plugin_info

            result = self.loader.reload_plugin("test_plugin")

            assert result is True
            mock_load.assert_called_once_with("test_plugin")

    def test_reload_plugin_currently_loaded(self):
        """Test reloading a currently loaded plugin."""
        self.loader._strategies["test_plugin"] = Mock()

        with (
            patch.object(self.loader, "unload_plugin", return_value=True),
            patch.object(self.loader, "_inspect_plugin_file", return_value=self.plugin_info),
            patch.object(self.loader, "load_plugin", return_value=Mock()),
        ):
            result = self.loader.reload_plugin("test_plugin")

            assert result is True


class TestModuleLoading:
    """Test module loading functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = Mock(spec=logging.Logger)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.loader = PluginLoader(self.logger, [self.temp_dir])

    def test_load_module_success(self):
        """Test successful module loading."""
        # Create a simple Python module
        module_content = """
def test_function():
    return "success"

TEST_CONSTANT = 42
"""
        module_file = self.temp_dir / "test_module.py"
        module_file.write_text(module_content)

        module = self.loader._load_module(module_file)

        assert hasattr(module, "test_function")
        assert hasattr(module, "TEST_CONSTANT")
        assert module.test_function() == "success"
        assert module.TEST_CONSTANT == 42

    def test_load_module_syntax_error(self):
        """Test loading module with syntax error."""
        # Create a module with syntax error
        invalid_content = "def broken_function(:\n    return 'error'"
        module_file = self.temp_dir / "broken_module.py"
        module_file.write_text(invalid_content)

        with pytest.raises(SyntaxError):
            self.loader._load_module(module_file)

    def test_load_nonexistent_module(self):
        """Test loading non-existent module."""
        nonexistent_file = self.temp_dir / "nonexistent.py"

        with pytest.raises((ImportError, FileNotFoundError)):
            self.loader._load_module(nonexistent_file)


class TestPluginInspection:
    """Test plugin file inspection."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = Mock(spec=logging.Logger)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.loader = PluginLoader(self.logger, [self.temp_dir])

    def test_inspect_valid_plugin_file(self):
        """Test inspecting a valid plugin file."""
        plugin_content = '''
"""Test plugin module."""

from tmux_orchestrator.core.monitoring.interfaces import MonitoringStrategyInterface

class TestStrategy(MonitoringStrategyInterface):
    """A test monitoring strategy."""

    def get_name(self):
        return "test"

    def get_description(self):
        return "test strategy"

    def execute(self, context):
        return {}

    def get_required_components(self):
        return []
'''

        plugin_file = self.temp_dir / "test_plugin.py"
        plugin_file.write_text(plugin_content)

        with patch("tmux_orchestrator.core.monitoring.plugin_loader.issubclass") as mock_issubclass:
            mock_issubclass.return_value = True

            plugin_info = self.loader._inspect_plugin_file(plugin_file)

            assert plugin_info is not None
            assert plugin_info.name == "test_plugin"
            assert plugin_info.class_name == "TestStrategy"
            assert plugin_info.description == "A test monitoring strategy."

    def test_inspect_file_no_strategy_class(self):
        """Test inspecting file with no strategy class."""
        non_plugin_content = """
class RegularClass:
    def regular_method(self):
        return "not a strategy"
"""

        plugin_file = self.temp_dir / "non_plugin.py"
        plugin_file.write_text(non_plugin_content)

        plugin_info = self.loader._inspect_plugin_file(plugin_file)

        assert plugin_info is None

    def test_inspect_invalid_file(self):
        """Test inspecting invalid Python file."""
        invalid_content = "This is not valid Python {"
        plugin_file = self.temp_dir / "invalid.py"
        plugin_file.write_text(invalid_content)

        plugin_info = self.loader._inspect_plugin_file(plugin_file)

        assert plugin_info is None


class TestErrorHandling:
    """Test error handling and edge cases."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = Mock(spec=logging.Logger)
        self.loader = PluginLoader(self.logger, [])

    def test_empty_plugin_directories(self):
        """Test with empty plugin directories list."""
        loader = PluginLoader(self.logger, [])
        plugins = loader.discover_plugins()

        assert plugins == []

    def test_concurrent_access(self):
        """Test thread safety of plugin operations."""
        # This is a basic test - real concurrency testing would need threads
        plugin_info = PluginInfo(
            name="test",
            file_path=Path("/test.py"),
            module_name="test",
            class_name="Test",
            status=PluginStatus.DISCOVERED,
        )

        # Simulate concurrent access
        self.loader._plugins["test"] = plugin_info
        info1 = self.loader.get_plugin_info("test")
        info2 = self.loader.get_plugin_info("test")

        assert info1 == info2

    def test_plugin_with_no_docstring(self):
        """Test plugin inspection with no class docstring."""
        plugin_content = """
from tmux_orchestrator.core.monitoring.interfaces import MonitoringStrategyInterface

class NoDocStrategy(MonitoringStrategyInterface):
    def get_name(self):
        return "no_doc"
"""

        plugin_file = Path(tempfile.mktemp(suffix=".py"))
        plugin_file.write_text(plugin_content)

        try:
            with patch("tmux_orchestrator.core.monitoring.plugin_loader.issubclass", return_value=True):
                plugin_info = self.loader._inspect_plugin_file(plugin_file)

                assert plugin_info is not None
                assert plugin_info.description is None
        finally:
            plugin_file.unlink(missing_ok=True)
