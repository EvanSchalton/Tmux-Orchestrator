"""Tests for agent CLI commands."""

from unittest.mock import Mock, patch
from click.testing import CliRunner
import pytest

from tmux_orchestrator.cli.agent import agent
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_ctx_obj() -> dict:
    """Create mock context object with TMUXManager."""
    mock_tmux = Mock(spec=TMUXManager)
    return {'tmux': mock_tmux, 'console': Mock()}


def test_agent_restart_success(runner: CliRunner) -> None:
    """Test successful agent restart command."""
    with patch('tmux_orchestrator.cli.agent.restart_agent') as mock_restart:
        mock_restart.return_value = (True, "Agent restarted successfully")
        
        with patch.object(runner, 'invoke') as mock_invoke:
            # Mock the Click context
            mock_ctx = Mock()
            mock_ctx.obj = {'tmux': Mock(spec=TMUXManager)}
            mock_invoke.return_value.exit_code = 0
            
            # This test verifies the CLI command structure
            # In a real scenario, we'd need to mock the full Click context
            
            # Verify the command exists and has correct parameters
            assert hasattr(agent, 'restart')
            
            # Test that restart function is called with correct parameters
            from tmux_orchestrator.cli.agent import restart
            
            # Mock Click context
            ctx = Mock()
            ctx.obj = {'tmux': Mock(spec=TMUXManager)}
            
            with patch('tmux_orchestrator.core.agent_operations.restart_agent') as mock_restart_func:
                mock_restart_func.return_value = (True, "Success message")
                
                # Call the function directly (bypassing Click decorator)
                restart(ctx, "test-session:0")
                
                # Verify business logic was called
                mock_restart_func.assert_called_once_with(ctx.obj['tmux'], "test-session:0")


def test_agent_restart_failure(runner: CliRunner) -> None:
    """Test agent restart command failure."""
    with patch('tmux_orchestrator.core.agent_operations.restart_agent') as mock_restart:
        mock_restart.return_value = (False, "Session not found")
        
        # Test the business logic delegation
        from tmux_orchestrator.cli.agent import restart
        
        ctx = Mock()
        ctx.obj = {'tmux': Mock(spec=TMUXManager)}
        
        restart(ctx, "invalid:target")
        
        # Verify error case is handled
        mock_restart.assert_called_once_with(ctx.obj['tmux'], "invalid:target")


def test_agent_message_success(runner: CliRunner) -> None:
    """Test successful message sending."""
    from tmux_orchestrator.cli.agent import message
    
    ctx = Mock()
    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.send_message.return_value = True
    ctx.obj = {'tmux': mock_tmux}
    
    # Call message function
    message(ctx, "test-session:0", "Hello agent!")
    
    # Verify TMUXManager method was called
    mock_tmux.send_message.assert_called_once_with("test-session:0", "Hello agent!")


def test_agent_message_failure(runner: CliRunner) -> None:
    """Test message sending failure."""
    from tmux_orchestrator.cli.agent import message
    
    ctx = Mock()
    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.send_message.return_value = False
    ctx.obj = {'tmux': mock_tmux}
    
    # Call message function
    message(ctx, "test-session:0", "Hello agent!")
    
    # Verify TMUXManager method was called
    mock_tmux.send_message.assert_called_once_with("test-session:0", "Hello agent!")


def test_agent_attach_success(runner: CliRunner) -> None:
    """Test successful attach command."""
    from tmux_orchestrator.cli.agent import attach
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        ctx = Mock()
        ctx.obj = {'tmux': Mock(spec=TMUXManager)}
        
        # Call attach function
        attach(ctx, "test-session:0")
        
        # Verify subprocess call
        mock_run.assert_called_once_with(['tmux', 'attach', '-t', 'test-session:0'], check=True)


def test_agent_attach_failure(runner: CliRunner) -> None:
    """Test attach command failure."""
    from tmux_orchestrator.cli.agent import attach
    import subprocess
    
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, 'tmux')
        
        ctx = Mock()
        ctx.obj = {'tmux': Mock(spec=TMUXManager)}
        
        # Call attach function - should not raise exception
        attach(ctx, "invalid-session:0")
        
        # Verify subprocess was called
        mock_run.assert_called_once_with(['tmux', 'attach', '-t', 'invalid-session:0'], check=True)


def test_agent_deploy_success(runner: CliRunner) -> None:
    """Test successful deploy command."""
    from tmux_orchestrator.cli.agent import deploy
    
    with patch('tmux_orchestrator.core.agent_manager.AgentManager') as mock_agent_mgr_class:
        mock_agent_mgr = Mock()
        mock_agent_mgr.deploy_agent.return_value = "test-session-123"
        mock_agent_mgr_class.return_value = mock_agent_mgr
        
        ctx = Mock()
        mock_tmux = Mock(spec=TMUXManager)
        ctx.obj = {'tmux': mock_tmux}
        
        # Call deploy function
        deploy(ctx, "frontend", "developer")
        
        # Verify AgentManager was used
        mock_agent_mgr_class.assert_called_once_with(mock_tmux)
        mock_agent_mgr.deploy_agent.assert_called_once_with("frontend", "developer")


def test_agent_status_success(runner: CliRunner) -> None:
    """Test successful status command."""
    from tmux_orchestrator.cli.agent import status
    
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
        
        ctx = Mock()
        mock_tmux = Mock(spec=TMUXManager)
        ctx.obj = {'tmux': mock_tmux}
        
        # Call status function
        status(ctx)
        
        # Verify AgentManager was used
        mock_agent_mgr_class.assert_called_once_with(mock_tmux)
        mock_agent_mgr.get_all_status.assert_called_once()


def test_agent_group_exists() -> None:
    """Test that agent command group exists."""
    # Verify the main command group
    assert callable(agent)
    
    # Verify all subcommands exist
    subcommands = ['deploy', 'message', 'attach', 'restart', 'status']
    for cmd_name in subcommands:
        assert hasattr(agent, cmd_name) or cmd_name in [c.name for c in agent.commands.values()]