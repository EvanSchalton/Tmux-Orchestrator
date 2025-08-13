"""Tests for broadcast_message business logic tool."""

from unittest.mock import call

import pytest

from tmux_orchestrator.server.tools.broadcast_message import (
    BroadcastMessageRequest,
    broadcast_message,
)


@pytest.fixture
def empty_message_request():
    """Request with empty message."""
    return BroadcastMessageRequest(
        session="test-session",
        message="",
    )


@pytest.fixture
def nonexistent_session_request():
    """Request for nonexistent session."""
    return BroadcastMessageRequest(
        session="nonexistent",
        message="Test broadcast",
    )


@pytest.fixture
def all_agents_request():
    """Request to broadcast to all agents."""
    return BroadcastMessageRequest(
        session="test-session",
        message="Team update: New feature ready",
    )


@pytest.fixture
def filtered_agents_request():
    """Request filtered by agent type."""
    return BroadcastMessageRequest(
        session="test-session",
        message="Developers only message",
        agent_types=["developer"],
    )


@pytest.fixture
def excluded_targets_request():
    """Request with excluded targets."""
    return BroadcastMessageRequest(
        session="test-session",
        message="Message for most agents",
        exclude_targets=["test-session:0"],  # Exclude PM
    )


@pytest.fixture
def urgent_message_request():
    """Request with urgent flag."""
    return BroadcastMessageRequest(
        session="test-session",
        message="🚨 URGENT: System down!",
        urgent=True,
    )


@pytest.fixture
def status_update_request():
    """Request for status update."""
    return BroadcastMessageRequest(
        session="test-session",
        message="Status update",
    )


@pytest.fixture
def hello_team_request():
    """Request for hello team message."""
    return BroadcastMessageRequest(
        session="test-session",
        message="Hello team",
    )


@pytest.fixture
def test_message_request() -> None:
    """Request for test message."""
    return BroadcastMessageRequest(
        session="test-session",
        message="Test message",
    )


@pytest.fixture
def dev_qa_request():
    """Request for dev and QA announcement."""
    return BroadcastMessageRequest(
        session="test-session",
        message="Dev and QA announcement",
        agent_types=["developer", "qa"],
    )


@pytest.fixture
def cross_session_pm_request():
    """Request for cross-session PM broadcast."""
    return BroadcastMessageRequest(
        message="All PMs meeting in 5 minutes",
        role="pm",
    )


@pytest.fixture
def urgent_production_request():
    """Request for urgent production message."""
    return BroadcastMessageRequest(
        session="test-session",
        message="Production is down",
        urgent=True,
    )


@pytest.fixture
def standard_windows():
    """Standard set of windows for testing."""
    return [
        {"id": "0", "name": "Claude-pm"},
        {"id": "1", "name": "Claude-developer"},
        {"id": "2", "name": "Claude-qa"},
    ]


@pytest.fixture
def extended_windows():
    """Extended set of windows for testing."""
    return [
        {"id": "0", "name": "Claude-pm"},
        {"id": "1", "name": "Claude-developer"},
        {"id": "2", "name": "Claude-qa"},
        {"id": "3", "name": "Claude-backend-dev"},
    ]


@pytest.fixture
def non_claude_windows():
    """Non-Claude windows for testing."""
    return [
        {"id": "0", "name": "bash"},
        {"id": "1", "name": "vim"},
    ]


def test_broadcast_message_empty_message(mock_tmux, empty_message_request) -> None:
    """Test broadcast with empty message."""
    # Act
    result = broadcast_message(mock_tmux, empty_message_request)

    # Assert
    assert not result.success
    assert result.error_message == "Message cannot be empty"
    assert result.targets_sent == []
    assert result.targets_failed == []


def test_broadcast_message_session_not_found(mock_tmux, nonexistent_session_request) -> None:
    """Test broadcast when session doesn't exist."""
    # Arrange
    mock_tmux.has_session.return_value = False

    # Act
    result = broadcast_message(mock_tmux, nonexistent_session_request)

    # Assert
    assert not result.success
    assert result.error_message == "Session 'nonexistent' not found"
    mock_tmux.has_session.assert_called_once_with("nonexistent")


