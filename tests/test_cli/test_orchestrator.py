"""Tests for orchestrator CLI commands."""

from unittest.mock import Mock, patch, MagicMock

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.orchestrator import orchestrator
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture  
def mock_tmux():
    """Create mock TMUXManager."""
    return Mock(spec=TMUXManager)


def test_orchestrator_start_new_session(runner, mock_tmux):
    """Test starting orchestrator in new session."""
    # Mock session check
    mock_tmux.session_exists.return_value = False
    
    # Mock subprocess for tmux new-session
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        result = runner.invoke(orchestrator, ['start'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "Starting orchestrator" in result.output
        
        # Verify tmux command
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        assert 'tmux' in args
        assert 'new-session' in args
        assert 'tmux-orc' in args


def test_orchestrator_start_existing_session(runner, mock_tmux):
    """Test starting orchestrator when session exists."""
    # Mock session exists
    mock_tmux.session_exists.return_value = True
    
    # Mock window count
    mock_tmux.run_command.return_value = "3"
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        result = runner.invoke(orchestrator, ['start'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "already exists" in result.output
        
        # Should create new window
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        assert 'new-window' in args


def test_orchestrator_stop(runner, mock_tmux):
    """Test stopping orchestrator session."""
    # Mock session exists
    mock_tmux.session_exists.return_value = True
    
    result = runner.invoke(orchestrator, ['stop'], obj={'tmux': mock_tmux})
    
    assert result.exit_code == 0
    assert "Stopping orchestrator" in result.output
    mock_tmux.kill_session.assert_called_once_with('tmux-orc')


def test_orchestrator_stop_not_running(runner, mock_tmux):
    """Test stopping orchestrator when not running."""
    # Mock session doesn't exist
    mock_tmux.session_exists.return_value = False
    
    result = runner.invoke(orchestrator, ['stop'], obj={'tmux': mock_tmux})
    
    assert result.exit_code == 0
    assert "not running" in result.output


def test_orchestrator_restart(runner, mock_tmux):
    """Test restarting orchestrator."""
    # First session exists (for stop)
    mock_tmux.session_exists.side_effect = [True, False]
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        result = runner.invoke(orchestrator, ['restart'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "Restarting" in result.output
        
        # Should kill then create
        mock_tmux.kill_session.assert_called_once_with('tmux-orc')
        mock_run.assert_called()


def test_orchestrator_status_running(runner, mock_tmux):
    """Test orchestrator status when running."""
    # Mock session exists
    mock_tmux.session_exists.return_value = True
    
    # Mock list windows
    mock_tmux.run_command.return_value = """0: Orchestrator
1: Project-Manager  
2: Developer
3: QA-Engineer"""
    
    result = runner.invoke(orchestrator, ['status'], obj={'tmux': mock_tmux})
    
    assert result.exit_code == 0
    assert "running" in result.output
    assert "Orchestrator" in result.output
    assert "Project-Manager" in result.output


def test_orchestrator_status_not_running(runner, mock_tmux):
    """Test orchestrator status when not running."""
    # Mock session doesn't exist
    mock_tmux.session_exists.return_value = False
    
    result = runner.invoke(orchestrator, ['status'], obj={'tmux': mock_tmux})
    
    assert result.exit_code == 0
    assert "not running" in result.output


def test_orchestrator_attach(runner, mock_tmux):
    """Test attaching to orchestrator session."""
    # Mock session exists
    mock_tmux.session_exists.return_value = True
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        result = runner.invoke(orchestrator, ['attach'], obj={'tmux': mock_tmux})
        
        # Attach will try to actually attach
        mock_run.assert_called_once_with(['tmux', 'attach', '-t', 'tmux-orc'], check=True)


def test_orchestrator_attach_not_running(runner, mock_tmux):
    """Test attaching when orchestrator not running."""  
    # Mock session doesn't exist
    mock_tmux.session_exists.return_value = False
    
    result = runner.invoke(orchestrator, ['attach'], obj={'tmux': mock_tmux})
    
    assert result.exit_code == 0
    assert "not running" in result.output
    assert "Start it with" in result.output


def test_orchestrator_group_exists():
    """Test that orchestrator command group exists and has expected subcommands."""
    assert callable(orchestrator)
    
    command_names = list(orchestrator.commands.keys())
    expected_commands = {'start', 'stop', 'restart', 'status', 'attach'}
    
    assert expected_commands.issubset(set(command_names))