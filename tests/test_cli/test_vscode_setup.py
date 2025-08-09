"""Tests for VS Code setup commands."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.setup import vscode_setup


class TestVSCodeSetup:
    """Test cases for VS Code setup commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI runner for testing."""
        return CliRunner()

    def test_vscode_setup_help(self, runner: CliRunner) -> None:
        """Test vscode-setup help command."""
        result = runner.invoke(vscode_setup, ["--help"])
        assert result.exit_code == 0
        assert "VS Code integration and project setup" in result.output

    def test_vscode_command_help(self, runner: CliRunner) -> None:
        """Test vscode-setup vscode help command."""
        result = runner.invoke(vscode_setup, ["vscode", "--help"])
        assert result.exit_code == 0
        assert "Generate VS Code tasks.json" in result.output

    def test_vscode_setup_creates_tasks_json(self, runner: CliRunner) -> None:
        """Test vscode setup creates tasks.json file."""
        with runner.isolated_filesystem():
            # Run vscode setup
            result = runner.invoke(vscode_setup, ["vscode", "--force"])

            assert result.exit_code == 0
            assert "VS Code tasks.json created successfully" in result.output

            # Check that .vscode/tasks.json was created
            tasks_file = Path(".vscode/tasks.json")
            assert tasks_file.exists()

            # Verify JSON content
            with open(tasks_file) as f:
                tasks_config = json.load(f)

            assert "version" in tasks_config
            assert tasks_config["version"] == "2.0.0"
            assert "tasks" in tasks_config
            assert len(tasks_config["tasks"]) > 0
            assert "inputs" in tasks_config

    def test_vscode_setup_minimal_mode(self, runner: CliRunner) -> None:
        """Test vscode setup with minimal flag."""
        with runner.isolated_filesystem():
            # Run vscode setup with minimal flag
            result = runner.invoke(vscode_setup, ["vscode", "--force", "--minimal"])

            assert result.exit_code == 0

            # Check that tasks.json has fewer tasks
            tasks_file = Path(".vscode/tasks.json")
            with open(tasks_file) as f:
                tasks_config = json.load(f)

            # Minimal mode should have fewer tasks
            assert len(tasks_config["tasks"]) <= 3

    def test_vscode_setup_existing_file_no_force(self, runner: CliRunner) -> None:
        """Test vscode setup with existing file and no force flag."""
        with runner.isolated_filesystem():
            # Create existing tasks.json
            vscode_dir = Path(".vscode")
            vscode_dir.mkdir()
            tasks_file = vscode_dir / "tasks.json"
            tasks_file.write_text('{"version": "1.0.0"}')

            # Run without force - should prompt and be cancelled
            result = runner.invoke(vscode_setup, ["vscode"], input="n\n")

            assert result.exit_code == 0
            assert "tasks.json already exists" in result.output
            assert "Setup cancelled" in result.output

            # Original file should remain unchanged
            with open(tasks_file) as f:
                content = json.load(f)
            assert content["version"] == "1.0.0"

    def test_vscode_setup_custom_project_dir(self, runner: CliRunner) -> None:
        """Test vscode setup with custom project directory."""
        with runner.isolated_filesystem():
            # Create custom project directory
            project_dir = Path("my-project")
            project_dir.mkdir()

            # Run vscode setup
            result = runner.invoke(vscode_setup, ["vscode", "--project-dir", "my-project", "--force"])

            assert result.exit_code == 0

            # Check that tasks.json was created in project directory
            tasks_file = project_dir / ".vscode" / "tasks.json"
            assert tasks_file.exists()

    def test_workspace_command(self, runner: CliRunner) -> None:
        """Test workspace command creates workspace file."""
        with runner.isolated_filesystem():
            result = runner.invoke(vscode_setup, ["workspace"])

            assert result.exit_code == 0
            assert "VS Code workspace created" in result.output

            # Check that workspace file was created
            workspace_files = list(Path(".").glob("*.code-workspace"))
            assert len(workspace_files) == 1

    def test_workspace_command_custom_name(self, runner: CliRunner) -> None:
        """Test workspace command with custom name."""
        with runner.isolated_filesystem():
            result = runner.invoke(vscode_setup, ["workspace", "--name", "my-workspace"])

            assert result.exit_code == 0

            # Check that workspace file with custom name was created
            workspace_file = Path("my-workspace.code-workspace")
            assert workspace_file.exists()

            # Verify workspace content
            with open(workspace_file) as f:
                workspace_config = json.load(f)

            assert "folders" in workspace_config
            assert "settings" in workspace_config
            assert "extensions" in workspace_config

    def test_extensions_command(self, runner: CliRunner) -> None:
        """Test extensions command lists recommended extensions."""
        result = runner.invoke(vscode_setup, ["extensions"])

        assert result.exit_code == 0
        assert "Recommended VS Code Extensions" in result.output
        assert "ms-python.python" in result.output
        assert "charliermarsh.ruff" in result.output
        assert "code --install-extension" in result.output

    def test_config_command(self, runner: CliRunner) -> None:
        """Test config command creates settings.json."""
        with runner.isolated_filesystem():
            result = runner.invoke(vscode_setup, ["config"])

            assert result.exit_code == 0
            assert "VS Code settings configured" in result.output

            # Check that settings.json was created
            settings_file = Path(".vscode/settings.json")
            assert settings_file.exists()

            # Verify settings content
            with open(settings_file) as f:
                settings = json.load(f)

            assert "python.defaultInterpreterPath" in settings
            assert "python.testing.pytestEnabled" in settings
            assert settings["python.testing.pytestEnabled"] is True

    def test_config_command_interactive(self, runner: CliRunner) -> None:
        """Test config command in interactive mode."""
        with runner.isolated_filesystem():
            # Provide input for interactive prompts
            result = runner.invoke(
                vscode_setup,
                ["config", "--interactive"],
                input="./custom/venv/bin/python\ny\ny\n"
            )

            assert result.exit_code == 0

            # Check custom settings
            settings_file = Path(".vscode/settings.json")
            with open(settings_file) as f:
                settings = json.load(f)

            assert settings["python.defaultInterpreterPath"] == "./custom/venv/bin/python"

    def test_generated_tasks_structure(self, runner: CliRunner) -> None:
        """Test the structure of generated tasks."""
        with runner.isolated_filesystem():
            result = runner.invoke(vscode_setup, ["vscode", "--force"])

            assert result.exit_code == 0

            # Load and verify task structure
            tasks_file = Path(".vscode/tasks.json")
            with open(tasks_file) as f:
                tasks_config = json.load(f)

            # Check some specific tasks exist
            task_labels = [task["label"] for task in tasks_config["tasks"]]
            assert "🎭 Start Orchestrator" in task_labels
            assert "📊 System Status" in task_labels

            # Verify task properties
            for task in tasks_config["tasks"]:
                assert "label" in task
                assert "type" in task
                assert "command" in task
                assert task["type"] == "shell"
                assert task["command"] == "tmux-orc"
