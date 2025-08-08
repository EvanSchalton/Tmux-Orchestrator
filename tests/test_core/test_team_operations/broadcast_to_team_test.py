"""Tests for broadcast_to_team business logic function."""

from typing import Dict, List, Union
from unittest.mock import Mock

import pytest

from tmux_orchestrator.core.team_operations.broadcast_to_team import broadcast_to_team
from tmux_orchestrator.utils.tmux import TMUXManager


def test_broadcast_to_team_success() -> None:
    """Test successful broadcast to team agents."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.send_message.return_value = True

    # Mock windows with agents
    mock_windows: List[Dict[str, str]] = [
        {'index': '0', 'name': 'claude-frontend'},
        {'index': '1', 'name': 'pm-manager'},
        {'index': '2', 'name': 'dev-server'},  # Not an agent
    ]
    mock_tmux.list_windows.return_value = mock_windows

    session: str = "test-session"
    message: str = "Test broadcast message"

    # Act
    success, summary, results = broadcast_to_team(mock_tmux, session, message)

    # Assert
    assert success is True
    assert "2/2 agents reached" in summary
    assert len(results) == 2  # Only agent windows

    # Verify send_message calls
    assert mock_tmux.send_message.call_count == 2
    mock_tmux.send_message.assert_any_call("test-session:0", message)
    mock_tmux.send_message.assert_any_call("test-session:1", message)

    # Check results structure
    for result in results:
        assert 'target' in result
        assert 'window_name' in result
        assert 'success' in result
        assert result['success'] is True


def test_broadcast_to_team_session_not_found() -> None:
    """Test broadcast when session doesn't exist."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = False

    session: str = "nonexistent-session"
    message: str = "Test message"

    # Act
    success, summary, results = broadcast_to_team(mock_tmux, session, message)

    # Assert
    assert success is False
    assert "Session 'nonexistent-session' not found" == summary
    assert results == []

    # Verify no message sending attempts
    mock_tmux.send_message.assert_not_called()


def test_broadcast_to_team_no_agents() -> None:
    """Test broadcast when no agent windows found."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True

    # Only non-agent windows
    mock_windows: List[Dict[str, str]] = [
        {'index': '0', 'name': 'shell'},
        {'index': '1', 'name': 'dev-server'},
    ]
    mock_tmux.list_windows.return_value = mock_windows

    session: str = "test-session"
    message: str = "Test message"

    # Act
    success, summary, results = broadcast_to_team(mock_tmux, session, message)

    # Assert
    assert success is False
    assert "No agent windows found in session 'test-session'" == summary
    assert results == []


def test_broadcast_to_team_partial_failure() -> None:
    """Test broadcast with some failures."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True

    # Mock send_message to succeed for first agent, fail for second
    mock_tmux.send_message.side_effect = [True, False]

    mock_windows: List[Dict[str, str]] = [
        {'index': '0', 'name': 'claude-frontend'},
        {'index': '1', 'name': 'claude-backend'},
    ]
    mock_tmux.list_windows.return_value = mock_windows

    session: str = "test-session"
    message: str = "Test message"

    # Act
    success, summary, results = broadcast_to_team(mock_tmux, session, message)

    # Assert
    assert success is True  # At least one succeeded
    assert "1/2 agents reached" in summary
    assert len(results) == 2

    # Check individual results
    assert results[0]['success'] is True
    assert results[0]['target'] == "test-session:0"
    assert results[1]['success'] is False
    assert results[1]['target'] == "test-session:1"


def test_broadcast_to_team_all_failures() -> None:
    """Test broadcast when all sends fail."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.send_message.return_value = False  # All fail

    mock_windows: List[Dict[str, str]] = [
        {'index': '0', 'name': 'claude-frontend'},
        {'index': '1', 'name': 'pm-manager'},
    ]
    mock_tmux.list_windows.return_value = mock_windows

    session: str = "test-session"
    message: str = "Test message"

    # Act
    success, summary, results = broadcast_to_team(mock_tmux, session, message)

    # Assert
    assert success is False  # No successes
    assert "0/2 agents reached" in summary
    assert len(results) == 2
    assert all(not result['success'] for result in results)


@pytest.mark.parametrize("window_names,expected_agent_count", [
    (['shell', 'dev-server'], 0),
    (['claude-agent'], 1),
    (['pm-window'], 1),
    (['Claude-Frontend', 'PM-Manager'], 2),
    (['claude-dev', 'pm-test', 'shell'], 2),
    (['CLAUDE-UPPERCASE', 'pm-lowercase'], 2),
])
def test_broadcast_to_team_agent_detection(
    window_names: List[str],
    expected_agent_count: int
) -> None:
    """Test agent window detection with various naming patterns."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.send_message.return_value = True

    mock_windows: List[Dict[str, str]] = [
        {'index': str(i), 'name': name}
        for i, name in enumerate(window_names)
    ]
    mock_tmux.list_windows.return_value = mock_windows

    session: str = "test-session"
    message: str = "Test message"

    # Act
    success, summary, results = broadcast_to_team(mock_tmux, session, message)

    # Assert
    if expected_agent_count == 0:
        assert success is False
        assert "No agent windows found" in summary
        assert results == []
    else:
        assert len(results) == expected_agent_count
        assert mock_tmux.send_message.call_count == expected_agent_count


def test_broadcast_to_team_result_structure() -> None:
    """Test the structure of broadcast results."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.send_message.return_value = True

    mock_windows: List[Dict[str, str]] = [
        {'index': '5', 'name': 'claude-test-agent'},
    ]
    mock_tmux.list_windows.return_value = mock_windows

    session: str = "my-session"
    message: str = "Hello agents!"

    # Act
    success, summary, results = broadcast_to_team(mock_tmux, session, message)

    # Assert
    assert len(results) == 1
    result: Dict[str, Union[str, bool]] = results[0]

    assert result['target'] == "my-session:5"
    assert result['window_name'] == "claude-test-agent"
    assert result['success'] is True

    # Ensure all expected keys are present
    expected_keys = {'target', 'window_name', 'success'}
    assert set(result.keys()) == expected_keys
