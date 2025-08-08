"""Tests for setup CLI commands."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.setup import setup
from tmux_orchestrator.cli.setup_vscode import setup_vscode


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_project_dir():
    """Create temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_setup_command(runner):
    """Test main setup command."""
    with patch('tmux_orchestrator.cli.setup.setup_completion'):
        with patch('tmux_orchestrator.cli.setup.verify_tmux_installed') as mock_verify:
            with patch('tmux_orchestrator.cli.setup.create_directories') as mock_create:
                with patch('builtins.print') as mock_print:
                    mock_verify.return_value = True
                    
                    result = runner.invoke(setup)
                    
                    assert result.exit_code == 0
                    mock_verify.assert_called_once()
                    mock_create.assert_called_once()
                    
                    # Check for success messages
                    print_calls = [call[0][0] for call in mock_print.call_args_list]
                    assert any("Setup complete" in str(call) for call in print_calls)


def test_setup_tmux_not_installed(runner):
    """Test setup when tmux is not installed."""
    with patch('shutil.which', return_value=None):
        result = runner.invoke(setup)
        
        assert result.exit_code == 0
        assert "tmux is not installed" in result.output


def test_setup_vscode_creates_structure(runner, temp_project_dir):
    """Test VS Code setup creates correct structure."""
    with patch('os.getcwd', return_value=str(temp_project_dir)):
        result = runner.invoke(setup_vscode)
        
        assert result.exit_code == 0
        
        # Check directory structure
        vscode_dir = temp_project_dir / ".vscode"
        assert vscode_dir.exists()
        
        # Check tasks.json created
        tasks_file = vscode_dir / "tasks.json"
        assert tasks_file.exists()
        
        # Verify tasks content
        content = tasks_file.read_text()
        assert "Open Orchestrator Terminal" in content
        assert "tmux attach -t" in content


def test_setup_vscode_existing_tasks(runner, temp_project_dir):
    """Test VS Code setup with existing tasks.json."""
    vscode_dir = temp_project_dir / ".vscode"
    vscode_dir.mkdir()
    
    # Create existing tasks.json
    existing_tasks = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "Existing Task",
                "type": "shell",
                "command": "echo hello"
            }
        ]
    }
    
    tasks_file = vscode_dir / "tasks.json"
    import json
    tasks_file.write_text(json.dumps(existing_tasks, indent=2))
    
    with patch('os.getcwd', return_value=str(temp_project_dir)):
        result = runner.invoke(setup_vscode)
        
        assert result.exit_code == 0
        
        # Check merged content
        content = json.loads(tasks_file.read_text())
        
        # Should have both existing and new tasks
        task_labels = [task['label'] for task in content['tasks']]
        assert "Existing Task" in task_labels
        assert "Open Orchestrator Terminal" in task_labels


def test_setup_vscode_with_project_path(runner, temp_project_dir):
    """Test VS Code setup with specific project path."""
    project_subdir = temp_project_dir / "my-project"
    project_subdir.mkdir()
    
    result = runner.invoke(setup_vscode, [str(project_subdir)])
    
    assert result.exit_code == 0
    
    # Check created in correct location
    vscode_dir = project_subdir / ".vscode"
    assert vscode_dir.exists()
    assert (vscode_dir / "tasks.json").exists()


def test_setup_completion_bash(runner):
    """Test shell completion setup for bash."""
    with patch('os.path.expanduser') as mock_expand:
        with patch('os.path.exists') as mock_exists:
            with patch('builtins.open', mock_open()) as mock_file:
                mock_expand.return_value = "/home/user/.bashrc"
                mock_exists.return_value = True
                
                # Import and test the function directly
                from tmux_orchestrator.cli.setup import setup_completion
                setup_completion()
                
                # Verify completion command was written
                mock_file.assert_called()
                handle = mock_file()
                written_content = ''.join(call[0][0] for call in handle.write.call_args_list)
                assert "_TMUX_ORC_COMPLETE" in written_content


def test_verify_tmux_installed(runner):
    """Test tmux verification."""
    from tmux_orchestrator.cli.setup import verify_tmux_installed
    
    with patch('shutil.which', return_value='/usr/bin/tmux'):
        assert verify_tmux_installed() is True
    
    with patch('shutil.which', return_value=None):
        assert verify_tmux_installed() is False


def test_create_directories(runner):
    """Test directory creation."""
    from tmux_orchestrator.cli.setup import create_directories
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('os.path.expanduser', return_value=tmpdir):
            create_directories()
            
            # Check directories created
            orc_dir = Path(tmpdir) / ".tmux_orchestrator"
            assert orc_dir.exists()
            assert (orc_dir / "projects").exists()
            assert (orc_dir / "templates").exists()
            assert (orc_dir / "archive").exists()
            assert (orc_dir / "registry").exists()
            assert (orc_dir / "logs").exists()


def test_setup_vscode_invalid_json(runner, temp_project_dir):
    """Test VS Code setup with invalid existing JSON."""
    vscode_dir = temp_project_dir / ".vscode"
    vscode_dir.mkdir()
    
    # Create invalid JSON
    tasks_file = vscode_dir / "tasks.json"
    tasks_file.write_text("{ invalid json")
    
    with patch('os.getcwd', return_value=str(temp_project_dir)):
        result = runner.invoke(setup_vscode)
        
        assert result.exit_code == 0
        assert "Error reading existing" in result.output or "Created new" in result.output