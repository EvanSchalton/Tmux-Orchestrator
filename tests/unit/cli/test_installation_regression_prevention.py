#!/usr/bin/env python3
"""
Installation Regression Prevention Test Suite

This comprehensive test suite prevents regressions in CLI installation and path resolution
by testing actual command execution in simulated fresh installation environments.

Focus Areas:
1. Fresh pip installation simulation
2. CLI entry point verification
3. Path resolution across different working directories
4. Setup command execution
5. Core command functionality
6. Edge case handling
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# Import the main CLI
try:
    from tmux_orchestrator.cli import cli
except ImportError as e:
    pytest.skip(f"Cannot import CLI modules: {e}", allow_module_level=True)


class FreshInstallationSimulator:
    """Simulates a fresh pip installation environment."""

    def __init__(self):
        self.runner = CliRunner()
        self.original_cwd = os.getcwd()

    def test_in_directory(self, test_dir: Path, isolated=True):
        """Context manager for testing in a specific directory."""
        if isolated:
            return self.runner.isolated_filesystem()
        else:

            class DirectoryContext:
                def __init__(self, target_dir):
                    self.target_dir = target_dir
                    self.original_cwd = os.getcwd()

                def __enter__(self):
                    os.chdir(self.target_dir)
                    return self.target_dir

                def __exit__(self, exc_type, exc_val, exc_tb):
                    os.chdir(self.original_cwd)

            return DirectoryContext(test_dir)


@pytest.fixture
def fresh_simulator():
    """Provide a fresh installation simulator."""
    return FreshInstallationSimulator()


def test_cli_module_entry_point():
    """Test that the CLI can be invoked via module execution."""
    result = subprocess.run(
        [sys.executable, "-m", "tmux_orchestrator.cli", "--help"],
        capture_output=True,
        text=True,
        cwd="/workspaces/Tmux-Orchestrator",
    )

    assert result.returncode == 0
    assert "TMUX Orchestrator" in result.stdout
    assert "tmux-orc" in result.stdout
    assert "Usage:" in result.stdout


def test_cli_basic_commands_execution(fresh_simulator):
    """Test that basic CLI commands execute without errors."""
    basic_commands = [
        ["--help"],
        ["--version"],
        ["reflect"],
        ["reflect", "--format", "json"],
        ["reflect", "--format", "markdown"],
        ["status", "--json"],
        ["list", "--json"],
    ]

    for command in basic_commands:
        result = fresh_simulator.runner.invoke(cli, command)
        assert result.exit_code == 0, f"Command {command} failed: {result.output}"


def test_cli_help_system_completeness(fresh_simulator):
    """Test that help system is complete and accessible."""
    # Test main help
    result = fresh_simulator.runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "Commands:" in result.output

    # Get all commands via reflection
    result = fresh_simulator.runner.invoke(cli, ["reflect", "--format", "json"])
    assert result.exit_code == 0

    try:
        commands_data = json.loads(result.output)

        # Test help for each top-level command
        for command_name in commands_data.keys():
            result = fresh_simulator.runner.invoke(cli, [command_name, "--help"])
            assert result.exit_code == 0, f"Help failed for command: {command_name}"
            assert "Usage:" in result.output

    except json.JSONDecodeError:
        pytest.fail("Could not parse CLI reflection output")


def test_fresh_installation_directory_independence():
    """Test CLI works independently of working directory."""
    test_directories = [
        "/tmp",
        "/home",
        "/usr",
        "/workspaces",
        "/workspaces/Tmux-Orchestrator",
    ]

    available_dirs = [d for d in test_directories if os.path.exists(d) and os.access(d, os.R_OK)]

    for test_dir in available_dirs[:3]:  # Test first 3 available directories
        try:
            result = subprocess.run(
                [sys.executable, "-m", "tmux_orchestrator.cli", "reflect", "--format", "json"],
                capture_output=True,
                text=True,
                cwd=test_dir,
            )

            assert result.returncode == 0, f"CLI failed in directory {test_dir}: {result.stderr}"

            # Verify JSON output
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON output in directory {test_dir}")

        except PermissionError:
            # Skip directories we can't access
            continue


def test_setup_command_execution_safety(fresh_simulator):
    """Test setup commands execute safely without making changes."""
    setup_commands = [
        ["setup", "--help"],
        ["setup", "check"],
        ["setup", "check-requirements"],
    ]

    for command in setup_commands:
        result = fresh_simulator.runner.invoke(cli, command)
        assert result.exit_code == 0, f"Setup command {command} failed: {result.output}"


def test_json_output_consistency(fresh_simulator):
    """Test JSON output consistency across commands."""
    json_commands = [
        ["reflect", "--format", "json"],
        ["status", "--json"],
        ["list", "--json"],
    ]

    for command in json_commands:
        result = fresh_simulator.runner.invoke(cli, command)
        assert result.exit_code == 0, f"JSON command {command} failed: {result.output}"

        # Verify valid JSON
        try:
            data = json.loads(result.output)
            assert isinstance(data, (dict, list)), f"Unexpected JSON type for {command}"
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON output for {command}: {result.output}")


def test_configuration_loading_robustness(fresh_simulator):
    """Test CLI handles missing/corrupt configuration gracefully."""
    with fresh_simulator.runner.isolated_filesystem():
        # Test with no config file
        result = fresh_simulator.runner.invoke(cli, ["status"])
        assert result.exit_code == 0

        # Test with invalid config file
        Path("tmux-orc.yaml").write_text("invalid: yaml: content: [")
        result = fresh_simulator.runner.invoke(cli, ["--verbose", "status"])
        assert result.exit_code == 0  # Should use defaults


def test_tmux_manager_initialization_robustness(fresh_simulator):
    """Test TMUXManager initialization with various scenarios."""
    with patch("tmux_orchestrator.utils.tmux.TMUXManager") as mock_tmux:
        # Test normal initialization
        mock_instance = MagicMock()
        mock_instance.list_sessions_cached.return_value = []
        mock_instance.list_agents_ultra_optimized.return_value = []
        mock_tmux.return_value = mock_instance

        result = fresh_simulator.runner.invoke(cli, ["status"])
        assert result.exit_code == 0

        # Test initialization failure
        mock_tmux.side_effect = Exception("TMUX not available")
        result = fresh_simulator.runner.invoke(cli, ["status"])
        # Should handle gracefully, possibly with warning
        assert result.exit_code in [0, 1]  # Accept either success or controlled failure


def test_command_filtering_and_discovery(fresh_simulator):
    """Test command filtering and discovery features."""
    # Test basic filtering
    result = fresh_simulator.runner.invoke(cli, ["reflect", "--filter", "setup"])
    assert result.exit_code == 0
    assert "setup" in result.output.lower()

    # Test regex filtering
    result = fresh_simulator.runner.invoke(cli, ["reflect", "--filter", "^status"])
    assert result.exit_code == 0

    # Test no match filtering
    result = fresh_simulator.runner.invoke(cli, ["reflect", "--filter", "nonexistent"])
    assert result.exit_code == 0
    assert "No commands match" in result.output


def test_error_handling_and_recovery(fresh_simulator):
    """Test error handling and recovery mechanisms."""
    # Test invalid command
    result = fresh_simulator.runner.invoke(cli, ["nonexistent-command"])
    assert result.exit_code != 0
    assert "No such command" in result.output

    # Test invalid options
    result = fresh_simulator.runner.invoke(cli, ["status", "--invalid-option"])
    assert result.exit_code != 0


def test_unicode_and_special_character_handling(fresh_simulator):
    """Test handling of unicode and special characters."""
    with fresh_simulator.runner.isolated_filesystem():
        # Create files with unicode names
        unicode_dir = Path("测试目录")
        unicode_dir.mkdir()

        os.chdir(unicode_dir)

        # CLI should still work
        result = fresh_simulator.runner.invoke(cli, ["reflect", "--format", "json"])
        assert result.exit_code == 0


@pytest.mark.parametrize(
    "command",
    [
        ["reflect"],
        ["status"],
        ["list"],
        ["setup", "check"],
    ],
)
def test_command_execution_in_various_environments(fresh_simulator, command):
    """Test command execution in various directory environments."""
    test_environments = [
        # Empty directory
        {},
        # Project with common files
        {
            "README.md": "# Test Project",
            "src": {},
            "tests": {},
            ".git": {},
        },
        # Deep nested structure
        {"project": {"src": {"main": {"app.py": "# Main app"}}}},
    ]

    for i, env_structure in enumerate(test_environments):
        with fresh_simulator.runner.isolated_filesystem():
            # Create environment structure
            for name, content in env_structure.items():
                path = Path(name)
                if isinstance(content, dict):
                    path.mkdir()
                    for subname, subcontent in content.items():
                        subpath = path / subname
                        if isinstance(subcontent, dict):
                            subpath.mkdir(parents=True)
                        else:
                            subpath.write_text(str(subcontent))
                else:
                    path.write_text(str(content))

            # Test command in this environment
            result = fresh_simulator.runner.invoke(cli, command)
            assert result.exit_code == 0, f"Command {command} failed in environment {i}: {result.output}"


def test_path_resolution_edge_cases(fresh_simulator):
    """Test path resolution with edge cases."""
    edge_cases = [
        "directory with spaces",
        "directory-with-hyphens",
        "directory_with_underscores",
        "UPPERCASE_DIRECTORY",
        "directory.with.dots",
    ]

    for case_name in edge_cases:
        with fresh_simulator.runner.isolated_filesystem():
            case_dir = Path(case_name)
            case_dir.mkdir()
            os.chdir(case_dir)

            # Test basic functionality
            result = fresh_simulator.runner.invoke(cli, ["reflect", "--format", "json"])
            assert result.exit_code == 0, f"Failed in directory: {case_name}"


def test_integration_with_python_path():
    """Test CLI works correctly with different Python path configurations."""
    # Test direct module execution
    result = subprocess.run(
        [sys.executable, "-c", "from tmux_orchestrator.cli import cli; cli(['--help'])"],
        capture_output=True,
        text=True,
        cwd="/workspaces/Tmux-Orchestrator",
    )

    assert result.returncode == 0
    assert "TMUX Orchestrator" in result.stdout


def test_memory_and_resource_efficiency(fresh_simulator):
    """Test CLI operations are memory and resource efficient."""
    import time

    import psutil

    # Measure memory before CLI operations
    process = psutil.Process()
    memory_before = process.memory_info().rss

    # Run several CLI operations
    commands = [
        ["reflect", "--format", "json"],
        ["status", "--json"],
        ["list", "--json"],
        ["setup", "check"],
    ]

    start_time = time.time()
    for command in commands:
        result = fresh_simulator.runner.invoke(cli, command)
        assert result.exit_code == 0

    end_time = time.time()
    memory_after = process.memory_info().rss

    # Basic performance checks
    execution_time = end_time - start_time
    memory_increase = memory_after - memory_before

    # Should complete reasonably quickly
    assert execution_time < 30.0, f"CLI operations took too long: {execution_time}s"

    # Memory increase should be reasonable (less than 100MB)
    assert memory_increase < 100 * 1024 * 1024, f"Excessive memory usage: {memory_increase} bytes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
