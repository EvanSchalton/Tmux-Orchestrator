"""Tests for broadcast_message business logic tool."""

from unittest.mock import MagicMock, call

import pytest

from tmux_orchestrator.server.tools.broadcast_message import (
    BroadcastMessageRequest,
    broadcast_message,
)


@pytest.fixture
def mock_tmux():
    """Create a mock TMUXManager for testing."""
    return MagicMock()


class TestBroadcastMessage:
    """Test broadcast_message function."""

    def test_broadcast_message_empty_message(self, mock_tmux):
        """Test broadcast with empty message."""
        # Arrange
        request = BroadcastMessageRequest(
            session="test-session",
            message="",
        )

        # Act
        result = broadcast_message(mock_tmux, request)

        # Assert
        assert not result.success
        assert result.error_message == "Message cannot be empty"
        assert result.targets_sent == []
        assert result.targets_failed == []

    def test_broadcast_message_session_not_found(self, mock_tmux):
        """Test broadcast when session doesn't exist."""
        # Arrange
        request = BroadcastMessageRequest(
            session="nonexistent",
            message="Test broadcast",
        )
        mock_tmux.has_session.return_value = False

        # Act
        result = broadcast_message(mock_tmux, request)

        # Assert
        assert not result.success
        assert result.error_message == "Session 'nonexistent' not found"
        mock_tmux.has_session.assert_called_once_with("nonexistent")

    def test_broadcast_message_to_all_agents(self, mock_tmux):
        """Test successful broadcast to all agents in session."""
        # Arrange
        request = BroadcastMessageRequest(
            session="test-session",
            message="Team update: New feature ready",
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.list_windows.return_value = [
            {"id": "0", "name": "Claude-pm"},
            {"id": "1", "name": "Claude-developer"},
            {"id": "2", "name": "Claude-qa"},
        ]
        mock_tmux.capture_pane.return_value = "│ > Ready for input"  # Claude indicator
        mock_tmux.send_message.return_value = True

        # Act
        result = broadcast_message(mock_tmux, request)

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

    def test_broadcast_message_with_agent_type_filter(self, mock_tmux):
        """Test broadcast filtered by agent type."""
        # Arrange
        request = BroadcastMessageRequest(
            session="test-session",
            message="Developers only message",
            agent_types=["developer"],
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.list_windows.return_value = [
            {"id": "0", "name": "Claude-pm"},
            {"id": "1", "name": "Claude-developer"},
            {"id": "2", "name": "Claude-qa"},
            {"id": "3", "name": "Claude-backend-dev"},
        ]
        mock_tmux.capture_pane.return_value = "│ > Ready"
        mock_tmux.send_message.return_value = True

        # Act
        result = broadcast_message(mock_tmux, request)

        # Assert
        assert result.success
        assert len(result.targets_sent) == 2
        assert "test-session:1" in result.targets_sent
        assert "test-session:3" in result.targets_sent
        assert result.targets_failed == []

    def test_broadcast_message_with_exclusions(self, mock_tmux):
        """Test broadcast with excluded targets."""
        # Arrange
        request = BroadcastMessageRequest(
            session="test-session",
            message="Message for most agents",
            exclude_targets=["test-session:0"],  # Exclude PM
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.list_windows.return_value = [
            {"id": "0", "name": "Claude-pm"},
            {"id": "1", "name": "Claude-developer"},
            {"id": "2", "name": "Claude-qa"},
        ]
        mock_tmux.capture_pane.return_value = "Human: "
        mock_tmux.send_message.return_value = True

        # Act
        result = broadcast_message(mock_tmux, request)

        # Assert
        assert result.success
        assert len(result.targets_sent) == 2
        assert "test-session:0" not in result.targets_sent
        assert "test-session:1" in result.targets_sent
        assert "test-session:2" in result.targets_sent

    def test_broadcast_message_urgent_flag(self, mock_tmux):
        """Test broadcast with urgent flag."""
        # Arrange
        request = BroadcastMessageRequest(
            session="test-session",
            message="🚨 URGENT: System down!",
            urgent=True,
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.list_windows.return_value = [
            {"id": "0", "name": "Claude-pm"},
            {"id": "1", "name": "Claude-developer"},
        ]
        mock_tmux.capture_pane.return_value = "assistant: I'm working on"
        mock_tmux.send_message.return_value = True

        # Act
        result = broadcast_message(mock_tmux, request)

        # Assert
        assert result.success
        assert len(result.targets_sent) == 2
        # Verify urgent messages are sent (implementation could add special handling)

    def test_broadcast_message_partial_failure(self, mock_tmux):
        """Test broadcast with some failures."""
        # Arrange
        request = BroadcastMessageRequest(
            session="test-session",
            message="Status update",
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.list_windows.return_value = [
            {"id": "0", "name": "Claude-pm"},
            {"id": "1", "name": "Claude-developer"},
            {"id": "2", "name": "Claude-qa"},
        ]
        mock_tmux.capture_pane.return_value = "Claude:"
        # First two succeed, third fails
        mock_tmux.send_message.side_effect = [True, True, False]

        # Act
        result = broadcast_message(mock_tmux, request)

        # Assert
        assert result.success  # Partial success
        assert len(result.targets_sent) == 2
        assert len(result.targets_failed) == 1
        assert "test-session:2" in result.targets_failed

    def test_broadcast_message_no_claude_windows(self, mock_tmux):
        """Test broadcast when no Claude agents found."""
        # Arrange
        request = BroadcastMessageRequest(
            session="test-session",
            message="Hello team",
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.list_windows.return_value = [
            {"id": "0", "name": "bash"},
            {"id": "1", "name": "vim"},
        ]
        # No Claude indicators in panes
        mock_tmux.capture_pane.return_value = "user@host:~$ "

        # Act
        result = broadcast_message(mock_tmux, request)

        # Assert
        assert not result.success
        assert result.error_message == "No agents found to broadcast to"
        assert result.targets_sent == []

    def test_broadcast_message_exception_handling(self, mock_tmux):
        """Test broadcast handles exceptions gracefully."""
        # Arrange
        request = BroadcastMessageRequest(
            session="test-session",
            message="Test message",
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.list_windows.side_effect = Exception("Tmux error")

        # Act
        result = broadcast_message(mock_tmux, request)

        # Assert
        assert not result.success
        assert "Unexpected error broadcasting message" in result.error_message

    def test_broadcast_message_multiple_agent_types(self, mock_tmux):
        """Test broadcast to multiple agent types."""
        # Arrange
        request = BroadcastMessageRequest(
            session="test-session",
            message="Dev and QA announcement",
            agent_types=["developer", "qa"],
        )
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
        result = broadcast_message(mock_tmux, request)

        # Assert
        assert result.success
        assert len(result.targets_sent) == 2
        assert "test-session:1" in result.targets_sent  # developer
        assert "test-session:2" in result.targets_sent  # qa
        assert "test-session:0" not in result.targets_sent  # pm excluded
        assert "test-session:3" not in result.targets_sent  # devops excluded

    def test_broadcast_message_cross_session_role(self, mock_tmux):
        """Test broadcast to specific role across all sessions."""
        # Arrange
        request = BroadcastMessageRequest(
            message="All PMs meeting in 5 minutes",
            role="pm",
        )
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
        result = broadcast_message(mock_tmux, request)

        # Assert
        assert result.success
        assert len(result.targets_sent) == 3  # 3 PMs across 3 projects
        assert "project-a:0" in result.targets_sent
        assert "project-b:0" in result.targets_sent
        assert "project-c:1" in result.targets_sent  # PM is in window 1 here

    def test_broadcast_message_urgent_formatting(self, mock_tmux):
        """Test that urgent messages are formatted correctly."""
        # Arrange
        request = BroadcastMessageRequest(
            session="test-session",
            message="Production is down",
            urgent=True,
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.list_windows.return_value = [
            {"id": "0", "name": "Claude-developer"},
        ]
        mock_tmux.capture_pane.return_value = "│ > Ready"
        mock_tmux.send_message.return_value = True

        # Act
        result = broadcast_message(mock_tmux, request)

        # Assert
        assert result.success
        # Verify the message was prefixed with urgent indicator
        mock_tmux.send_message.assert_called_with("test-session:0", "🚨 URGENT: Production is down")
