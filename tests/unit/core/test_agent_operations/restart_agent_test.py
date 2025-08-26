"""Tests for restart_agent business logic function."""

from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.agent_operations.restart_agent import restart_agent
from tmux_orchestrator.utils.tmux import TMUXManager


def test_restart_agent_success() -> None:
    """Test successful agent restart."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.send_keys.return_value = True
    mock_tmux.list_windows.return_value = [{"index": "0", "name": "test-window"}]
    mock_tmux.capture_pane.return_value = "Claude ready"
    mock_tmux.send_message.return_value = True

    target: str = "test-session:0"

    # Act
    with patch("time.sleep"):  # Mock time.sleep to speed up test
        success, message, details = restart_agent(mock_tmux, target)

    # Assert
    assert success is True
    assert "Agent at test-session:0 restarted successfully" in message

    # Verify tmux interactions
    mock_tmux.has_session.assert_called_once_with("test-session")

    # Verify the correct sequence of send_keys calls
    expected_calls = [
        ("test-session:0", "C-c"),
        ("test-session:0", "C-u"),
        ("test-session:0", "claude --dangerously-skip-permissions"),
        ("test-session:0", "Enter"),
    ]

    actual_calls = [call.args for call in mock_tmux.send_keys.call_args_list]
    assert actual_calls == expected_calls


def test_restart_agent_invalid_target_format() -> None:
    """Test restart with invalid target format."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.list_windows.return_value = [{"index": "0", "name": "test-window"}]
    mock_tmux.capture_pane.return_value = "Claude ready"
    target: str = "invalid-target-format"

    # Act
    success, message, details = restart_agent(mock_tmux, target)

    # Assert
    assert success is False
    assert "Invalid target format 'invalid-target-format'. Use session:window" == message

    # Verify no tmux interactions
    mock_tmux.has_session.assert_not_called()
    mock_tmux.send_keys.assert_not_called()


def test_restart_agent_session_not_found() -> None:
    """Test restart when session doesn't exist."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = False
    mock_tmux.list_windows.return_value = [{"index": "0", "name": "test-window"}]
    mock_tmux.capture_pane.return_value = "Claude ready"

    target: str = "nonexistent-session:0"

    # Act
    success, message, details = restart_agent(mock_tmux, target)

    # Assert
    assert success is False
    assert "Session 'nonexistent-session' not found" == message

    # Verify session check was called but no send_keys
    mock_tmux.has_session.assert_called_once_with("nonexistent-session")
    mock_tmux.send_keys.assert_not_called()


@pytest.mark.parametrize(
    "target,expected_session,expected_window",
    [
        ("frontend:0", "frontend", "0"),
        ("backend-dev:1", "backend-dev", "1"),
        ("project-manager:10", "project-manager", "10"),
    ],
)
def test_restart_agent_target_parsing(target: str, expected_session: str, expected_window: str) -> None:
    """Test various target format parsing scenarios."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.send_keys.return_value = True
    mock_tmux.list_windows.return_value = [{"index": expected_window, "name": "test-window"}]
    mock_tmux.capture_pane.return_value = "Claude ready"
    mock_tmux.send_message.return_value = True

    # Act
    with patch("time.sleep"):
        success, message, details = restart_agent(mock_tmux, target)

    # Assert
    assert success is True
    mock_tmux.has_session.assert_called_once_with(expected_session)

    # Verify send_keys calls include correct target
    send_keys_calls = mock_tmux.send_keys.call_args_list
    assert all(call.args[0] == target for call in send_keys_calls)


def test_restart_agent_empty_target() -> None:
    """Test restart with empty target."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.list_windows.return_value = [{"index": "0", "name": "test-window"}]
    mock_tmux.capture_pane.return_value = "Claude ready"
    target: str = ""

    # Act
    success, message, details = restart_agent(mock_tmux, target)

    # Assert
    assert success is False
    assert "Invalid target format ''. Use session:window" == message


def test_restart_agent_colon_only_target() -> None:
    """Test restart with target containing only colon."""
    # Arrange
    mock_tmux: Mock = Mock(spec=TMUXManager)
    mock_tmux.list_windows.return_value = [{"index": "0", "name": "test-window"}]
    mock_tmux.capture_pane.return_value = "Claude ready"
    target: str = ":"

    # Act
    success, message, details = restart_agent(mock_tmux, target)

    # Assert
    assert success is False
    # Should not call has_session because format is invalid
    mock_tmux.has_session.assert_not_called()
    assert "Invalid target format ':'. Use session:window" == message