def test_broadcast_message_to_all_agents(mock_tmux, all_agents_request, standard_windows) -> None:
    """Test successful broadcast to all agents in session."""
    # Arrange
    mock_tmux.has_session.return_value = True
    mock_tmux.list_windows.return_value = standard_windows
    mock_tmux.capture_pane.return_value = "│ > Ready for input"  # Claude indicator
    mock_tmux.send_message.return_value = True

    # Act
    result = broadcast_message(mock_tmux, all_agents_request)

    # Assert
    assert result.success
    assert len(result.targets_sent) == 3
    assert "test-session:0" in result.targets_sent
    assert "test-session:1" in result.targets_sent
    assert "test-session:2" in result.targets_sent
    assert result.targets_failed == []

    # Verify messages were sent
    expected_calls = [
        call("test-session:0", "Team update: New feature ready"),
        call("test-session:1", "Team update: New feature ready"),
        call("test-session:2", "Team update: New feature ready"),
    ]
    mock_tmux.send_message.assert_has_calls(expected_calls, any_order=True)


def test_broadcast_message_with_agent_type_filter(mock_tmux, filtered_agents_request, extended_windows) -> None:
    """Test broadcast filtered by agent type."""
    # Arrange
    mock_tmux.has_session.return_value = True
    mock_tmux.list_windows.return_value = extended_windows
    mock_tmux.capture_pane.return_value = "│ > Ready"
    mock_tmux.send_message.return_value = True

    # Act
    result = broadcast_message(mock_tmux, filtered_agents_request)

    # Assert
    assert result.success
    assert len(result.targets_sent) == 2
    assert "test-session:1" in result.targets_sent
    assert "test-session:3" in result.targets_sent
    assert result.targets_failed == []


def test_broadcast_message_with_exclusions(mock_tmux, excluded_targets_request, standard_windows) -> None:
    """Test broadcast with excluded targets."""
    # Arrange
    mock_tmux.has_session.return_value = True
    mock_tmux.list_windows.return_value = standard_windows
    mock_tmux.capture_pane.return_value = "Human: "
    mock_tmux.send_message.return_value = True

    # Act
    result = broadcast_message(mock_tmux, excluded_targets_request)

    # Assert
    assert result.success
    assert len(result.targets_sent) == 2
    assert "test-session:0" not in result.targets_sent
    assert "test-session:1" in result.targets_sent
    assert "test-session:2" in result.targets_sent


def test_broadcast_message_urgent_flag(mock_tmux, urgent_message_request) -> None:
    """Test broadcast with urgent flag."""
    # Arrange
    mock_tmux.has_session.return_value = True
    mock_tmux.list_windows.return_value = [
        {"id": "0", "name": "Claude-pm"},
        {"id": "1", "name": "Claude-developer"},
    ]
    mock_tmux.capture_pane.return_value = "assistant: I'm working on"
    mock_tmux.send_message.return_value = True

    # Act
    result = broadcast_message(mock_tmux, urgent_message_request)

    # Assert
    assert result.success
    assert len(result.targets_sent) == 2
    # Verify urgent messages are sent (implementation could add special handling)


def test_broadcast_message_partial_failure(mock_tmux, status_update_request, standard_windows) -> None:
    """Test broadcast with some failures."""
    # Arrange
    mock_tmux.has_session.return_value = True
    mock_tmux.list_windows.return_value = standard_windows
    mock_tmux.capture_pane.return_value = "Claude:"
    # First two succeed, third fails
    mock_tmux.send_message.side_effect = [True, True, False]

    # Act
    result = broadcast_message(mock_tmux, status_update_request)

    # Assert
    assert result.success  # Partial success
    assert len(result.targets_sent) == 2
    assert len(result.targets_failed) == 1
    assert "test-session:2" in result.targets_failed


