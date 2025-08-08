"""Tests for recovery CLI commands."""

from unittest.mock import Mock, patch, MagicMock

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.recovery import recovery
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_tmux():
    """Create mock TMUXManager."""
    return Mock(spec=TMUXManager)


def test_recovery_check_all_healthy(runner, mock_tmux):
    """Test recovery check when all agents are healthy."""
    with patch('tmux_orchestrator.core.recovery.discover_agents') as mock_discover:
        with patch('tmux_orchestrator.core.recovery.check_agent_health') as mock_health:
            # Mock discovery
            mock_discover.return_value = [
                {'target': 'proj:0', 'session': 'proj', 'window': '0'},
                {'target': 'proj:1', 'session': 'proj', 'window': '1'},
                {'target': 'proj:2', 'session': 'proj', 'window': '2'}
            ]
            
            # All healthy
            mock_health.return_value = {'healthy': True, 'status': 'active'}
            
            result = runner.invoke(recovery, ['check'], obj={'tmux': mock_tmux})
            
            assert result.exit_code == 0
            assert "3 agents" in result.output
            assert "All healthy" in result.output or "0 unhealthy" in result.output


def test_recovery_check_with_unhealthy(runner, mock_tmux):
    """Test recovery check with unhealthy agents."""
    with patch('tmux_orchestrator.core.recovery.discover_agents') as mock_discover:
        with patch('tmux_orchestrator.core.recovery.check_agent_health') as mock_health:
            # Mock discovery
            mock_discover.return_value = [
                {'target': 'proj:0', 'session': 'proj', 'window': '0'},
                {'target': 'proj:1', 'session': 'proj', 'window': '1'},
                {'target': 'proj:2', 'session': 'proj', 'window': '2'}
            ]
            
            # Mixed health
            mock_health.side_effect = [
                {'healthy': True, 'status': 'active'},
                {'healthy': False, 'reason': 'No activity for 1h'},
                {'healthy': True, 'status': 'active'}
            ]
            
            result = runner.invoke(recovery, ['check'], obj={'tmux': mock_tmux})
            
            assert result.exit_code == 0
            assert "1 unhealthy" in result.output
            assert "proj:1" in result.output


def test_recovery_check_auto_restart(runner, mock_tmux):
    """Test recovery check with auto-restart enabled."""
    with patch('tmux_orchestrator.core.recovery.discover_agents') as mock_discover:
        with patch('tmux_orchestrator.core.recovery.check_agent_health') as mock_health:
            with patch('tmux_orchestrator.core.agent_operations.restart_agent') as mock_restart:
                # Mock discovery
                mock_discover.return_value = [
                    {'target': 'proj:0', 'session': 'proj', 'window': '0'},
                    {'target': 'proj:1', 'session': 'proj', 'window': '1'}
                ]
                
                # One unhealthy
                mock_health.side_effect = [
                    {'healthy': True, 'status': 'active'},
                    {'healthy': False, 'reason': 'Crashed'}
                ]
                
                # Mock restart
                mock_restart.return_value = (True, "Restarted successfully")
                
                result = runner.invoke(recovery, ['check', '--auto-restart'], 
                                     obj={'tmux': mock_tmux})
                
                assert result.exit_code == 0
                assert "Restarting" in result.output
                mock_restart.assert_called_once()


def test_recovery_discover(runner, mock_tmux):
    """Test agent discovery command."""
    with patch('tmux_orchestrator.core.recovery.discover_agents') as mock_discover:
        mock_discover.return_value = [
            {'target': 'frontend:0', 'session': 'frontend', 'window': '0', 'type': 'orchestrator'},
            {'target': 'frontend:1', 'session': 'frontend', 'window': '1', 'type': 'pm'},
            {'target': 'frontend:2', 'session': 'frontend', 'window': '2', 'type': 'developer'},
            {'target': 'backend:0', 'session': 'backend', 'window': '0', 'type': 'orchestrator'},
            {'target': 'backend:1', 'session': 'backend', 'window': '1', 'type': 'developer'}
        ]
        
        result = runner.invoke(recovery, ['discover'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "5 agents" in result.output
        assert "frontend:0" in result.output
        assert "backend:1" in result.output


def test_recovery_restore_specific_agent(runner, mock_tmux):
    """Test restoring specific agent."""
    with patch('tmux_orchestrator.core.recovery.restore_context') as mock_restore:
        mock_restore.return_value = {
            'success': True,
            'agent': 'project:2',
            'context_restored': True,
            'message': 'Agent restored with previous context'
        }
        
        result = runner.invoke(recovery, ['restore', 'project:2'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "Restoring project:2" in result.output
        assert "restored" in result.output.lower()
        mock_restore.assert_called_once_with(mock_tmux, 'project:2')


def test_recovery_restore_all_in_session(runner, mock_tmux):
    """Test restoring all agents in a session."""
    with patch('tmux_orchestrator.core.recovery.discover_agents') as mock_discover:
        with patch('tmux_orchestrator.core.recovery.restore_context') as mock_restore:
            # Mock discovery for session
            mock_discover.return_value = [
                {'target': 'myproject:0', 'session': 'myproject', 'window': '0'},
                {'target': 'myproject:1', 'session': 'myproject', 'window': '1'},
                {'target': 'myproject:2', 'session': 'myproject', 'window': '2'}
            ]
            
            # Mock restore success
            mock_restore.return_value = {
                'success': True,
                'context_restored': True
            }
            
            result = runner.invoke(recovery, ['restore', '--session', 'myproject'], 
                                 obj={'tmux': mock_tmux})
            
            assert result.exit_code == 0
            assert "Restoring 3 agents" in result.output
            assert mock_restore.call_count == 3


def test_recovery_history(runner, mock_tmux):
    """Test viewing recovery history."""
    with patch('tmux_orchestrator.core.recovery.get_recovery_history') as mock_history:
        mock_history.return_value = [
            {
                'timestamp': '2024-01-01 10:00:00',
                'agent': 'project:1',
                'action': 'restart',
                'reason': 'No activity for 1h',
                'success': True
            },
            {
                'timestamp': '2024-01-01 11:30:00', 
                'agent': 'project:2',
                'action': 'restart',
                'reason': 'Crashed',
                'success': True
            }
        ]
        
        result = runner.invoke(recovery, ['history'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "Recovery History" in result.output
        assert "project:1" in result.output
        assert "No activity" in result.output


def test_recovery_history_specific_session(runner, mock_tmux):
    """Test viewing recovery history for specific session."""
    with patch('tmux_orchestrator.core.recovery.get_recovery_history') as mock_history:
        mock_history.return_value = [
            {
                'timestamp': '2024-01-01 10:00:00',
                'agent': 'myproject:1',
                'action': 'restart',
                'reason': 'Idle',
                'success': True
            }
        ]
        
        result = runner.invoke(recovery, ['history', '--session', 'myproject'], 
                             obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "myproject:1" in result.output
        mock_history.assert_called_once_with(session='myproject')


def test_recovery_group_exists():
    """Test that recovery command group exists and has expected subcommands."""
    assert callable(recovery)
    
    command_names = list(recovery.commands.keys())
    expected_commands = {'check', 'discover', 'restore', 'history'}
    
    assert expected_commands.issubset(set(command_names))