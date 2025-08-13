"""Tests for execute CLI command."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.execute import execute

# Remove the module-level skip since we'll fix the tests


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def sample_prd():
    """Create a sample PRD file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(
            """# Task Management System

## Overview
Build a CLI-based task management system.

## Requirements
1. Create, update, delete tasks
2. List and filter tasks
3. Persistent storage
4. Command-line interface

## Technical Requirements
- Python-based CLI using Click
- SQLite for storage
- Rich for terminal UI
"""
        )
        yield f.name
    os.unlink(f.name)


def test_execute_with_prd_file(runner, mock_tmux, temp_orchestrator_dir, sample_prd) -> None:
    """Test executing a PRD file."""
    # Mock subprocess calls for task creation and team composition
    with patch("subprocess.run") as mock_run:
        # Mock successful task creation
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # tasks create
            Mock(returncode=0, stdout="", stderr=""),  # team compose
        ]

        # Mock deploy_standard_team
        with patch("tmux_orchestrator.core.team_operations.deploy_team.deploy_standard_team") as mock_deploy:
            mock_deploy.return_value = (True, "Team deployed successfully")
            mock_tmux.has_session.return_value = False
            mock_tmux.send_message.return_value = True
            mock_tmux.list_windows.return_value = []

            # Create a proper context object
            ctx_obj = {"tmux": mock_tmux}
            result = runner.invoke(
                execute, [sample_prd, "--team-type", "fullstack", "--no-monitor", "--no-wait-for-tasks"], obj=ctx_obj
            )

            # Print output for debugging
            if result.exit_code != 0:
                print("Exit code:", result.exit_code)
                print("Output:", result.output)
                print("Exception:", result.exception)

            assert result.exit_code == 0
            assert "Executing PRD" in result.output
            assert "PRD execution initiated successfully" in result.output
            assert "execution started!" in result.output.lower()


def test_execute_existing_session(runner, mock_tmux, temp_orchestrator_dir, sample_prd) -> None:
    """Test executing when session already exists."""
    # Mock subprocess call for task creation
    with patch("subprocess.run") as mock_run:
        with patch("subprocess.Popen") as mock_popen:  # Mock daemon startup
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            mock_popen.return_value = Mock(pid=12345)

            # Mock that session already exists
            mock_tmux.has_session.return_value = True

            ctx_obj = {"tmux": mock_tmux}
            result = runner.invoke(
                execute, [sample_prd, "--team-type", "backend", "--no-monitor", "--no-wait-for-tasks"], obj=ctx_obj
            )

        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            print(f"Exception: {result.exception}")

        assert result.exit_code == 0
        assert "Session" in result.output and "already exists" in result.output


def test_execute_with_team_type(runner, mock_tmux, temp_orchestrator_dir, sample_prd) -> None:
    """Test executing with specific team type."""
    # Mock subprocess calls
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # tasks create
            Mock(returncode=0, stdout="", stderr=""),  # team compose (skipped for backend)
        ]

        # Mock deploy_standard_team
        with patch("tmux_orchestrator.core.team_operations.deploy_team.deploy_standard_team") as mock_deploy:
            mock_deploy.return_value = (True, "Team deployed successfully")
            mock_tmux.has_session.return_value = False
            mock_tmux.send_message.return_value = True
            mock_tmux.list_windows.return_value = []

            result = runner.invoke(
                execute,
                [sample_prd, "--team-type", "backend", "--no-monitor", "--no-wait-for-tasks"],
                obj={"tmux": mock_tmux},
            )

            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
                if result.exception:
                    import traceback

                    traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

            assert result.exit_code == 0
            assert "Executing PRD" in result.output
            # Verify deploy_standard_team was called with correct args
            # The project name is derived from the temp filename (which is random)
            args = mock_deploy.call_args[0]
            assert args[1] == "backend"  # team_type
            assert args[2] == 5  # size
            # args[3] is the project name which is derived from temp filename


