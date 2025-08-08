"""Tests for team CLI commands."""

from unittest.mock import Mock, patch, MagicMock

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.team import team
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_tmux():
    """Create mock TMUXManager."""
    return Mock(spec=TMUXManager)


def test_team_deploy_frontend(runner, mock_tmux):
    """Test deploying a frontend team."""
    with patch('tmux_orchestrator.core.team_manager.TeamManager') as mock_team_mgr:
        mock_mgr_instance = Mock()
        mock_mgr_instance.deploy_team.return_value = {
            'session': 'project-123',
            'agents': ['orchestrator', 'pm', 'frontend1', 'frontend2', 'qa']
        }
        mock_team_mgr.return_value = mock_mgr_instance
        
        result = runner.invoke(team, ['deploy', 'frontend', '3'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "Deploying frontend team" in result.output
        mock_mgr_instance.deploy_team.assert_called_once_with('frontend', 3)


def test_team_deploy_backend(runner, mock_tmux):
    """Test deploying a backend team."""
    with patch('tmux_orchestrator.core.team_manager.TeamManager') as mock_team_mgr:
        mock_mgr_instance = Mock()
        mock_mgr_instance.deploy_team.return_value = {
            'session': 'backend-456',
            'agents': ['orchestrator', 'pm', 'backend1', 'backend2', 'qa']
        }
        mock_team_mgr.return_value = mock_mgr_instance
        
        result = runner.invoke(team, ['deploy', 'backend', '2'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "Deploying backend team" in result.output


def test_team_deploy_custom(runner, mock_tmux):
    """Test deploying a custom team."""
    with patch('tmux_orchestrator.core.team_manager.TeamManager') as mock_team_mgr:
        mock_mgr_instance = Mock()
        mock_mgr_instance.deploy_team.return_value = {
            'session': 'custom-789',
            'agents': ['orchestrator', 'pm', 'custom-agents']
        }
        mock_team_mgr.return_value = mock_mgr_instance
        
        result = runner.invoke(team, ['deploy', 'my-project', '--custom'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "custom team configuration" in result.output.lower()


def test_team_status_all(runner, mock_tmux):
    """Test getting status of all teams."""
    with patch('tmux_orchestrator.core.team_operations.list_all_teams') as mock_list:
        mock_list.return_value = {
            'project1': {
                'agents': 5,
                'active': 4,
                'idle': 1,
                'status': 'healthy'
            },
            'project2': {
                'agents': 3,
                'active': 3,
                'idle': 0,
                'status': 'healthy'
            }
        }
        
        result = runner.invoke(team, ['status'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "project1" in result.output
        assert "project2" in result.output
        assert "healthy" in result.output


def test_team_status_specific_session(runner, mock_tmux):
    """Test getting status of specific team."""
    with patch('tmux_orchestrator.core.team_operations.get_team_status') as mock_status:
        mock_status.return_value = {
            'session': 'project1',
            'agents': {
                'orchestrator:0': {'status': 'active', 'last_activity': '5m ago'},
                'pm:1': {'status': 'active', 'last_activity': '2m ago'},
                'dev:2': {'status': 'idle', 'last_activity': '45m ago'}
            }
        }
        
        result = runner.invoke(team, ['status', 'project1'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "orchestrator:0" in result.output
        assert "active" in result.output
        assert "idle" in result.output


def test_team_list(runner, mock_tmux):
    """Test listing all teams."""
    with patch('tmux_orchestrator.core.team_operations.list_all_teams') as mock_list:
        mock_list.return_value = {
            'frontend-app': {'agents': 5, 'created': '2024-01-01'},
            'backend-api': {'agents': 4, 'created': '2024-01-02'},
            'data-pipeline': {'agents': 3, 'created': '2024-01-03'}
        }
        
        result = runner.invoke(team, ['list'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "frontend-app" in result.output
        assert "backend-api" in result.output
        assert "data-pipeline" in result.output


def test_team_broadcast(runner, mock_tmux):
    """Test broadcasting message to team."""
    with patch('tmux_orchestrator.core.team_operations.broadcast_to_team') as mock_broadcast:
        mock_broadcast.return_value = {'sent': 5, 'failed': 0}
        
        result = runner.invoke(team, ['broadcast', 'project1', 'Team meeting in 5 minutes'], 
                              obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "Broadcasting to project1" in result.output
        mock_broadcast.assert_called_once_with(mock_tmux, 'project1', 'Team meeting in 5 minutes')


def test_team_broadcast_with_failures(runner, mock_tmux):
    """Test broadcasting with some failures."""
    with patch('tmux_orchestrator.core.team_operations.broadcast_to_team') as mock_broadcast:
        mock_broadcast.return_value = {'sent': 3, 'failed': 2}
        
        result = runner.invoke(team, ['broadcast', 'project1', 'Status update'], 
                              obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "sent: 3" in result.output.lower() or "3 agents" in result.output.lower()
        assert "failed: 2" in result.output.lower() or "2 failed" in result.output.lower()


def test_team_recover(runner, mock_tmux):
    """Test recovering failed agents in team."""
    with patch('tmux_orchestrator.core.recovery.discover_agents') as mock_discover:
        with patch('tmux_orchestrator.core.recovery.check_agent_health') as mock_health:
            with patch('tmux_orchestrator.core.agent_operations.restart_agent') as mock_restart:
                # Mock discovery
                mock_discover.return_value = [
                    {'target': 'project1:0', 'session': 'project1', 'window': '0'},
                    {'target': 'project1:1', 'session': 'project1', 'window': '1'},
                    {'target': 'project1:2', 'session': 'project1', 'window': '2'}
                ]
                
                # Mock health checks - one unhealthy
                mock_health.side_effect = [
                    {'healthy': True},
                    {'healthy': False, 'reason': 'No activity'},
                    {'healthy': True}
                ]
                
                # Mock restart
                mock_restart.return_value = (True, "Restarted successfully")
                
                result = runner.invoke(team, ['recover', 'project1'], obj={'tmux': mock_tmux})
                
                assert result.exit_code == 0
                assert "Checking health" in result.output
                assert "1 unhealthy" in result.output or "Restarting" in result.output


def test_team_coordinate(runner, mock_tmux):
    """Test team coordination command."""
    result = runner.invoke(team, ['coordinate', 'project1'], obj={'tmux': mock_tmux})
    
    # This command should send coordination messages
    assert result.exit_code == 0
    assert "coordination" in result.output.lower()


def test_team_group_exists():
    """Test that team command group exists and has expected subcommands."""
    assert callable(team)
    
    command_names = list(team.commands.keys())
    expected_commands = {'deploy', 'status', 'list', 'broadcast', 'recover', 'coordinate'}
    
    assert expected_commands.issubset(set(command_names))