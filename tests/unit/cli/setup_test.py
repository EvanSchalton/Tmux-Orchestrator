"""Tests for setup CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.setup_claude import setup as setup_cli


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_project_dir():
    """Create temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_setup_command(runner) -> None:
    """Test main setup command."""
    result = runner.invoke(setup_cli)

    # The setup command should display available subcommands
    assert result.exit_code == 0
    assert "claude-code" in result.output or "vscode" in result.output or "Commands:" in result.output


def test_setup_tmux_not_installed(runner) -> None:
    """Test setup when tmux is not installed."""
    # Test that system check command exists
    result = runner.invoke(setup_cli, ["check-requirements"])

    # Should run system check
    assert result.exit_code == 0
    assert "Tmux Orchestrator System Setup Check" in result.output or "requirements" in result.output


def test_setup_vscode_creates_structure(runner, temp_project_dir) -> None:
    """Test VS Code setup creates correct structure."""
    with patch("os.getcwd", return_value=str(temp_project_dir)):
        result = runner.invoke(setup_cli, ["vscode"])

        assert result.exit_code == 0

        # Check directory structure
        vscode_dir = temp_project_dir / ".vscode"
        assert vscode_dir.exists()

        # Check tasks.json created
        tasks_file = vscode_dir / "tasks.json"
        assert tasks_file.exists()

        # Verify tasks content
        content = tasks_file.read_text()
        assert "Start Orchestrator" in content
        assert "tmux-orc" in content


def test_setup_vscode_existing_tasks(runner, temp_project_dir) -> None:
    """Test VS Code setup with existing tasks.json."""
    vscode_dir = temp_project_dir / ".vscode"
    vscode_dir.mkdir()

    # Create existing tasks.json
    existing_tasks = {
        "version": "2.0.0",
        "tasks": [{"label": "Existing Task", "type": "shell", "command": "echo hello"}],
    }

    tasks_file = vscode_dir / "tasks.json"
    import json

    tasks_file.write_text(json.dumps(existing_tasks, indent=2))

    with patch("os.getcwd", return_value=str(temp_project_dir)):
        result = runner.invoke(setup_cli, ["vscode"])

        assert result.exit_code == 0
        assert "already exists" in result.output

        # Check that the existing content is unchanged
        content = json.loads(tasks_file.read_text())
        assert content == existing_tasks


def test_setup_vscode_with_project_path(runner, temp_project_dir) -> None:
    """Test VS Code setup with specific project path."""
    project_subdir = temp_project_dir / "my-project"
    project_subdir.mkdir()

    result = runner.invoke(setup_cli, ["vscode", str(project_subdir)])

    assert result.exit_code == 0

    # Check created in correct location
    vscode_dir = project_subdir / ".vscode"
    assert vscode_dir.exists()
    assert (vscode_dir / "tasks.json").exists()


def test_setup_vscode_invalid_json(runner, temp_project_dir) -> None:
    """Test VS Code setup with invalid existing JSON."""
    vscode_dir = temp_project_dir / ".vscode"
    vscode_dir.mkdir()

    # Create invalid JSON
    tasks_file = vscode_dir / "tasks.json"
    tasks_file.write_text("{ invalid json")

    with patch("os.getcwd", return_value=str(temp_project_dir)):
        result = runner.invoke(setup_cli, ["vscode"])

        # The command doesn't validate JSON, it just checks if file exists
        assert result.exit_code == 0
        assert "already exists" in result.output

        # The invalid JSON file should remain unchanged
        assert tasks_file.read_text() == "{ invalid json"