def test_execute_skip_team_planning(runner, mock_tmux, temp_orchestrator_dir, sample_prd) -> None:
    """Test executing with skip team planning."""
    # Mock subprocess calls
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # tasks create
            # No team compose call when skip-planning is used
        ]

        # Mock deploy_standard_team
        with patch("tmux_orchestrator.core.team_operations.deploy_team.deploy_standard_team") as mock_deploy:
            mock_deploy.return_value = (True, "Team deployed successfully")
            mock_tmux.has_session.return_value = False
            mock_tmux.send_message.return_value = True
            mock_tmux.list_windows.return_value = []

            result = runner.invoke(
                execute, [sample_prd, "--skip-planning", "--no-monitor", "--no-wait-for-tasks"], obj={"tmux": mock_tmux}
            )

            assert result.exit_code == 0
            assert "Executing PRD" in result.output
            # Should use default custom team type
            assert "Team: custom" in result.output


def test_execute_with_team_size(runner, mock_tmux, temp_orchestrator_dir, sample_prd) -> None:
    """Test executing with custom team size."""
    # Mock subprocess calls
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # tasks create
            Mock(returncode=0, stdout="", stderr=""),  # team compose
        ]

        # Mock deploy_standard_team
        with patch("tmux_orchestrator.core.team_operations.deploy_team.deploy_standard_team") as mock_deploy:
            mock_deploy.return_value = (True, "Team deployed successfully")
            mock_tmux.has_session.return_value = False
            mock_tmux.send_message.return_value = True
            mock_tmux.list_windows.return_value = []

            result = runner.invoke(
                execute,
                [sample_prd, "--team-type", "fullstack", "--team-size", "8", "--no-monitor", "--no-wait-for-tasks"],
                obj={"tmux": mock_tmux},
            )

            assert result.exit_code == 0
            assert "Executing PRD" in result.output
            assert "Team: fullstack (8 agents)" in result.output
            # Verify deploy was called with correct args: tmux, team_type, size, name
            args = mock_deploy.call_args[0]
            assert args[1] == "fullstack"  # team_type (fullstack gets passed to deploy)
            assert args[2] == 8  # size
            # args[3] is the project name which is derived from temp filename


def test_execute_nonexistent_file(runner, mock_tmux) -> None:
    """Test executing non-existent file."""
    result = runner.invoke(execute, ["nonexistent.md"], obj={"tmux": mock_tmux})

    # Should exit with code 2 because Click validates file existence
    assert result.exit_code == 2
    assert "does not exist" in result.output.lower()


def test_execute_project_creation(runner, mock_tmux, temp_orchestrator_dir, sample_prd) -> None:
    """Test that execute creates project structure."""
    # Mock subprocess calls
    with patch("subprocess.run") as mock_run:
        with patch("subprocess.Popen"):  # For daemon startup
            # Mock successful subprocess calls
            mock_run.side_effect = [
                Mock(returncode=0, stdout="Project created", stderr=""),  # tasks create
                Mock(returncode=0, stdout="Team composed", stderr=""),  # team compose
            ]

            # Mock deploy_standard_team
            with patch("tmux_orchestrator.core.team_operations.deploy_team.deploy_standard_team") as mock_deploy:
                mock_deploy.return_value = (True, "Team deployed successfully")
                mock_tmux.has_session.return_value = False
                mock_tmux.send_message.return_value = True
                mock_tmux.list_windows.return_value = []

                result = runner.invoke(
                    execute,
                    [sample_prd, "--team-type", "backend", "--no-monitor", "--no-wait-for-tasks"],
                    obj={"tmux": mock_tmux},
                )

                assert result.exit_code == 0
                # Verify project creation via subprocess
                calls = mock_run.call_args_list
                assert len(calls) >= 1
                # First call should be tasks create
                assert "tasks" in calls[0][0][0]
                assert "create" in calls[0][0][0]


def test_execute_function_exists() -> None:
    """Test that execute function exists and is callable."""
    assert callable(execute)

    # Check it's a Click command
    assert hasattr(execute, "params")

    # Check expected options based on actual implementation
    param_names = [p.name for p in execute.params]
    assert "team_type" in param_names
    assert "team_size" in param_names  # Changed from agents
    assert "skip_planning" in param_names  # Changed from skip_team_planning
    assert "project_name" in param_names
    assert "no_monitor" in param_names
