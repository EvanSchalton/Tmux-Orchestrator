"""Tests for agent CLI commands."""

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

    with patch('tmux_orchestrator.core.agent_operations.restart_agent') as mock_restart:
        mock_restart.return_value = (True, "Agent restarted successfully")

        # Create a mock context
        with patch('click.get_current_context') as mock_get_ctx:
            mock_ctx = Mock()
            mock_tmux = Mock(spec=TMUXManager)
            mock_ctx.obj = {'tmux': mock_tmux}
            mock_get_ctx.return_value = mock_ctx

            # Test CLI command through runner
            result = runner.invoke(agent, ['restart', 'test-session:0'])

            assert result.exit_code == 0
            assert "Restarting agent at test-session:0" in result.output
            assert "Agent restarted successfully" in result.output


def test_agent_restart_failure() -> None:
    """Test agent restart command failure via CLI."""
    runner = CliRunner()

    with patch('tmux_orchestrator.core.agent_operations.restart_agent') as mock_restart:
        mock_restart.return_value = (False, "Session not found")

        with patch('click.get_current_context') as mock_get_ctx:
            mock_ctx = Mock()
            mock_tmux = Mock(spec=TMUXManager)
            mock_ctx.obj = {'tmux': mock_tmux}
            mock_get_ctx.return_value = mock_ctx

            result = runner.invoke(agent, ['restart', 'invalid:target'])

            assert result.exit_code == 0  # Command runs, but shows error
            assert "Session not found" in result.output


def test_agent_message_success() -> None:
    """Test successful message sending via CLI."""
    runner = CliRunner()

    with patch('click.get_current_context') as mock_get_ctx:
        mock_ctx = Mock()
        mock_tmux = Mock(spec=TMUXManager)
        mock_tmux.send_message.return_value = True
        mock_ctx.obj = {'tmux': mock_tmux}
        mock_get_ctx.return_value = mock_ctx

        result = runner.invoke(agent, ['message', 'test-session:0', 'Hello agent!'])

        assert result.exit_code == 0
        assert "Message sent to test-session:0" in result.output


def test_agent_message_failure() -> None:
    """Test message sending failure via CLI."""
    runner = CliRunner()

    with patch('click.get_current_context') as mock_get_ctx:
        mock_ctx = Mock()
        mock_tmux = Mock(spec=TMUXManager)
        mock_tmux.send_message.return_value = False
        mock_ctx.obj = {'tmux': mock_tmux}
        mock_get_ctx.return_value = mock_ctx

        result = runner.invoke(agent, ['message', 'test-session:0', 'Hello agent!'])

        assert result.exit_code == 0
        assert "Failed to send message" in result.output


def test_agent_attach_success() -> None:
    """Test successful attach command via CLI."""
    runner = CliRunner()

    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0

        with patch('click.get_current_context') as mock_get_ctx:
            mock_ctx = Mock()
            mock_ctx.obj = {'tmux': Mock(spec=TMUXManager)}
            mock_get_ctx.return_value = mock_ctx

            result = runner.invoke(agent, ['attach', 'test-session:0'])

            # attach command will try to actually attach, which we can't test in unit tests
            # The important thing is that subprocess.run is called correctly
            mock_run.assert_called_once_with(['tmux', 'attach', '-t', 'test-session:0'], check=True)


def test_agent_deploy_success() -> None:
    """Test successful deploy command via CLI."""
    runner = CliRunner()

    with patch('tmux_orchestrator.core.agent_manager.AgentManager') as mock_agent_mgr_class:
        mock_agent_mgr = Mock()
        mock_agent_mgr.deploy_agent.return_value = "test-session-123"
        mock_agent_mgr_class.return_value = mock_agent_mgr

        with patch('click.get_current_context') as mock_get_ctx:
            mock_ctx = Mock()
            mock_tmux = Mock(spec=TMUXManager)
            mock_ctx.obj = {'tmux': mock_tmux}
            mock_get_ctx.return_value = mock_ctx

            result = runner.invoke(agent, ['deploy', 'frontend', 'developer'])

            assert result.exit_code == 0
            assert "Deployed frontend developer" in result.output
            mock_agent_mgr_class.assert_called_once_with(mock_tmux)
            mock_agent_mgr.deploy_agent.assert_called_once_with("frontend", "developer")


def test_agent_status_success() -> None:
    """Test successful status command via CLI."""
    runner = CliRunner()

    with patch('tmux_orchestrator.core.agent_manager.AgentManager') as mock_agent_mgr_class:
        mock_agent_mgr = Mock()
        mock_agent_mgr.get_all_status.return_value = {
            'agent-1': {
                'state': 'active',
                'last_activity': '2023-01-01 10:00:00',
                'current_task': 'Working on frontend'
            }
        }
        mock_agent_mgr_class.return_value = mock_agent_mgr

        with patch('click.get_current_context') as mock_get_ctx:
            mock_ctx = Mock()
            mock_tmux = Mock(spec=TMUXManager)
            mock_ctx.obj = {'tmux': mock_tmux}
            mock_get_ctx.return_value = mock_ctx

            result = runner.invoke(agent, ['status'])

            assert result.exit_code == 0
            assert "agent-1" in result.output
            assert "active" in result.output


def test_agent_group_exists() -> None:
    """Test that agent command group exists and has expected subcommands."""
    # Verify the main command group
    assert callable(agent)

    # Get the command names from the group
    command_names = list(agent.commands.keys())
    expected_commands = {'deploy', 'message', 'attach', 'restart', 'status'}

    # Verify all expected commands exist
    assert expected_commands.issubset(set(command_names))


def test_restart_function_direct() -> None:
    """Test restart function directly without CLI runner."""
    with patch('tmux_orchestrator.core.agent_operations.restart_agent') as mock_restart:
        mock_restart.return_value = (True, "Success message")

        ctx = Mock()
        ctx.obj = {'tmux': Mock(spec=TMUXManager)}

        # Call the function directly
        restart(ctx, "test-session:0")

        # Verify business logic was called
        mock_restart.assert_called_once_with(ctx.obj['tmux'], "test-session:0")


def test_message_function_direct() -> None:
    """Test message function directly without CLI runner."""
    ctx = Mock()
    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.send_message.return_value = True
    ctx.obj = {'tmux': mock_tmux}

    # Call message function directly
    message(ctx, "test-session:0", "Hello agent!")

    # Verify TMUXManager method was called
    mock_tmux.send_message.assert_called_once_with("test-session:0", "Hello agent!")
