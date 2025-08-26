"""Basic tests for agent CLI commands - core operations."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.agent import agent, message, restart
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


def test_agent_restart_success() -> None:
    """Test successful agent restart command via CLI."""
    runner = CliRunner()

    with patch("tmux_orchestrator.cli.agent.restart_agent") as mock_restart:
        mock_restart.return_value = (True, "Agent restarted successfully", {})
        mock_tmux = Mock(spec=TMUXManager)

        # Test CLI command through runner with context
        result = runner.invoke(agent, ["restart", "test-session:0"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        # Strip ANSI color codes for testing
        clean_output = (
            result.output.replace("\x1b[33m", "")
            .replace("\x1b[0m", "")
            .replace("\x1b[1;33m", "")
            .replace("\x1b[32m", "")
            .replace("\x1b[1;32m", "")
        )
        assert "Restarting agent at test-session:0" in clean_output
        assert "restarted successfully" in clean_output


def test_agent_restart_failure() -> None:
    """Test agent restart command failure via CLI."""
    runner = CliRunner()

    with patch("tmux_orchestrator.cli.agent.restart_agent") as mock_restart:
        mock_restart.return_value = (False, "Session not found", {"status": "failed"})
        mock_tmux = Mock(spec=TMUXManager)

        result = runner.invoke(agent, ["restart", "invalid:target"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0  # CLI command itself succeeds even if operation fails
        # Clean ANSI color codes from output
        clean_output = (
            result.output.replace("\x1b[33m", "")
            .replace("\x1b[0m", "")
            .replace("\x1b[32m", "")
            .replace("\x1b[1;32m", "")
            .replace("\x1b[31m", "")  # Also remove red color codes for error messages
            .replace("\x1b[1;31m", "")
        )
        # The restart should show it's attempting to restart and then show failure
        assert "Restarting agent at invalid:target" in clean_output
        assert "Session not found" in clean_output


def test_agent_message_success() -> None:
    """Test successful message sending via CLI."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.send_message.return_value = True

    result = runner.invoke(agent, ["message", "test-session:0", "Hello agent!"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    clean_output = result.output.replace("\x1b[32m", "").replace("\x1b[0m", "").replace("\x1b[1;32m", "")
    assert "Message sent to test-session:0" in clean_output


def test_agent_message_failure() -> None:
    """Test message sending failure via CLI."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.send_message.return_value = False

    result = runner.invoke(agent, ["message", "test-session:0", "Hello agent!"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    assert "Failed to send message" in result.output


def test_agent_attach_success() -> None:
    """Test successful attach command via CLI."""
    runner = CliRunner()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_tmux = Mock(spec=TMUXManager)

        _result = runner.invoke(agent, ["attach", "test-session:0"], obj={"tmux": mock_tmux})

        # attach command will try to actually attach, which we can't test in unit tests
        # The important thing is that subprocess.run is called correctly
        mock_run.assert_called_once_with(["tmux", "attach", "-t", "test-session:0"], check=True)


def test_agent_deploy_success() -> None:
    """Test successful deploy command via CLI."""
    runner = CliRunner()

    with patch("tmux_orchestrator.core.agent_manager.AgentManager") as mock_agent_mgr_class:
        mock_agent_mgr = Mock()
        mock_agent_mgr.deploy_agent.return_value = "test-session-123"
        mock_agent_mgr_class.return_value = mock_agent_mgr
        mock_tmux = Mock(spec=TMUXManager)

        result = runner.invoke(agent, ["deploy", "frontend", "developer"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Deployed frontend developer" in result.output
        mock_agent_mgr_class.assert_called_once_with(mock_tmux)
        mock_agent_mgr.deploy_agent.assert_called_once_with("frontend", "developer")


def test_agent_status_success() -> None:
    """Test successful status command via CLI."""
    runner = CliRunner()

    with patch("tmux_orchestrator.core.agent_manager.AgentManager") as mock_agent_mgr_class:
        mock_agent_mgr = Mock()
        mock_agent_mgr.get_all_status.return_value = {
            "agent-1": {
                "state": "active",
                "last_activity": "2023-01-01 10:00:00",
                "current_task": "Working on frontend",
            }
        }
        mock_agent_mgr_class.return_value = mock_agent_mgr
        mock_tmux = Mock(spec=TMUXManager)

        result = runner.invoke(agent, ["status"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        clean_output = result.output.replace("\x1b[1;36m", "").replace("\x1b[0m", "").replace("\x1b[1;92m", "")
        assert "agent-1" in clean_output
        assert "active" in clean_output


def test_agent_group_exists() -> None:
    """Test that agent command group exists and has expected subcommands."""
    # Verify the main command group
    assert callable(agent)

    # Get the command names from the group
    command_names = list(agent.commands.keys())
    expected_commands = {"deploy", "message", "attach", "restart", "status", "send"}

    # Verify all expected commands exist
    assert expected_commands.issubset(set(command_names))


def test_restart_function_direct() -> None:
    """Test restart function directly without CLI runner."""
    runner = CliRunner()

    with patch("tmux_orchestrator.cli.agent.restart_agent") as mock_restart:
        mock_restart.return_value = (True, "Success message", {"status": "success"})
        mock_tmux = Mock(spec=TMUXManager)

        # Use runner.invoke instead of calling function directly
        result = runner.invoke(restart, ["test-session:0"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        # Verify business logic was called with all expected parameters
        mock_restart.assert_called_once_with(
            mock_tmux, "test-session:0", health_check=True, preserve_context=True, custom_command=None, timeout=10
        )


def test_message_function_direct() -> None:
    """Test message function directly without CLI runner."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.send_message.return_value = True

    # Use runner.invoke instead of calling function directly
    result = runner.invoke(message, ["test-session:0", "Hello agent!"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    # Verify TMUXManager method was called
    mock_tmux.send_message.assert_called_once_with("test-session:0", "Hello agent!")
