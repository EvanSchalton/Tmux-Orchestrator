"""Tests for get_team_status business logic function."""

from typing import Any
from unittest.mock import Mock

import pytest

from tmux_orchestrator.core.team_operations.get_team_status import (
    _determine_window_status,
    _determine_window_type,
    get_team_status,
)
from tmux_orchestrator.utils.tmux import TMUXManager


def test_get_team_status_success() -> None:
    """Test successful team status retrieval."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True

    # Mock session info
    mock_sessions: list[dict[str, str]] = [{"name": "test-session", "created": "1234567890", "attached": "1"}]
    mock_tmux.list_sessions.return_value = mock_sessions

    # Mock windows
    mock_windows: list[dict[str, str]] = [
        {"index": "0", "name": "Claude-Frontend"},
        {"index": "1", "name": "Dev-Server"},
    ]
    mock_tmux.list_windows.return_value = mock_windows

    # Mock pane content
    mock_tmux.capture_pane.return_value = "Working on frontend..."
    mock_tmux._is_idle.return_value = False

    session: str = "test-session"

    # Act
    result: dict[str, Any] | None = get_team_status(mock_tmux, session)

    # Assert
    assert result is not None
    assert result["session_info"] == mock_sessions[0]
    assert len(result["windows"]) == 2
    assert result["summary"]["total_windows"] == 2
    assert result["summary"]["active_agents"] == 1  # Only Claude-Frontend counts as agent

    # Check window details
    frontend_window = next(w for w in result["windows"] if w["name"] == "Claude-Frontend")
    assert frontend_window["type"] == "Frontend Dev"
    assert frontend_window["status"] == "Active"
    assert frontend_window["target"] == "test-session:0"


def test_get_team_status_session_not_found() -> None:
    """Test when session doesn't exist."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = False

    session: str = "nonexistent-session"

    # Act
    result: dict[str, Any] | None = get_team_status(mock_tmux, session)

    # Assert
    assert result is None
    mock_tmux.has_session.assert_called_once_with(session)


def test_get_team_status_session_info_not_found() -> None:
    """Test when session exists but info can't be retrieved."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.list_sessions.return_value = []  # Empty sessions list

    session: str = "test-session"

    # Act
    result: dict[str, Any] | None = get_team_status(mock_tmux, session)

    # Assert
    assert result is None


def test_get_team_status_no_windows() -> None:
    """Test when session has no windows."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True

    mock_sessions: list[dict[str, str]] = [{"name": "test-session", "created": "1234567890"}]
    mock_tmux.list_sessions.return_value = mock_sessions
    mock_tmux.list_windows.return_value = []  # No windows

    session: str = "test-session"

    # Act
    result: dict[str, Any] | None = get_team_status(mock_tmux, session)

    # Assert
    assert result is not None
    assert result["windows"] == []
    assert result["summary"]["total_windows"] == 0
    assert result["summary"]["active_agents"] == 0


@pytest.mark.parametrize(
    "window_name,expected_type",
    [
        ("Claude-Frontend", "Frontend Dev"),
        ("claude-backend", "Backend Dev"),
        ("PM-Window", "Project Manager"),
        ("qa-test", "QA Engineer"),
        ("Dev-Server", "Dev Server"),
        ("Shell-Window", "Shell"),
        ("Random-Window", "Other"),
    ],
)
def test_determine_window_type(window_name: str, expected_type: str) -> None:
    """Test window type determination logic."""
    # Act
    result: str = _determine_window_type(window_name)

    # Assert
    assert result == expected_type


@pytest.mark.parametrize(
    "pane_content,is_idle,expected_status,expected_activity",
    [
        ("Working on code...", False, "Active", "Working..."),
        ("Waiting for input", True, "Idle", "Waiting for task"),
        ("Error: failed to compile", False, "Error", "Has errors"),
        ("Task completed successfully", False, "Complete", "Task completed"),
    ],
)
def test_determine_window_status(
    pane_content: str, is_idle: bool, expected_status: str, expected_activity: str
) -> None:
    """Test window status determination logic."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux._is_idle.return_value = is_idle

    # Act
    status, activity = _determine_window_status(mock_tmux, pane_content)

    # Assert
    assert status == expected_status
    assert activity == expected_activity


def test_get_team_status_agent_counting() -> None:
    """Test that agent counting works correctly."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True

    mock_sessions: list[dict[str, str]] = [{"name": "test-session", "created": "1234567890"}]
    mock_tmux.list_sessions.return_value = mock_sessions

    # Mix of agent and non-agent windows
    mock_windows: list[dict[str, str]] = [
        {"index": "0", "name": "claude-frontend"},  # Agent
        {"index": "1", "name": "pm-manager"},  # Agent
        {"index": "2", "name": "dev-server"},  # Not agent
        {"index": "3", "name": "shell"},  # Not agent
        {"index": "4", "name": "Claude-QA"},  # Agent
    ]
    mock_tmux.list_windows.return_value = mock_windows
    mock_tmux.capture_pane.return_value = "test content"
    mock_tmux._is_idle.return_value = False

    session: str = "test-session"

    # Act
    result: dict[str, Any] | None = get_team_status(mock_tmux, session)

    # Assert
    assert result is not None
    assert result["summary"]["total_windows"] == 5
    assert result["summary"]["active_agents"] == 3  # claude-frontend, pm-manager, Claude-QA
