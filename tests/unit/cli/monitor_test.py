"""Tests for monitor CLI commands and daemon functionality."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.monitor import monitor


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_pid_file():
    """Create temporary PID file location."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        pid_file = f.name
    yield pid_file
    # Cleanup
    if os.path.exists(pid_file):
        os.unlink(pid_file)


def test_monitor_start_success(runner, mock_tmux, temp_pid_file) -> None:
    """Test starting the monitor daemon."""
    with patch("tmux_orchestrator.core.monitor.IdleMonitor") as mock_idle_monitor:
        mock_instance = Mock()
        mock_idle_monitor.return_value = mock_instance
        mock_instance.is_running.return_value = False
        mock_instance.start.return_value = 12345

        result = runner.invoke(monitor, ["start"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Monitor daemon started successfully" in result.output or "started" in result.output.lower()
        mock_instance.start.assert_called_once_with(10)


def test_monitor_start_already_running(runner, mock_tmux, temp_pid_file) -> None:
    """Test starting monitor when already running."""
    with patch("tmux_orchestrator.core.monitor.IdleMonitor") as mock_idle_monitor:
        # Import the actual exception class
        from tmux_orchestrator.core.monitor import DaemonAlreadyRunningError

        mock_instance = Mock()
        mock_idle_monitor.return_value = mock_instance
        # Make start() raise DaemonAlreadyRunningError with required pid_file argument
        mock_instance.start.side_effect = DaemonAlreadyRunningError("Already running", temp_pid_file)

        result = runner.invoke(monitor, ["start"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "already running" in result.output.lower()


def test_monitor_stop_success(runner, mock_tmux, temp_pid_file) -> None:
    """Test stopping the monitor daemon."""
    with patch("tmux_orchestrator.core.monitor.IdleMonitor") as mock_idle_monitor:
        mock_instance = Mock()
        mock_idle_monitor.return_value = mock_instance
        mock_instance.is_running.return_value = True
        mock_instance.stop.return_value = True

        result = runner.invoke(monitor, ["stop"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "stopped successfully" in result.output.lower() or "stop signal sent" in result.output.lower()
        mock_instance.stop.assert_called_once()


def test_monitor_stop_not_running(runner, mock_tmux, temp_pid_file) -> None:
    """Test stopping monitor when not running."""
    with patch("tmux_orchestrator.core.monitor.IdleMonitor") as mock_idle_monitor:
        mock_instance = Mock()
        mock_idle_monitor.return_value = mock_instance
        # Mock the supervisor to indicate daemon is not running
        mock_instance.supervisor = Mock()
        mock_instance.supervisor.is_daemon_running.return_value = False

        # Make sure PID file doesn't exist (simulates not running)
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False

            result = runner.invoke(monitor, ["stop"], obj={"tmux": mock_tmux})

            assert result.exit_code == 0
            assert "not running" in result.output.lower()


def test_monitor_status_running(runner, mock_tmux, temp_pid_file) -> None:
    """Test monitor status when running."""
    with patch("tmux_orchestrator.core.monitor.IdleMonitor") as mock_idle_monitor:
        mock_instance = Mock()
        mock_idle_monitor.return_value = mock_instance
        mock_instance.is_running.return_value = True

        # Mock the status method to print the expected output
        def mock_status():
            from rich.console import Console

            console = Console()
            console.print("[green]✓ Monitor is running (PID: 12345)[/green]")

        mock_instance.status = mock_status

        result = runner.invoke(monitor, ["status"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Monitor is running" in result.output


def test_monitor_status_not_running(runner, mock_tmux, temp_pid_file) -> None:
    """Test monitor status when not running."""
    with patch("tmux_orchestrator.core.monitor.IdleMonitor") as mock_idle_monitor:
        mock_instance = Mock()
        mock_idle_monitor.return_value = mock_instance
        mock_instance.is_running.return_value = False

        # Mock the status method
        def mock_status():
            from rich.console import Console

            console = Console()
            console.print("[red]✗ Monitor is not running[/red]")

        mock_instance.status = mock_status

        result = runner.invoke(monitor, ["status"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Monitor is not running" in result.output


def test_monitor_dashboard(runner, mock_tmux) -> None:
    """Test monitor dashboard command."""
    # Mock tmux methods
    mock_tmux.list_sessions.return_value = [{"name": "session1", "created": "1234567890", "attached": "1"}]
    mock_tmux.list_agents.return_value = [
        {"target": "session1:0", "session": "session1", "window": "0", "status": "Active", "type": "Developer"},
        {"target": "session1:1", "session": "session1", "window": "1", "status": "Idle", "type": "QA Engineer"},
    ]

    result = runner.invoke(monitor, ["dashboard", "--refresh", "0"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    assert "TMUX Orchestrator Dashboard" in result.output


def test_monitor_logs(runner, mock_tmux) -> None:
    """Test monitor logs command."""
    with patch("os.path.exists") as mock_exists:
        with patch("subprocess.run") as mock_run:
            mock_exists.return_value = True

            result = runner.invoke(monitor, ["logs"], obj={"tmux": mock_tmux})

            assert result.exit_code == 0
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "tail" in args
            assert "-20" in args  # Default lines


def test_monitor_with_custom_interval(runner, mock_tmux) -> None:
    """Test monitor with custom interval."""
    with patch("tmux_orchestrator.core.monitor.IdleMonitor") as mock_idle_monitor:
        mock_instance = Mock()
        mock_idle_monitor.return_value = mock_instance
        mock_instance.is_running.return_value = False
        mock_instance.start.return_value = 12345

        result = runner.invoke(monitor, ["start", "--interval", "30"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Monitor daemon started successfully" in result.output or "started" in result.output.lower()
        mock_instance.start.assert_called_once_with(30)


def test_monitor_group_exists() -> None:
    """Test that monitor command group exists and has expected subcommands."""
    assert callable(monitor)

    command_names = list(monitor.commands.keys())
    expected_commands = {"start", "stop", "status", "logs", "dashboard"}

    assert expected_commands.issubset(set(command_names))
