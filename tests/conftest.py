"""Pytest configuration and shared fixtures for Tmux-Orchestrator tests."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, Mock

import pytest
from click.testing import CliRunner

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
    mock.list_sessions.return_value = ["session1", "session2"]
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
        is_healthy=True, failure_count=0, last_check=None, status_message="healthy"
    )

    return mock


@pytest.fixture
def mock_recovery_functions():
    """Provide mocked recovery functions for testing."""
    mock = Mock()

    # Configure recovery function returns
    mock.detect_failure.return_value = "healthy"
    mock.check_agent_health.return_value = Mock(
        is_healthy=True, failure_count=0, last_check=None, status_message="healthy"
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
        "last_activity": "2024-01-01T00:00:00Z",
    }


@pytest.fixture(autouse=True)
def cleanup_test_logs(tmp_path, monkeypatch):
    """Automatically clean up test logs and use temp directories."""
    # Use temporary directory for logs during testing
    test_log_dir = tmp_path / "logs"
    test_log_dir.mkdir()

    monkeypatch.setenv("TMUX_ORC_LOG_DIR", str(test_log_dir))

    yield

    # Cleanup is automatic with tmp_path


# ===== COMMONLY USED FIXTURES =====
# These fixtures are used across many test files and have been consolidated here


@pytest.fixture
def mock_tmux() -> Mock:
    """Create a mock TMUXManager for testing.

    This is the most commonly used fixture across the test suite.
    Use this instead of creating local mock_tmux fixtures.
    """
    return MagicMock(spec=TMUXManager)


@pytest.fixture
def logger() -> Mock:
    """Create a mock logger for testing.

    Used by monitor tests and other components that use logging.
    """
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner.

    Used by CLI tests for testing command line interfaces.
    """
    return CliRunner()


@pytest.fixture
def temp_activity_file() -> Generator[Path, None, None]:
    """Create a temporary activity file for testing.

    Used by report_activity and get_agent_status tests.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
        # Initialize empty activity file
        json.dump([], f)
    yield temp_path
    # Clean up
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_schedule_file() -> Generator[Path, None, None]:
    """Create a temporary schedule file for testing.

    Used by schedule_checkin tests.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
        # Initialize empty schedule file
        json.dump([], f)
    yield temp_path
    # Clean up
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_orchestrator_dir() -> Generator[Path, None, None]:
    """Create temporary orchestrator directory.

    Used by CLI tests that need a temporary working directory.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_uuid() -> str:
    """Generate unique test identifier for traceability.

    This fixture provides a unique UUID for each test run,
    enabling traceability across test executions and debugging.
    Used throughout the test suite for consistent test identification.
    """
    import uuid

    return str(uuid.uuid4())
