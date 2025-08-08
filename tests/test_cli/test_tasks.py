"""Tests for tasks CLI commands."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.tasks import tasks


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_orchestrator_dir():
    """Create temporary orchestrator directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        orc_dir = Path(tmpdir) / ".tmux_orchestrator"
        orc_dir.mkdir()
        (orc_dir / "projects").mkdir()
        (orc_dir / "templates").mkdir()
        (orc_dir / "archive").mkdir()
        
        # Set environment variable
        with patch.dict(os.environ, {'TMUX_ORCHESTRATOR_HOME': str(orc_dir)}):
            yield orc_dir


def test_tasks_create_new_project(runner, temp_orchestrator_dir):
    """Test creating a new project."""
    # Use unique project name to avoid conflicts
    import uuid
    project_name = f"test-project-{uuid.uuid4().hex[:8]}"
    
    # Ensure the projects directory is created first
    (temp_orchestrator_dir / "projects").mkdir(exist_ok=True)
    
    result = runner.invoke(tasks, ['create', project_name])
    
    assert result.exit_code == 0
    # Check for success - the output includes the project name
    assert project_name in result.output
    assert "Created project structure" in result.output or "✓ Created project structure" in result.output
    
    # The actual directory is created using get_orchestrator_home()
    # So we need to check the output to find where it was created
    if "Project location:" in result.output:
        # Extract project location from output
        import re
        match = re.search(r'Project location:\s*\n([^\n]+)', result.output)
        if match:
            actual_path = Path(match.group(1).strip())
            assert actual_path.exists()
            assert (actual_path / "prd.md").exists()
            assert (actual_path / "tasks.md").exists()
            assert (actual_path / "agents").exists()
            assert (actual_path / "status").exists()
    else:
        # Fall back to checking in expected location
        project_dir = Path.home() / ".tmux_orchestrator" / "projects" / project_name
        assert project_dir.exists()
        assert (project_dir / "prd.md").exists()
        assert (project_dir / "tasks.md").exists()
        assert (project_dir / "agents").exists()
        assert (project_dir / "status").exists()


def test_tasks_create_with_prd_import(runner, temp_orchestrator_dir):
    """Test creating project with existing PRD."""
    # Create a test PRD file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test PRD\n\nThis is a test PRD.")
        prd_path = f.name
    
    try:
        result = runner.invoke(tasks, ['create', 'test-project', '--prd', prd_path])
        
        assert result.exit_code == 0
        assert "Imported PRD from" in result.output
        
        # Verify PRD was copied
        project_prd = temp_orchestrator_dir / "projects" / "test-project" / "prd.md"
        assert project_prd.read_text() == "# Test PRD\n\nThis is a test PRD."
    finally:
        os.unlink(prd_path)


def test_tasks_create_existing_project(runner, temp_orchestrator_dir):
    """Test creating a project that already exists."""
    # Create project first
    runner.invoke(tasks, ['create', 'test-project'])
    
    # Try to create again
    result = runner.invoke(tasks, ['create', 'test-project'])
    
    assert result.exit_code == 0
    assert "Project test-project already exists" in result.output


def test_tasks_status(runner, temp_orchestrator_dir):
    """Test project status command."""
    # Create a project first
    runner.invoke(tasks, ['create', 'test-project'])
    
    # Add some test content
    project_dir = temp_orchestrator_dir / "projects" / "test-project"
    (project_dir / "tasks.md").write_text("- [ ] Task 1\n- [x] Task 2\n- [ ] Task 3")
    
    result = runner.invoke(tasks, ['status', 'test-project'])
    
    assert result.exit_code == 0
    assert "test-project" in result.output
    assert "33% complete" in result.output or "1/3" in result.output


def test_tasks_status_nonexistent_project(runner, temp_orchestrator_dir):
    """Test status for non-existent project."""
    result = runner.invoke(tasks, ['status', 'nonexistent'])
    
    assert result.exit_code == 0
    assert "Project nonexistent not found" in result.output


def test_tasks_list(runner, temp_orchestrator_dir):
    """Test listing all projects."""
    # Create multiple projects
    runner.invoke(tasks, ['create', 'project1'])
    runner.invoke(tasks, ['create', 'project2'])
    
    result = runner.invoke(tasks, ['list'])
    
    assert result.exit_code == 0
    assert "project1" in result.output
    assert "project2" in result.output


def test_tasks_distribute(runner, temp_orchestrator_dir):
    """Test task distribution."""
    # Create project with tasks
    runner.invoke(tasks, ['create', 'test-project'])
    project_dir = temp_orchestrator_dir / "projects" / "test-project"
    
    # Add test tasks
    tasks_content = """# Project Tasks

## Frontend Tasks
- [ ] Create login page
- [ ] Add user dashboard

## Backend Tasks  
- [ ] Setup authentication
- [ ] Create API endpoints
"""
    (project_dir / "tasks.md").write_text(tasks_content)
    
    result = runner.invoke(tasks, ['distribute', 'test-project'])
    
    assert result.exit_code == 0
    assert "Distributed tasks for test-project" in result.output
    
    # Check agent files created
    agents_dir = project_dir / "agents"
    assert len(list(agents_dir.glob("*.md"))) > 0


def test_tasks_export(runner, temp_orchestrator_dir):
    """Test exporting project."""
    # Create and setup project
    runner.invoke(tasks, ['create', 'test-project'])
    project_dir = temp_orchestrator_dir / "projects" / "test-project"
    
    with tempfile.TemporaryDirectory() as export_dir:
        result = runner.invoke(tasks, ['export', 'test-project', export_dir])
        
        assert result.exit_code == 0
        assert "Exported test-project to" in result.output
        
        # Check export created
        export_files = list(Path(export_dir).glob("test-project_*.tar.gz"))
        assert len(export_files) == 1


def test_tasks_archive(runner, temp_orchestrator_dir):
    """Test archiving completed project."""
    # Create project
    runner.invoke(tasks, ['create', 'test-project'])
    
    result = runner.invoke(tasks, ['archive', 'test-project'])
    
    assert result.exit_code == 0
    assert "Archived test-project" in result.output
    
    # Verify moved to archive
    assert not (temp_orchestrator_dir / "projects" / "test-project").exists()
    assert (temp_orchestrator_dir / "archive" / "test-project").exists()


def test_tasks_generate(runner, temp_orchestrator_dir):
    """Test task generation from PRD."""
    # Create project with PRD
    runner.invoke(tasks, ['create', 'test-project'])
    project_dir = temp_orchestrator_dir / "projects" / "test-project"
    
    prd_content = """# Test Project

## Overview
A simple web application.

## Requirements
1. User authentication
2. Dashboard
3. API endpoints
"""
    (project_dir / "prd.md").write_text(prd_content)
    
    # Mock the AI task generation
    with patch('tmux_orchestrator.cli.tasks.generate_tasks_from_prd') as mock_gen:
        mock_gen.return_value = "- [ ] Implement authentication\n- [ ] Create dashboard"
        
        result = runner.invoke(tasks, ['generate', 'test-project'])
        
        assert result.exit_code == 0
        assert "Generated tasks for test-project" in result.output
        
        # Verify tasks were written
        tasks_file = project_dir / "tasks.md"
        assert "Implement authentication" in tasks_file.read_text()


def test_tasks_group_exists():
    """Test that tasks command group exists and has expected subcommands."""
    assert callable(tasks)
    
    command_names = list(tasks.commands.keys())
    expected_commands = {'create', 'status', 'list', 'distribute', 'export', 'archive', 'generate'}
    
    assert expected_commands.issubset(set(command_names))