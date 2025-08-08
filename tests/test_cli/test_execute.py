"""Tests for execute CLI command."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.execute import execute
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_tmux():
    """Create mock TMUXManager."""
    return Mock(spec=TMUXManager)


@pytest.fixture
def temp_orchestrator_dir():
    """Create temporary orchestrator directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orc_dir = Path(tmpdir) / ".tmux_orchestrator"
        orc_dir.mkdir()
        (orc_dir / "projects").mkdir()
        (orc_dir / "templates").mkdir()
        (orc_dir / "agent-templates").mkdir()
        
        # Set environment variable
        with patch.dict(os.environ, {'TMUX_ORCHESTRATOR_HOME': str(orc_dir)}):
            yield orc_dir


@pytest.fixture
def sample_prd():
    """Create a sample PRD file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# Task Management System

## Overview
Build a CLI-based task management system.

## Requirements
1. Create, update, delete tasks
2. List and filter tasks
3. Persistent storage
4. Command-line interface

## Technical Requirements
- Python-based CLI using Click
- SQLite for storage
- Rich for terminal UI
""")
        yield f.name
    os.unlink(f.name)


def test_execute_with_prd_file(runner, mock_tmux, temp_orchestrator_dir, sample_prd):
    """Test executing a PRD file."""
    # Mock the task generation
    with patch('tmux_orchestrator.cli.execute.generate_tasks_from_prd') as mock_gen_tasks:
        with patch('tmux_orchestrator.cli.execute.compose_team_from_prd') as mock_compose:
            with patch('tmux_orchestrator.core.team_manager.TeamManager') as mock_team_mgr:
                # Mock task generation
                mock_gen_tasks.return_value = """## Tasks
- [ ] Design CLI interface
- [ ] Implement task CRUD operations
- [ ] Setup SQLite database
- [ ] Add filtering capabilities"""
                
                # Mock team composition
                mock_compose.return_value = {
                    'agents': [
                        {'role': 'project-manager', 'name': 'PM'},
                        {'role': 'cli-developer', 'name': 'CLI-Dev-1'},
                        {'role': 'backend-developer', 'name': 'Backend-Dev'},
                        {'role': 'qa-engineer', 'name': 'QA'}
                    ]
                }
                
                # Mock team deployment
                mock_mgr = Mock()
                mock_mgr.deploy_custom_team.return_value = {
                    'session': 'task-mgmt-123',
                    'agents': ['task-mgmt-123:0', 'task-mgmt-123:1', 'task-mgmt-123:2', 'task-mgmt-123:3']
                }
                mock_team_mgr.return_value = mock_mgr
                
                result = runner.invoke(execute, [sample_prd], obj={'tmux': mock_tmux})
                
                assert result.exit_code == 0
                assert "Executing PRD" in result.output
                assert "task-mgmt-123" in result.output
                
                # Verify project was created
                project_name = "task-management-system"
                project_dir = temp_orchestrator_dir / "projects" / project_name
                assert project_dir.exists()
                assert (project_dir / "prd.md").exists()
                assert (project_dir / "tasks.md").exists()


