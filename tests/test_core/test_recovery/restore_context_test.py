"""Tests for restore_context module."""

from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.recovery.restore_context import (
    _build_context_message,
    restore_context,
)


def test_restore_context_success() -> None:
    """Test successful context restoration."""
    # Arrange
    tmux_mock: Mock = Mock()
    tmux_mock.send_message.return_value = True
    target: str = "test-session:0"
    logger_mock: Mock = Mock()

    with patch("time.sleep"):  # Mock sleep to speed up tests
        # Act
        result: bool = restore_context(tmux_mock, target, logger_mock)

        # Assert
        assert result is True
        tmux_mock.send_message.assert_called_once()
        logger_mock.info.assert_called()


def test_restore_context_send_message_failure() -> None:
    """Test context restoration when send_message fails."""
    # Arrange
    tmux_mock: Mock = Mock()
    tmux_mock.send_message.return_value = False
    target: str = "test-session:0"
    logger_mock: Mock = Mock()

    with patch("time.sleep"):
        # Act
        result: bool = restore_context(tmux_mock, target, logger_mock)

        # Assert
        assert result is False
        logger_mock.error.assert_called()


def test_restore_context_invalid_target_format() -> None:
    """Test context restoration with invalid target format."""
    # Arrange
    tmux_mock: Mock = Mock()
    target: str = "invalid-format"
    logger_mock: Mock = Mock()

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid target format"):
        restore_context(tmux_mock, target, logger_mock)


def test_restore_context_with_context_data() -> None:
    """Test context restoration with additional context data."""
    # Arrange
    tmux_mock: Mock = Mock()
    tmux_mock.send_message.return_value = True
    target: str = "test-session:0"
    logger_mock: Mock = Mock()
    context_data: dict = {
        "last_task": "Implementing user authentication",
        "progress": "50% complete",
    }

    with patch("time.sleep"):
        # Act
        result: bool = restore_context(tmux_mock, target, logger_mock, context_data)

        # Assert
        assert result is True
        # Check that the message contains context data
        call_args = tmux_mock.send_message.call_args
        message_content = call_args[0][1]
        assert "last_task: Implementing user authentication" in message_content
        assert "progress: 50% complete" in message_content


def test_restore_context_exception_handling() -> None:
    """Test context restoration exception handling."""
    # Arrange
    tmux_mock: Mock = Mock()
    tmux_mock.send_message.side_effect = RuntimeError("Connection failed")
    target: str = "test-session:0"
    logger_mock: Mock = Mock()

    with patch("time.sleep"):
        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to restore context"):
            restore_context(tmux_mock, target, logger_mock)


def test_build_context_message_basic() -> None:
    """Test building basic context message."""
    # Arrange
    target: str = "test-session:0"

    # Act
    message: str = _build_context_message(target)

    # Assert
    assert "RECOVERY NOTICE" in message
    assert "test-session:0" in message
    assert "automatically restarted" in message
    assert "IMMEDIATE ACTIONS" in message


def test_build_context_message_with_context_data() -> None:
    """Test building context message with additional data."""
    # Arrange
    target: str = "test-session:0"
    context_data: dict = {
        "project": "E-commerce API",
        "current_branch": "feature/payment-integration",
    }

    # Act
    message: str = _build_context_message(target, context_data)

    # Assert
    assert "RECOVERY NOTICE" in message
    assert "ADDITIONAL CONTEXT" in message
    assert "project: E-commerce API" in message
    assert "current_branch: feature/payment-integration" in message


def test_build_context_message_contains_timestamp() -> None:
    """Test that context message contains timestamp."""
    # Arrange
    target: str = "test-session:0"

    with patch("tmux_orchestrator.core.recovery.restore_context.datetime") as dt_mock:
        dt_mock.now.return_value.strftime.return_value = "2024-01-01 12:00:00"

        # Act
        message: str = _build_context_message(target)

        # Assert
        assert "2024-01-01 12:00:00" in message


def test_build_context_message_empty_context_data() -> None:
    """Test building context message with empty context data."""
    # Arrange
    target: str = "test-session:0"
    context_data: dict = {}

    # Act
    message: str = _build_context_message(target, context_data)

    # Assert
    assert "RECOVERY NOTICE" in message
    # Should not contain additional context section for empty dict
    assert "ADDITIONAL CONTEXT" not in message
