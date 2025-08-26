"""Pytest configuration and shared fixtures for Tmux-Orchestrator tests."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, Mock

import pytest
from click.testing import CliRunner

from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI runner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_tmux_manager() -> Mock:
    """Provide a mocked TMUXManager for testing."""
    mock = Mock(spec=TMUXManager)

    # Configure common return values
    mock.list_sessions.return_value = [{"name": "session1"}, {"name": "session2"}]
    mock.has_session.return_value = True
    mock.send_keys.return_value = True
    mock.kill_window.return_value = True
    mock.create_window.return_value = True
    mock.capture_pane.return_value = "Mock pane content"

    return mock


@pytest.fixture
def mock_agent_operations() -> Mock:
    """Provide mocked agent operations for testing."""
    mock = Mock()

    # Configure success responses
    mock.restart_agent.return_value = {"success": True, "message": "Agent restarted"}
    mock.check_agent_health.return_value = Mock(
        is_healthy=True, failure_count=0, last_check=None, status_message="healthy"
    )

    return mock


@pytest.fixture
def mock_recovery_functions() -> Mock:
    """Provide mocked recovery functions for testing."""
    mock = Mock()

    # Configure recovery function returns
    mock.detect_failure.return_value = "healthy"
    mock.check_agent_health.return_value = Mock(
        is_healthy=True, failure_count=0, last_check=None, status_message="healthy"
    )

    return mock


@pytest.fixture
def sample_agent_data() -> Dict[str, Any]:
    """Provide sample agent data for testing."""
    return {
        "session": "test-session",
        "window": "1",
        "agent_type": "developer",
        "status": "active",
        "last_activity": "2024-01-01T00:00:00Z",
    }


@pytest.fixture(autouse=True)
def cleanup_test_logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
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


class MockTMUXManager:
    """Featureless mock TMUXManager that prevents real tmux operations.

    This mock completely replaces TMUXManager functionality to ensure
    no real tmux sessions are created during testing.
    """

    def __init__(self, cache_ttl: float = 5.0):
        """Mock initialization."""
        self.tmux_cmd = "mock-tmux"
        self._mock_sessions = {}
        self._mock_windows = {}
        self._cache_ttl = cache_ttl
        self._agent_cache = {}
        self._agent_cache_time = 0.0
        self._session_cache = {}
        self._session_cache_time = 0.0
        self._batch_size = 10

    def list_agents_optimized(self) -> list[dict[str, str]]:
        """Mock optimized agent listing."""
        return []

    def list_agents_ultra_optimized(self) -> list[dict[str, str]]:
        """Mock ultra-optimized agent listing."""
        return []

    def invalidate_cache(self) -> None:
        """Mock cache invalidation."""
        self._agent_cache.clear()
        self._session_cache.clear()

    def has_session_optimized(self, session_name: str) -> bool:
        """Mock optimized session check."""
        return session_name in self._mock_sessions

    def has_session(self, session_name: str) -> bool:
        """Mock session check."""
        return session_name in self._mock_sessions

    def send_keys_optimized(self, target: str, keys: str, literal: bool = False) -> bool:
        """Mock optimized send keys."""
        return True

    def send_keys(self, target: str, keys: str, literal: bool = False) -> bool:
        """Mock send keys."""
        return True

    def quick_deploy_dry_run_optimized(self, team_type: str, size: int, project_name: str) -> tuple[bool, str, float]:
        """Mock quick deploy dry run."""
        return True, f"Mock deployment of {team_type} team with {size} members", 0.1

    def list_sessions_cached(self) -> list[dict[str, str]]:
        """Mock cached session listing."""
        return [{"name": name, "created": "mock"} for name in self._mock_sessions.keys()]

    def list_sessions(self) -> list[dict[str, str]]:
        """Mock session listing."""
        return [{"name": name, "created": "mock"} for name in self._mock_sessions.keys()]

    def list_agents(self) -> list[dict[str, str]]:
        """Mock agent listing that processes mocked session and window data."""
        agents = []

        # Get sessions from mock methods (may be patched in tests)
        try:
            sessions = self.list_sessions()
        except Exception:
            sessions = []

        for session in sessions:
            session_name = session.get("name", "")
            try:
                windows = self.list_windows(session_name)
            except Exception:
                windows = []

            for window in windows:
                window_name = window.get("name", "")
                window_index = window.get("index", "0")

                # Check if this looks like an agent window
                if self._is_agent_window(window_name):
                    agents.append(
                        {
                            "session": session_name,
                            "window": str(window_index),
                            "type": self._determine_agent_type(window_name, session_name),
                            "status": "Active",  # Mock status
                            "target": f"{session_name}:{window_index}",
                        }
                    )

        return agents

    def _is_agent_window(self, window_name: str) -> bool:
        """Check if window appears to be an agent window."""
        if not window_name:
            return False
        window_lower = window_name.lower()
        agent_keywords = [
            "claude",
            "pm",
            "developer",
            "qa",
            "devops",
            "reviewer",
            "backend",
            "frontend",
            "manager",
            "engineer",
            "specialist",
            "writer",
            "database",
            "security",
            "api",
            "research",
            "automation",
            "analyst",
            "ops",
            "dev",
        ]
        return any(keyword in window_lower for keyword in agent_keywords)

    def _determine_agent_type(self, window_name: str, session_name: str = "") -> str:
        """Determine agent type from window name and session context."""
        if not window_name:
            return "Unknown"

        session_lower = session_name.lower()

        # Remove Claude- prefix for analysis
        clean_name = window_name
        if clean_name.lower().startswith("claude-"):
            clean_name = clean_name[7:]  # Remove "Claude-" prefix
        elif clean_name.lower() == "claude":
            clean_name = ""

        clean_lower = clean_name.lower()

        # Enhanced type mapping with session context
        if "pm" in clean_lower or "project-manager" in clean_lower or "manager" in clean_lower:
            return "PM"
        elif "qa" in clean_lower or "quality-analyst" in clean_lower or "testing" in session_lower:
            return "QA"
        elif "backend" in clean_lower or "backend" in session_lower:
            return "Backend"
        elif "frontend" in clean_lower or "frontend" in session_lower or "ui" in clean_lower:
            return "Frontend"
        elif "devops" in clean_lower or "ops" in clean_lower:
            return "DevOps"
        elif "review" in clean_lower:
            return "Reviewer"
        elif "doc" in clean_lower or "writer" in clean_lower:
            return "Writer"
        elif "database" in clean_lower or "db" in clean_lower or "data" in clean_lower:
            return "Database"
        elif "security" in clean_lower:
            return "Security Expert"
        elif "api" in clean_lower:
            return "Api Specialist"
        elif "research" in clean_lower:
            return "Researcher"
        elif "dev" in clean_lower or "developer" in clean_lower:
            return "Developer"
        elif "specialist" in clean_lower:
            return "Frontend"  # Default for specialist
        elif "engineer" in clean_lower:
            return "DevOps"  # Default for engineer
        elif "automation" in clean_lower:
            return "QA"  # Test automation
        else:
            # Fallback to title case of clean name, or "Developer" if empty
            return clean_name.title() if clean_name else "Developer"

    def capture_pane(self, target: str, lines: int = 50) -> str:
        """Mock pane capture."""
        return "Mock pane content"

    def list_windows(self, session: str) -> list[dict[str, str]]:
        """Mock window listing."""
        return self._mock_windows.get(session, [])

    def create_window(self, session_name: str, window_name: str, start_directory: str = None) -> bool:
        """Mock window creation."""
        if session_name not in self._mock_windows:
            self._mock_windows[session_name] = []
        self._mock_windows[session_name].append(
            {"name": window_name, "index": str(len(self._mock_windows[session_name])), "active": "1"}
        )
        return True

    def send_text(self, target: str, text: str) -> bool:
        """Mock text sending."""
        return True

    def press_enter(self, target: str) -> bool:
        """Mock enter press."""
        return True

    def press_ctrl_u(self, target: str) -> bool:
        """Mock Ctrl+U press."""
        return True

    def send_message(self, target: str, message: str, delay: float = 0.5) -> bool:
        """Mock message sending."""
        return True

    def kill_window(self, target: str) -> bool:
        """Mock window kill."""
        return True

    def kill_session(self, session_name: str) -> bool:
        """Mock session kill."""
        if session_name in self._mock_sessions:
            del self._mock_sessions[session_name]
        if session_name in self._mock_windows:
            del self._mock_windows[session_name]
        return True

    def press_escape(self, target: str) -> bool:
        """Mock escape press."""
        return True

    def press_ctrl_e(self, target: str) -> bool:
        """Mock Ctrl+E press."""
        return True

    def run(self, command: str) -> bool:
        """Mock command run."""
        return True

    def _validate_input(self, value: str, field_name: str = "input") -> str:
        """Mock input validation."""
        return value

    def _is_idle(self, pane_content: str) -> bool:
        """Mock idle check."""
        return False

    def _get_sessions_and_windows_batch(self) -> dict[str, list[dict[str, str]]]:
        """Mock batch sessions and windows."""
        return {name: windows for name, windows in self._mock_windows.items()}

    def _is_agent_window(self, window_name: str) -> bool:
        """Mock agent window check."""
        return "agent" in window_name.lower() or "Claude-" in window_name

    def _batch_get_agent_statuses(self, agent_windows: list[dict[str, Any]]) -> dict[int, str]:
        """Mock batch status check."""
        return {i: "mock-active" for i in range(len(agent_windows))}

    def _get_batch_statuses(self, batch: list[dict[str, Any]], offset: int) -> dict[int, str]:
        """Mock batch status."""
        return {i + offset: "mock-active" for i in range(len(batch))}

    def _get_basic_agent_list(self) -> list[dict[str, str]]:
        """Mock basic agent list."""
        return []

    def create_session(self, session_name: str) -> bool:
        """Mock session creation."""
        if session_name not in self._mock_sessions:
            self._mock_sessions[session_name] = True
            # Initialize empty window list for the new session
            self._mock_windows[session_name] = []
        return True


@pytest.fixture
def comprehensive_mock_tmux() -> MockTMUXManager:
    """Create a comprehensive mock TMUXManager that prevents all real tmux operations.

    This fixture provides a complete mock that:
    - Prevents any real tmux session creation
    - Provides realistic mock behavior
    - Supports all TMUXManager methods
    - Allows tests to focus on logic rather than infrastructure
    """
    return MockTMUXManager()


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