def test_execute_existing_project(runner, mock_tmux, temp_orchestrator_dir):
    """Test executing an existing project."""
    # Create project structure
    project_name = "my-project"
    project_dir = temp_orchestrator_dir / "projects" / project_name
    project_dir.mkdir(parents=True)
    
    # Create PRD and tasks
    (project_dir / "prd.md").write_text("# My Project\n\nA test project.")
    (project_dir / "tasks.md").write_text("- [ ] Task 1\n- [ ] Task 2")
    
    # Create team composition
    (project_dir / "team-composition.md").write_text("""# Team Composition

## Agents
- project-manager
- frontend-developer
- backend-developer
""")
    
    with patch('tmux_orchestrator.core.team_manager.TeamManager') as mock_team_mgr:
        mock_mgr = Mock()
        mock_mgr.deploy_custom_team.return_value = {
            'session': 'my-project',
            'agents': ['my-project:0', 'my-project:1', 'my-project:2']
        }
        mock_team_mgr.return_value = mock_mgr
        
        result = runner.invoke(execute, [project_name], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "Found existing project" in result.output


def test_execute_with_team_type(runner, mock_tmux, temp_orchestrator_dir, sample_prd):
    """Test executing with specific team type."""
    with patch('tmux_orchestrator.core.team_manager.TeamManager') as mock_team_mgr:
        mock_mgr = Mock()
        mock_mgr.deploy_team.return_value = {
            'session': 'backend-project',
            'agents': ['backend-project:0', 'backend-project:1', 'backend-project:2']
        }
        mock_team_mgr.return_value = mock_mgr
        
        result = runner.invoke(execute, [sample_prd, '--team-type', 'backend'], 
                             obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        mock_mgr.deploy_team.assert_called_once_with('backend', 3)


def test_execute_skip_team_planning(runner, mock_tmux, temp_orchestrator_dir, sample_prd):
    """Test executing with skip team planning."""
    with patch('tmux_orchestrator.cli.execute.generate_tasks_from_prd') as mock_gen_tasks:
        with patch('tmux_orchestrator.core.team_manager.TeamManager') as mock_team_mgr:
            mock_gen_tasks.return_value = "- [ ] Task 1"
            
            mock_mgr = Mock()
            mock_mgr.deploy_team.return_value = {
                'session': 'project',
                'agents': ['project:0', 'project:1']
            }
            mock_team_mgr.return_value = mock_mgr
            
            result = runner.invoke(execute, [sample_prd, '--skip-team-planning'], 
                                 obj={'tmux': mock_tmux})
            
            assert result.exit_code == 0
            # Should use default fullstack team
            mock_mgr.deploy_team.assert_called_once_with('fullstack', 3)


def test_execute_with_agent_count(runner, mock_tmux, temp_orchestrator_dir, sample_prd):
    """Test executing with custom agent count."""
    with patch('tmux_orchestrator.cli.execute.generate_tasks_from_prd'):
        with patch('tmux_orchestrator.cli.execute.compose_team_from_prd'):
            with patch('tmux_orchestrator.core.team_manager.TeamManager') as mock_team_mgr:
                mock_mgr = Mock()
                mock_mgr.deploy_custom_team.return_value = {
                    'session': 'project',
                    'agents': ['project:0', 'project:1', 'project:2', 'project:3', 'project:4']
                }
                mock_team_mgr.return_value = mock_mgr
                
                result = runner.invoke(execute, [sample_prd, '--agents', '5'], 
                                     obj={'tmux': mock_tmux})
                
                assert result.exit_code == 0
                # Verify it tries to deploy 5 agents
                args = mock_mgr.deploy_custom_team.call_args
                assert len(args[0][1]) <= 5  # Team composition should respect agent count


def test_execute_nonexistent_file(runner, mock_tmux):
    """Test executing non-existent file."""
    result = runner.invoke(execute, ['nonexistent.md'], obj={'tmux': mock_tmux})
    
    assert result.exit_code == 0
    assert "not found" in result.output.lower() or "does not exist" in result.output.lower()


def test_execute_distribute_tasks(runner, mock_tmux, temp_orchestrator_dir, sample_prd):
    """Test that execute distributes tasks to agents."""
    with patch('tmux_orchestrator.cli.execute.generate_tasks_from_prd') as mock_gen_tasks:
        with patch('tmux_orchestrator.cli.execute.compose_team_from_prd') as mock_compose:
            with patch('tmux_orchestrator.core.team_manager.TeamManager') as mock_team_mgr:
                with patch('tmux_orchestrator.cli.tasks.distribute_tasks') as mock_distribute:
                    # Setup mocks
                    mock_gen_tasks.return_value = "- [ ] Task 1\n- [ ] Task 2"
                    mock_compose.return_value = {'agents': [{'role': 'pm'}, {'role': 'dev'}]}
                    
                    mock_mgr = Mock()
                    mock_mgr.deploy_custom_team.return_value = {
                        'session': 'project',
                        'agents': ['project:0', 'project:1']
                    }
                    mock_team_mgr.return_value = mock_mgr
                    
                    result = runner.invoke(execute, [sample_prd], obj={'tmux': mock_tmux})
                    
                    assert result.exit_code == 0
                    # Verify tasks were distributed
                    assert mock_distribute.called


def test_execute_function_exists():
    """Test that execute function exists and is callable."""
    assert callable(execute)
    
    # Check it's a Click command
    assert hasattr(execute, 'params')
    
    # Check expected options
    param_names = [p.name for p in execute.params]
    assert 'team_type' in param_names
    assert 'agents' in param_names
    assert 'skip_team_planning' in param_names