#!/usr/bin/env python3
"""
CLI Installation and Path Resolution Test Suite

This test suite validates the CLI functionality across different installation scenarios
and directory structures to prevent path resolution regressions.

Test Scenarios:
1. Fresh installation simulation (pip install tmux-orc)
2. Setup command testing in various directories
3. Path resolution validation across environments
4. Edge case testing (permissions, missing directories)
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# Import the main CLI
try:
    from tmux_orchestrator.cli import cli
except ImportError as e:
    pytest.skip(f"Cannot import CLI modules: {e}", allow_module_level=True)


class InstallationTestEnvironment:
    """Simulates different installation environments for testing."""

    def __init__(self, test_dir: Path):
        self.test_dir = test_dir
        self.original_cwd = os.getcwd()
        self.runner = CliRunner()

    def __enter__(self):
        os.chdir(self.test_dir)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.original_cwd)

    def create_project_structure(self, structure: Dict[str, Any]) -> None:
        """Create a directory structure from a nested dict."""

        def _create_structure(base_path: Path, struct: Dict[str, Any]):
            for name, content in struct.items():
                path = base_path / name
                if isinstance(content, dict):
                    path.mkdir(parents=True, exist_ok=True)
                    _create_structure(path, content)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if content is not None:
                        path.write_text(str(content))
                    else:
                        path.touch()

        _create_structure(self.test_dir, structure)


def test_cli_entry_point_exists():
    """Test that the CLI entry point is properly configured."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "tmux-orc" in result.output
    assert "TMUX Orchestrator" in result.output


def test_cli_reflects_available_commands():
    """Test that CLI reflection works and shows available commands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["reflect", "--format", "json"])

    assert result.exit_code == 0

    try:
        data = json.loads(result.output)
        assert isinstance(data, dict)
        # Should have core commands
        expected_commands = ["list", "status", "reflect", "quick-deploy"]
        for cmd in expected_commands:
            assert cmd in data, f"Missing command: {cmd}"
    except json.JSONDecodeError:
        pytest.fail(f"CLI reflect output is not valid JSON: {result.output}")


def test_fresh_installation_empty_directory():
    """Test CLI functionality in a completely empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with InstallationTestEnvironment(Path(temp_dir)) as env:
            # Test basic commands that should work without any setup
            result = env.runner.invoke(cli, ["--help"])
            assert result.exit_code == 0

            result = env.runner.invoke(cli, ["reflect"])
            assert result.exit_code == 0

            result = env.runner.invoke(cli, ["status", "--json"])
            assert result.exit_code == 0


def test_fresh_installation_project_directory():
    """Test CLI functionality in a typical project directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_structure = {
            "src": {
                "main.py": 'print("Hello World")',
                "utils": {"__init__.py": "", "helpers.py": "def helper(): pass"},
            },
            "tests": {"test_main.py": "def test_main(): pass"},
            "README.md": "# My Project",
            "requirements.txt": "requests\nflask\n",
            ".git": {"config": "[core]\n\trepositoryformatversion = 0"},
        }

        with InstallationTestEnvironment(Path(temp_dir)) as env:
            env.create_project_structure(project_structure)

            # Test commands in project context
            result = env.runner.invoke(cli, ["status", "--json"])
            assert result.exit_code == 0

            result = env.runner.invoke(cli, ["list", "--json"])
            assert result.exit_code == 0


def test_setup_command_paths():
    """Test setup command in various directory structures."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_structures = [
            # Empty directory
            {},
            # Simple project
            {"main.py": 'print("test")', "README.md": "# Test"},
            # Nested project
            {"project": {"src": {"app.py": "app = Flask(__name__)"}, "config": {"settings.py": "DEBUG = True"}}},
        ]

        for i, structure in enumerate(test_structures):
            test_subdir = Path(temp_dir) / f"test_{i}"
            test_subdir.mkdir()

            with InstallationTestEnvironment(test_subdir) as env:
                env.create_project_structure(structure)

                # Test CLI commands work in this structure
                result = env.runner.invoke(cli, ["reflect", "--format", "json"])
                assert result.exit_code == 0, f"Failed in structure {i}: {result.output}"


@pytest.mark.parametrize(
    "command",
    [
        ["list"],
        ["status"],
        ["reflect"],
        ["reflect", "--format", "json"],
        ["reflect", "--format", "markdown"],
        ["quick-deploy", "--help"],  # Just test help, don't actually deploy
    ],
)
def test_command_execution_different_directories(command: List[str]):
    """Test that core commands work from different working directories."""
    test_dirs = []

    # Create test directories
    with tempfile.TemporaryDirectory() as temp_base:
        for i in range(3):
            test_dir = Path(temp_base) / f"test_dir_{i}"
            test_dir.mkdir()
            test_dirs.append(test_dir)

        for test_dir in test_dirs:
            with InstallationTestEnvironment(test_dir) as env:
                result = env.runner.invoke(cli, command)
                assert result.exit_code == 0, f"Command {command} failed in {test_dir}: {result.output}"


