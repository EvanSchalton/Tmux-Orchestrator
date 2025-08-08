"""Integration tests for end-to-end workflows."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli import cli
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_tmux():
    """Create mock TMUXManager."""
    mock = Mock(spec=TMUXManager)
    # Setup default behaviors
    mock.session_exists.return_value = False
    mock.list_sessions.return_value = []
    return mock


@pytest.fixture
def temp_orchestrator_home():
    """Create temporary orchestrator home."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orc_dir = Path(tmpdir) / ".tmux_orchestrator"
        orc_dir.mkdir()
        (orc_dir / "projects").mkdir()
        (orc_dir / "templates").mkdir()
        (orc_dir / "agent-templates").mkdir()
        (orc_dir / "archive").mkdir()
        
        with patch.dict(os.environ, {'TMUX_ORCHESTRATOR_HOME': str(orc_dir)}):
            yield orc_dir


def test_complete_prd_workflow(runner, mock_tmux, temp_orchestrator_home):
    """Test complete PRD to deployment workflow."""
    # Create test PRD
    prd_content = """# Test Project

## Overview
A simple test application.

## Requirements
1. User authentication
2. Data storage
3. API endpoints
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(prd_content)
        prd_path = f.name
    
    try:
        # Mock various components
        with patch('tmux_orchestrator.cli.execute.generate_tasks_from_prd') as mock_gen:
            with patch('tmux_orchestrator.cli.execute.compose_team_from_prd') as mock_compose:
                with patch('tmux_orchestrator.core.team_manager.TeamManager') as mock_team_mgr:
                    # Setup mocks
                    mock_gen.return_value = "- [ ] Setup auth\n- [ ] Create API"
                    mock_compose.return_value = {
                        'agents': [
                            {'role': 'pm', 'name': 'Project Manager'},
                            {'role': 'backend', 'name': 'Backend Dev'}
                        ]
                    }
                    
                    mock_mgr = Mock()
                    mock_mgr.deploy_custom_team.return_value = {
                        'session': 'test-project',
                        'agents': ['test-project:0', 'test-project:1']
                    }
                    mock_team_mgr.return_value = mock_mgr
                    
                    # Execute PRD
                    result = runner.invoke(cli, ['execute', prd_path], obj={'tmux': mock_tmux})
                    
                    assert result.exit_code == 0
                    
                    # Verify project created
                    project_dir = temp_orchestrator_home / "projects" / "test-project"
                    assert project_dir.exists()
                    assert (project_dir / "prd.md").exists()
                    assert (project_dir / "tasks.md").exists()
                    
                    # Check team status
                    with patch('tmux_orchestrator.core.team_operations.get_team_status') as mock_status:
                        mock_status.return_value = {
                            'session': 'test-project',
                            'agents': {
                                'test-project:0': {'status': 'active'},
                                'test-project:1': {'status': 'active'}
                            }
                        }
                        
                        result = runner.invoke(cli, ['team', 'status', 'test-project'], 
                                             obj={'tmux': mock_tmux})
                        assert result.exit_code == 0
                        assert 'active' in result.output
    
    finally:
        os.unlink(prd_path)


def test_task_management_workflow(runner, mock_tmux, temp_orchestrator_home):
    """Test task creation and distribution workflow."""
    # Create project
    result = runner.invoke(cli, ['tasks', 'create', 'my-project'])
    assert result.exit_code == 0
    
    project_dir = temp_orchestrator_home / "projects" / "my-project"
    assert project_dir.exists()
    
    # Add tasks
    tasks_content = """# Tasks

## Frontend
- [ ] Create login page
- [ ] Build dashboard

