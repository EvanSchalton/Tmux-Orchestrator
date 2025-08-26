"""Tests for list_all_teams business logic function."""

from typing import Any
from unittest.mock import Mock

import pytest

from tmux_orchestrator.core.team_operations.list_all_teams import list_all_teams
from tmux_orchestrator.utils.tmux import TMUXManager

# TMUXManager import removed - using comprehensive_mock_tmux fixture


def test_list_all_teams_success() -> None:
    """Test successful listing of all teams."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)

    # Mock sessions
    mock_sessions: list[dict[str, str]] = [
        {"name": "frontend-team", "attached": "1", "created": "1234567890"},
        {"name": "backend-team", "attached": "0", "created": "1234567891"},
    ]
    mock_tmux.list_sessions.return_value = mock_sessions

    # Mock windows for each session
    mock_tmux.list_windows.side_effect = [
        [{"name": "claude-frontend"}, {"name": "pm-manager"}, {"name": "dev-server"}],
        [{"name": "claude-backend"}, {"name": "shell"}],
    ]

    # Act
    result: list[dict[str, Any]] = list_all_teams(mock_tmux)

    # Assert
    assert len(result) == 2

    # Check frontend team
    frontend_team = next(team for team in result if team["name"] == "frontend-team")
    assert frontend_team["windows"] == 3
    assert frontend_team["agents"] == 2  # claude-frontend, pm-manager
    assert frontend_team["status"] == "Active"  # attached = '1'
    assert frontend_team["created"] == "1234567890"

    # Check backend team
    backend_team = next(team for team in result if team["name"] == "backend-team")
    assert backend_team["windows"] == 2
    assert backend_team["agents"] == 1  # claude-backend
    assert backend_team["status"] == "Detached"  # attached = '0'
    assert backend_team["created"] == "1234567891"


def test_list_all_teams_empty() -> None:
    """Test when no sessions exist."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.list_sessions.return_value = []

    # Act
    result: list[dict[str, Any]] = list_all_teams(mock_tmux)

    # Assert
    assert result == []


def test_list_all_teams_no_windows() -> None:
    """Test team with no windows."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)

    mock_sessions: list[dict[str, str]] = [{"name": "empty-team", "attached": "0", "created": "1234567890"}]
    mock_tmux.list_sessions.return_value = mock_sessions
    mock_tmux.list_windows.return_value = []  # No windows

    # Act
    result: list[dict[str, Any]] = list_all_teams(mock_tmux)

    # Assert
    assert len(result) == 1
    team = result[0]
    assert team["name"] == "empty-team"
    assert team["windows"] == 0
    assert team["agents"] == 0
    assert team["status"] == "Detached"


@pytest.mark.parametrize(
    "window_names,expected_agent_count",
    [
        ([], 0),
        (["shell", "dev-server"], 0),
        (["claude-agent"], 1),
        (["pm-window"], 1),
        (["Claude-Frontend", "PM-Manager"], 2),
        (["claude-dev", "pm-test", "shell", "server"], 2),
    ],
)
def test_list_all_teams_agent_counting(window_names: list[str], expected_agent_count: int) -> None:
    """Test agent counting with various window name patterns."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)

    mock_sessions: list[dict[str, str]] = [{"name": "test-team", "attached": "1", "created": "1234567890"}]
    mock_tmux.list_sessions.return_value = mock_sessions

    mock_windows: list[dict[str, str]] = [{"name": name} for name in window_names]
    mock_tmux.list_windows.return_value = mock_windows

    # Act
    result: list[dict[str, Any]] = list_all_teams(mock_tmux)

    # Assert
    assert len(result) == 1
    team = result[0]
    assert team["agents"] == expected_agent_count
    assert team["windows"] == len(window_names)


@pytest.mark.parametrize(
    "attached_value,expected_status",
    [
        ("1", "Active"),
        ("0", "Detached"),
        (None, "Active"),  # Default when not specified
        ("", "Active"),  # Default for empty string
    ],
)
def test_list_all_teams_status_determination(attached_value: str, expected_status: str) -> None:
    """Test session status determination based on attached value."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)

    session: dict[str, str] = {"name": "test-team", "created": "1234567890"}
    if attached_value is not None:
        session["attached"] = attached_value

    mock_sessions: list[dict[str, str]] = [session]
    mock_tmux.list_sessions.return_value = mock_sessions
    mock_tmux.list_windows.return_value = []

    # Act
    result: list[dict[str, Any]] = list_all_teams(mock_tmux)

    # Assert
    assert len(result) == 1
    team = result[0]
    assert team["status"] == expected_status


def test_list_all_teams_missing_created_field() -> None:
    """Test handling of sessions without created field."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)

    mock_sessions: list[dict[str, str]] = [{"name": "test-team", "attached": "1"}]  # No 'created' field
    mock_tmux.list_sessions.return_value = mock_sessions
    mock_tmux.list_windows.return_value = []

    # Act
    result: list[dict[str, Any]] = list_all_teams(mock_tmux)

    # Assert
    assert len(result) == 1
    team = result[0]
    assert team["created"] == "Unknown"