def test_config_resolution():
    """Test configuration file resolution across different scenarios."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_scenarios = [
            # No config file
            {},
            # Config in working directory
            {"tmux-orc.yaml": "monitor:\n  interval: 30\n"},
            # Config in subdirectory
            {"config": {"tmux-orc.yaml": "monitor:\n  interval: 60\n"}},
        ]

        for i, scenario in enumerate(config_scenarios):
            test_subdir = Path(temp_dir) / f"config_test_{i}"
            test_subdir.mkdir()

            with InstallationTestEnvironment(test_subdir) as env:
                env.create_project_structure(scenario)

                # Test CLI loads without config errors
                result = env.runner.invoke(cli, ["--verbose", "status"])
                # Should not fail, even if no config file exists
                assert result.exit_code == 0, f"Config test {i} failed: {result.output}"


def test_permission_scenarios():
    """Test CLI behavior with different permission scenarios."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "perm_test"
        test_dir.mkdir()

        with InstallationTestEnvironment(test_dir) as env:
            # Create a readonly directory
            readonly_dir = test_dir / "readonly"
            readonly_dir.mkdir()
            readonly_dir.chmod(0o555)  # Read + execute only

            try:
                # Test CLI in readonly directory
                os.chdir(readonly_dir)
                result = env.runner.invoke(cli, ["status", "--json"])
                # Should handle readonly directories gracefully
                assert result.exit_code == 0

            finally:
                # Restore permissions for cleanup
                readonly_dir.chmod(0o755)


def test_path_resolution_edge_cases():
    """Test edge cases for path resolution."""
    with tempfile.TemporaryDirectory() as temp_dir:
        edge_cases = {
            "spaces in name": {"file with spaces.txt": "content"},
            "unicode-name-测试": {"unicode-file-测试.py": 'print("unicode")'},
            "very-long-name-" + "x" * 100: {"nested": {"deep": {"file.txt": "deep content"}}},
        }

        for case_name, structure in edge_cases.items():
            case_dir = Path(temp_dir) / case_name
            case_dir.mkdir()

            with InstallationTestEnvironment(case_dir) as env:
                env.create_project_structure(structure)

                # Test basic CLI functionality
                result = env.runner.invoke(cli, ["reflect", "--format", "json"])
                assert result.exit_code == 0, f"Edge case '{case_name}' failed: {result.output}"


@patch("tmux_orchestrator.utils.tmux.TMUXManager")
def test_tmux_manager_initialization(mock_tmux_manager):
    """Test that TMUXManager initializes correctly in different scenarios."""
    mock_instance = MagicMock()
    mock_tmux_manager.return_value = mock_instance

    with tempfile.TemporaryDirectory() as temp_dir:
        with InstallationTestEnvironment(Path(temp_dir)) as env:
            result = env.runner.invoke(cli, ["status"])

            # TMUXManager should be initialized
            mock_tmux_manager.assert_called()
            assert result.exit_code == 0


def test_json_output_consistency():
    """Test that JSON output is consistent across different environments."""
    json_commands = [["list", "--json"], ["status", "--json"], ["reflect", "--format", "json"]]

    results = []

    with tempfile.TemporaryDirectory() as temp_dir:
        for i in range(2):  # Test in 2 different directories
            test_subdir = Path(temp_dir) / f"json_test_{i}"
            test_subdir.mkdir()

            with InstallationTestEnvironment(test_subdir) as env:
                for command in json_commands:
                    result = env.runner.invoke(cli, command)
                    assert result.exit_code == 0

                    # Validate JSON structure
                    try:
                        json_data = json.loads(result.output)
                        results.append((command, json_data))
                    except json.JSONDecodeError:
                        pytest.fail(f"Invalid JSON output for {command}: {result.output}")

    # Verify JSON structure consistency
    for command, data in results:
        assert isinstance(data, (dict, list)), f"Unexpected JSON type for {command}"


def test_cli_help_accessibility():
    """Test that help is accessible for all commands."""
    runner = CliRunner()

    # Test main help
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output

    # Test reflect to discover all commands
    result = runner.invoke(cli, ["reflect", "--format", "json"])
    assert result.exit_code == 0

    try:
        commands_data = json.loads(result.output)

        # Test help for each top-level command
        for command_name in commands_data.keys():
            result = runner.invoke(cli, [command_name, "--help"])
            assert result.exit_code == 0, f"Help failed for command: {command_name}"
            assert "Usage:" in result.output

    except json.JSONDecodeError:
        pytest.skip("Could not parse CLI reflection output")


if __name__ == "__main__":
    # Run specific tests for debugging
    pytest.main([__file__, "-v"])
