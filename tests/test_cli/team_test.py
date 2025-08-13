"""Tests for team CLI commands."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.team import team


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


def test_team_deploy_frontend(runner, mock_tmux) -> None:
    """Test deploying a frontend team."""
    with patch("tmux_orchestrator.cli.team.deploy_standard_team") as mock_deploy:
        mock_deploy.return_value = (True, "Frontend team deployed successfully")

        result = runner.invoke(team, ["deploy", "frontend", "3"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Deploying frontend team" in result.output
        mock_deploy.assert_called_once()
        # Check the arguments
        args = mock_deploy.call_args[0]
        assert args[1] == "frontend"  # team_type
        assert args[2] == 3  # size


def test_team_deploy_backend(runner, mock_tmux) -> None:
    """Test deploying a backend team."""
    with patch("tmux_orchestrator.cli.team.deploy_standard_team") as mock_deploy:
        mock_deploy.return_value = (True, "Backend team deployed successfully")

        result = runner.invoke(team, ["deploy", "backend", "2"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Deploying backend team" in result.output


def test_team_deploy_fullstack(runner, mock_tmux) -> None:
    """Test deploying a fullstack team."""
    with patch("tmux_orchestrator.cli.team.deploy_standard_team") as mock_deploy:
        mock_deploy.return_value = (True, "Fullstack team deployed successfully")

        result = runner.invoke(team, ["deploy", "fullstack", "5"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Deploying fullstack team" in result.output


def test_team_list_all(runner, mock_tmux) -> None:
    """Test listing all teams."""
    with patch("tmux_orchestrator.cli.team.list_all_teams") as mock_list:
        mock_list.return_value = [
            {"name": "project1", "windows": 5, "agents": 5, "status": "healthy", "created": "2024-01-01"},
            {"name": "project2", "windows": 3, "agents": 3, "status": "healthy", "created": "2024-01-01"},
        ]

        result = runner.invoke(team, ["list"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "project1" in result.output
        assert "project2" in result.output
        assert "healthy" in result.output


def test_team_status_specific_session(runner, mock_tmux) -> None:
    """Test getting status of specific team."""
    with patch("tmux_orchestrator.cli.team.get_team_status") as mock_status:
        mock_status.return_value = {
            "session_info": {"name": "project1", "attached": "1", "created": "2024-01-01"},
            "windows": [
                {
                    "index": "0",
                    "name": "orchestrator",
                    "type": "orchestrator",
                    "status": "active",
                    "last_activity": "5m ago",
                },
                {"index": "1", "name": "pm", "type": "pm", "status": "active", "last_activity": "2m ago"},
                {"index": "2", "name": "dev", "type": "developer", "status": "idle", "last_activity": "45m ago"},
            ],
            "summary": {"total_windows": 3, "active_agents": 2},
        }

        result = runner.invoke(team, ["status", "project1"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "orchestrator" in result.output
        assert "active" in result.output
        assert "idle" in result.output


def test_team_list_json(runner, mock_tmux) -> None:
    """Test listing all teams in JSON format."""
    with patch("tmux_orchestrator.cli.team.list_all_teams") as mock_list:
        mock_list.return_value = [
            {"name": "frontend-app", "windows": 5, "agents": 5, "status": "healthy", "created": "2024-01-01"},
            {"name": "backend-api", "windows": 4, "agents": 4, "status": "healthy", "created": "2024-01-02"},
        ]

        result = runner.invoke(team, ["list", "--json"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        # Should be valid JSON
        import json

        data = json.loads(result.output)
        assert len(data) == 2


def test_team_broadcast(runner, mock_tmux) -> None:
    """Test broadcasting message to team."""
    # Mock list_windows to prevent iteration error
    mock_tmux.list_windows.return_value = [
        {"window": "0", "name": "PM", "panes": "1", "index": "0"},
        {"window": "1", "name": "Dev1", "panes": "1", "index": "1"},
    ]

    with patch("tmux_orchestrator.cli.team.broadcast_to_team") as mock_broadcast:
        # Return tuple (success, summary, results) as expected by CLI
        mock_broadcast.return_value = (
            True,
            "Broadcast successful: 5 messages sent",
            [{"target": f"project1:{i}", "window_name": f"Agent{i}", "success": True} for i in range(5)],
        )

        result = runner.invoke(
            team,
            ["broadcast", "project1", "Team meeting in 5 minutes"],
            obj={"tmux": mock_tmux},
        )

        assert result.exit_code == 0
        assert "Message sent to" in result.output or "Broadcast successful" in result.output
        mock_broadcast.assert_called_once_with(mock_tmux, "project1", "Team meeting in 5 minutes")


def test_team_broadcast_with_failures(runner, mock_tmux) -> None:
    """Test broadcasting with some failures."""
    # Mock list_windows to prevent iteration error
    mock_tmux.list_windows.return_value = [
        {"window": "0", "name": "PM", "panes": "1", "index": "0"},
        {"window": "1", "name": "Dev1", "panes": "1", "index": "1"},
        {"window": "2", "name": "Dev2", "panes": "1", "index": "2"},
        {"window": "3", "name": "QA", "panes": "1", "index": "3"},
        {"window": "4", "name": "DevOps", "panes": "1", "index": "4"},
    ]

    with patch("tmux_orchestrator.cli.team.broadcast_to_team") as mock_broadcast:
        # Return tuple (success, summary, results) as expected by CLI
        mock_broadcast.return_value = (
            True,
            "Broadcast completed: 3 successful, 2 failed",
            [
                {"target": "project1:0", "window_name": "PM", "success": True},
                {"target": "project1:1", "window_name": "Dev1", "success": True},
                {"target": "project1:2", "window_name": "Dev2", "success": True},
                {"target": "project1:3", "window_name": "QA", "success": False},
                {"target": "project1:4", "window_name": "DevOps", "success": False},
            ],
        )

        result = runner.invoke(team, ["broadcast", "project1", "Status update"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Message sent to PM" in result.output or "3 successful" in result.output
        assert "Failed to send message" in result.output or "2 failed" in result.output


def test_team_recover(runner, mock_tmux) -> None:
    """Test recovering failed agents in team."""
    with patch("tmux_orchestrator.cli.team.recover_team_agents") as mock_recover:
        mock_recover.return_value = (True, "Recovery complete: 1 agent restarted")

        result = runner.invoke(team, ["recover", "project1"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Recovering failed agents" in result.output
        assert "Recovery complete" in result.output or "agent restarted" in result.output
        mock_recover.assert_called_once_with(mock_tmux, "project1")


def test_team_compose(runner, mock_tmux) -> None:
    """Test team compose command (if exists)."""
    # Check if compose command exists
    if "compose" not in team.commands:
        # Skip test if command doesn't exist
        return

    result = runner.invoke(team, ["compose", "project1"], obj={"tmux": mock_tmux})
    # Just check it doesn't crash
    assert result.exit_code in [0, 2]  # 0 for success, 2 for missing arguments


def test_team_group_exists() -> None:
    """Test that team command group exists and has expected subcommands."""
    assert callable(team)

    command_names = list(team.commands.keys())
    expected_commands = {
        "deploy",
        "status",
        "list",
        "broadcast",
        "recover",
    }

    assert expected_commands.issubset(set(command_names))
