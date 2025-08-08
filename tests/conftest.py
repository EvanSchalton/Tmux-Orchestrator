"""Pytest configuration and shared fixtures for Tmux-Orchestrator tests."""

import pytest
from unittest.mock import Mock, MagicMock
from click.testing import CliRunner
from fastapi.testclient import TestClient

from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_tmux_manager():
    """Provide a mocked TMUXManager for testing."""
    mock = Mock(spec=TMUXManager)
    
    # Configure common return values
    mock.list_sessions.return_value = ['session1', 'session2']
    mock.session_exists.return_value = True
    mock.send_keys.return_value = True
    mock.attach_session.return_value = True
    mock.kill_window.return_value = True
    mock.new_window.return_value = True
    mock.get_pane_content.return_value = "Mock pane content"
    
    return mock


@pytest.fixture
def mock_agent_operations():
    """Provide mocked agent operations for testing."""
    mock = Mock()
    
    # Configure success responses
    mock.restart_agent.return_value = {"success": True, "message": "Agent restarted"}
    mock.check_agent_health.return_value = Mock(
        is_healthy=True,
        failure_count=0,
        last_check=None,
        status_message="healthy"
    )
    
    return mock


@pytest.fixture
def mock_recovery_functions():
    """Provide mocked recovery functions for testing."""
    mock = Mock()
    
    # Configure recovery function returns
    mock.detect_failure.return_value = "healthy"
    mock.check_agent_health.return_value = Mock(
        is_healthy=True,
        failure_count=0,
        last_check=None,
        status_message="healthy"
    )
    
    return mock


@pytest.fixture
def sample_agent_data():
    """Provide sample agent data for testing."""
    return {
        "session": "test-session",
        "window": "1",
        "agent_type": "developer",
        "status": "active",
        "last_activity": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_fastapi_client():
    """Provide a test client for FastAPI route testing."""
    from tmux_orchestrator.server import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_test_logs(tmp_path, monkeypatch):
    """Automatically clean up test logs and use temp directories."""
    # Use temporary directory for logs during testing
    test_log_dir = tmp_path / "logs"
    test_log_dir.mkdir()
    
    monkeypatch.setenv("TMUX_ORC_LOG_DIR", str(test_log_dir))
    
    yield
    
    # Cleanup is automatic with tmp_path