def test_broadcast_message_no_claude_windows(mock_tmux, hello_team_request, non_claude_windows) -> None:
    """Test broadcast when no Claude agents found."""
    # Arrange
    mock_tmux.has_session.return_value = True
    mock_tmux.list_windows.return_value = non_claude_windows
    # No Claude indicators in panes
    mock_tmux.capture_pane.return_value = "user@host:~$ "

    # Act
    result = broadcast_message(mock_tmux, hello_team_request)

    # Assert
    assert not result.success
    assert result.error_message == "No agents found to broadcast to"
    assert result.targets_sent == []


def test_broadcast_message_exception_handling(mock_tmux, test_message_request) -> None:
    """Test broadcast handles exceptions gracefully."""
    # Arrange
    mock_tmux.has_session.return_value = True
    mock_tmux.list_windows.side_effect = Exception("Tmux error")

    # Act
    result = broadcast_message(mock_tmux, test_message_request)

    # Assert
    assert not result.success
    assert "Unexpected error broadcasting message" in result.error_message


def test_broadcast_message_multiple_agent_types(mock_tmux, dev_qa_request) -> None:
    """Test broadcast to multiple agent types."""
    # Arrange
    mock_tmux.has_session.return_value = True
    mock_tmux.list_windows.return_value = [
        {"id": "0", "name": "Claude-pm"},
        {"id": "1", "name": "Claude-developer"},
        {"id": "2", "name": "Claude-qa"},
        {"id": "3", "name": "Claude-devops"},
    ]
    mock_tmux.capture_pane.return_value = "I'll help"
    mock_tmux.send_message.return_value = True

    # Act
    result = broadcast_message(mock_tmux, dev_qa_request)

    # Assert
    assert result.success
    assert len(result.targets_sent) == 2
    assert "test-session:1" in result.targets_sent  # developer
    assert "test-session:2" in result.targets_sent  # qa
    assert "test-session:0" not in result.targets_sent  # pm excluded
    assert "test-session:3" not in result.targets_sent  # devops excluded


def test_broadcast_message_cross_session_role(mock_tmux, cross_session_pm_request) -> None:
    """Test broadcast to specific role across all sessions."""
    # Arrange
    mock_tmux.list_sessions.return_value = [
        {"name": "project-a"},
        {"name": "project-b"},
        {"name": "project-c"},
    ]
    mock_tmux.has_session.return_value = True
    mock_tmux.list_windows.side_effect = [
        [{"id": "0", "name": "Claude-pm"}, {"id": "1", "name": "Claude-developer"}],
        [{"id": "0", "name": "Claude-pm"}, {"id": "1", "name": "Claude-qa"}],
        [{"id": "0", "name": "Claude-developer"}, {"id": "1", "name": "Claude-pm"}],
    ]
    mock_tmux.capture_pane.return_value = "│ > Ready"
    mock_tmux.send_message.return_value = True

    # Act
    result = broadcast_message(mock_tmux, cross_session_pm_request)

    # Assert
    assert result.success
    assert len(result.targets_sent) == 3  # 3 PMs across 3 projects
    assert "project-a:0" in result.targets_sent
    assert "project-b:0" in result.targets_sent
    assert "project-c:1" in result.targets_sent  # PM is in window 1 here


def test_broadcast_message_urgent_formatting(mock_tmux, urgent_production_request) -> None:
    """Test that urgent messages are formatted correctly."""
    # Arrange
    mock_tmux.has_session.return_value = True
    mock_tmux.list_windows.return_value = [
        {"id": "0", "name": "Claude-developer"},
    ]
    mock_tmux.capture_pane.return_value = "│ > Ready"
    mock_tmux.send_message.return_value = True

    # Act
    result = broadcast_message(mock_tmux, urgent_production_request)

    # Assert
    assert result.success
    # Verify the message was prefixed with urgent indicator
    mock_tmux.send_message.assert_called_with("test-session:0", "🚨 URGENT: Production is down")
