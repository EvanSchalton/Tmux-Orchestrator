"""Tests for recovery CLI commands."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.recovery import recovery


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


def test_recovery_start_daemon(runner, mock_tmux) -> None:
    """Test starting recovery daemon."""
    with patch("tmux_orchestrator.core.recovery.recovery_daemon.run_recovery_daemon"):
        # Run with daemon flag and mock the background process
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            result = runner.invoke(recovery, ["start", "--daemon"], obj={"tmux": mock_tmux})

            assert result.exit_code == 0
            assert "Recovery daemon started" in result.output


def test_recovery_stop_daemon(runner, mock_tmux) -> None:
    """Test stopping recovery daemon."""
    with patch("pathlib.Path.exists") as mock_exists:
        with patch("builtins.open", create=True) as mock_open:
            with patch("os.kill"):
                mock_exists.return_value = True
                mock_open.return_value.__enter__.return_value.read.return_value = "12345"

                result = runner.invoke(recovery, ["stop"], obj={"tmux": mock_tmux})

                assert result.exit_code == 0
                assert "Stopping recovery daemon" in result.output


def test_recovery_status(runner, mock_tmux) -> None:
    """Test recovery status command."""
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = False
        mock_tmux.list_sessions.return_value = [{"name": "session1", "windows": "3"}]
        mock_tmux.list_agents.return_value = [{"target": "session1:0", "type": "orchestrator"}]

        result = runner.invoke(recovery, ["status"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Recovery System Status" in result.output


def test_recovery_test_single_agent(runner, mock_tmux) -> None:
    """Test recovery test command with single agent."""
    with patch("tmux_orchestrator.core.recovery.coordinate_agent_recovery") as mock_coordinate:
        mock_coordinate.return_value = (
            True,
            "Recovery test successful",
            {"health_checks": [{"is_healthy": True}], "recovery_attempted": False},
        )

        result = runner.invoke(recovery, ["test", "project:0"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Testing recovery system" in result.output
        assert "Recovery test successful" in result.output


def test_recovery_test_comprehensive(runner, mock_tmux) -> None:
    """Test comprehensive recovery test suite."""
    with patch("tmux_orchestrator.core.recovery.recovery_test.run_recovery_system_test") as mock_test:
        mock_test.return_value = {
            "summary": {
                "total_tests": 10,
                "tests_passed": 8,
                "tests_failed": 2,
                "overall_success_rate": 80.0,
                "test_breakdown": {
                    "health_check": {"passed": 5, "failed": 1, "success_rate": 83.3},
                    "recovery": {"passed": 3, "failed": 1, "success_rate": 75.0},
                },
            },
            "target_agents": ["project:0", "project:1"],
            "total_duration": 45.2,
            "test_session_id": "test-123",
        }

        result = runner.invoke(recovery, ["test", "--comprehensive"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Comprehensive Recovery Test Results" in result.output
        assert "Tests Run: 10" in result.output


def test_recovery_test_no_restart(runner, mock_tmux) -> None:
    """Test recovery test with no-restart flag."""
    with patch("tmux_orchestrator.core.recovery.coordinate_agent_recovery") as mock_coordinate:
        mock_coordinate.return_value = (True, "Detection successful", {"recovery_attempted": False})

        result = runner.invoke(recovery, ["test", "project:0", "--no-restart"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "detection-only mode" in result.output
        # Verify enable_auto_restart is False
        mock_coordinate.assert_called_once()
        assert mock_coordinate.call_args[1]["enable_auto_restart"] is False


def test_recovery_group_exists() -> None:
    """Test that recovery command group exists and has expected subcommands."""
    assert callable(recovery)

    command_names = list(recovery.commands.keys())
    expected_commands = {"start", "stop", "status", "test"}

    assert expected_commands.issubset(set(command_names))