## Backend  
- [ ] Setup database
- [ ] Create API
"""
    (project_dir / "tasks.md").write_text(tasks_content)
    
    # Distribute tasks
    result = runner.invoke(cli, ['tasks', 'distribute', 'my-project'])
    assert result.exit_code == 0
    
    # Check agent directories
    agents_dir = project_dir / "agents"
    agent_files = list(agents_dir.glob("*.md"))
    assert len(agent_files) > 0
    
    # Check status
    result = runner.invoke(cli, ['tasks', 'status', 'my-project'])
    assert result.exit_code == 0
    assert "0%" in result.output or "0/4" in result.output


def test_team_deployment_and_recovery(runner, mock_tmux, temp_orchestrator_home):
    """Test team deployment and recovery workflow."""
    # Deploy team
    with patch('tmux_orchestrator.core.team_manager.TeamManager') as mock_team_mgr:
        mock_mgr = Mock()
        mock_mgr.deploy_team.return_value = {
            'session': 'test-team',
            'agents': ['test-team:0', 'test-team:1', 'test-team:2']
        }
        mock_team_mgr.return_value = mock_mgr
        
        result = runner.invoke(cli, ['team', 'deploy', 'frontend', '2'], 
                             obj={'tmux': mock_tmux})
        assert result.exit_code == 0
    
    # Check team health
    with patch('tmux_orchestrator.core.recovery.discover_agents') as mock_discover:
        with patch('tmux_orchestrator.core.recovery.check_agent_health') as mock_health:
            # Mock unhealthy agent
            mock_discover.return_value = [
                {'target': 'test-team:0', 'session': 'test-team'},
                {'target': 'test-team:1', 'session': 'test-team'},
                {'target': 'test-team:2', 'session': 'test-team'}
            ]
            
            mock_health.side_effect = [
                {'healthy': True},
                {'healthy': False, 'reason': 'Idle'},
                {'healthy': True}
            ]
            
            result = runner.invoke(cli, ['recovery', 'check'], obj={'tmux': mock_tmux})
            assert result.exit_code == 0
            assert "1 unhealthy" in result.output
    
    # Recover team
    with patch('tmux_orchestrator.core.agent_operations.restart_agent') as mock_restart:
        mock_restart.return_value = (True, "Restarted")
        
        result = runner.invoke(cli, ['team', 'recover', 'test-team'], 
                             obj={'tmux': mock_tmux})
        assert result.exit_code == 0


def test_monitoring_workflow(runner, mock_tmux, temp_orchestrator_home):
    """Test monitoring daemon workflow."""
    # Start monitoring
    with patch('os.fork') as mock_fork:
        with patch('os.setsid'):
            with patch('tmux_orchestrator.cli.monitor.run_monitor_loop'):
                mock_fork.side_effect = [1, 0]  # Parent/child
                
                result = runner.invoke(cli, ['monitor', 'start'], obj={'tmux': mock_tmux})
                assert result.exit_code == 0
    
    # Check status
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('12345')
        pid_file = f.name
    
    try:
        with patch('tmux_orchestrator.cli.monitor.PID_FILE', pid_file):
            with patch('os.kill'):
                result = runner.invoke(cli, ['monitor', 'status'], obj={'tmux': mock_tmux})
                assert result.exit_code == 0
                assert "12345" in result.output
    finally:
        os.unlink(pid_file)
    
    # Run single check
    with patch('tmux_orchestrator.core.recovery.discover_agents') as mock_discover:
        with patch('tmux_orchestrator.core.recovery.check_agent_health') as mock_health:
            mock_discover.return_value = [{'target': 'test:0'}]
            mock_health.return_value = {'healthy': True}
            
            result = runner.invoke(cli, ['monitor', 'check'], obj={'tmux': mock_tmux})
            assert result.exit_code == 0


def test_agent_communication_workflow(runner, mock_tmux):
    """Test agent messaging workflow."""
    # Send message to agent
    mock_tmux.send_message.return_value = True
    
    result = runner.invoke(cli, ['agent', 'message', 'project:0', 'Hello agent'], 
                         obj={'tmux': mock_tmux})
    assert result.exit_code == 0
    assert "sent" in result.output.lower()
    
    # Broadcast to team
    with patch('tmux_orchestrator.core.team_operations.broadcast_to_team') as mock_bc:
        mock_bc.return_value = {'sent': 3, 'failed': 0}
        
        result = runner.invoke(cli, ['team', 'broadcast', 'project', 'Team update'], 
                             obj={'tmux': mock_tmux})
        assert result.exit_code == 0


def test_project_archival_workflow(runner, mock_tmux, temp_orchestrator_home):
    """Test project completion and archival."""
    # Create and complete project
    runner.invoke(cli, ['tasks', 'create', 'completed-project'])
    
    project_dir = temp_orchestrator_home / "projects" / "completed-project"
    
    # Mark tasks complete
    (project_dir / "tasks.md").write_text("- [x] Task 1\n- [x] Task 2")
    
    # Archive project
    result = runner.invoke(cli, ['tasks', 'archive', 'completed-project'])
    assert result.exit_code == 0
    
    # Verify moved to archive
    assert not project_dir.exists()
    archive_dir = temp_orchestrator_home / "archive" / "completed-project"
    assert archive_dir.exists()