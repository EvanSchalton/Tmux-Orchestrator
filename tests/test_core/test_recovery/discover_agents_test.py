"""Tests for discover_agents module."""

from unittest.mock import Mock

import pytest

from tmux_orchestrator.core.recovery.discover_agents import (
    _is_claude_agent,
    discover_agents,
)


@pytest.fixture
def tmux_mock():
    """Create a mock TMUXManager for testing."""
    return Mock()


@pytest.fixture
def logger_mock():
    """Create a mock logger for testing."""
    return Mock()


def test_discover_agents_finds_claude_agents(tmux_mock, logger_mock) -> None:
    """Test agent discovery finds Claude agents."""
    # Arrange
    tmux_mock.list_sessions.return_value = [
        {"name": "ai-chat"},
        {"name": "development"},
    ]
    tmux_mock.list_windows.side_effect = [
        [{"index": "0"}, {"index": "1"}],  # ai-chat windows
        [{"index": "0"}],  # development windows
    ]
    tmux_mock.capture_pane.side_effect = [
        "│ > I'll help you with that task",  # Claude agent
        "bash-5.0$ ls",  # Not Claude
        "assistant: Let me analyze this",  # Claude agent
    ]

    # Act
    discovered = discover_agents(tmux_mock, logger_mock)

    # Assert
    assert "ai-chat:0" in discovered
    assert "development:0" in discovered
    assert "ai-chat:1" not in discovered  # Not Claude
    assert len(discovered) == 2


def test_discover_agents_excludes_sessions(tmux_mock, logger_mock) -> None:
    """Test agent discovery excludes specified sessions."""
    # Arrange
    exclude_sessions = {"orchestrator", "monitoring"}
    tmux_mock.list_sessions.return_value = [
        {"name": "orchestrator"},
        {"name": "ai-chat"},
        {"name": "monitoring-session"},
    ]
    tmux_mock.list_windows.return_value = [{"index": "0"}]
    tmux_mock.capture_pane.return_value = "│ > Claude interface"

    # Act
    discovered = discover_agents(tmux_mock, logger_mock, exclude_sessions)

    # Assert
    # Only ai-chat should be processed (orchestrator excluded, monitoring-session contains 'monitoring')
    assert len(discovered) <= 1
    logger_mock.debug.assert_called()  # Should log skipped sessions


def test_discover_agents_empty_sessions(tmux_mock, logger_mock) -> None:
    """Test agent discovery with no sessions."""
    # Arrange
    tmux_mock.list_sessions.return_value = []

    # Act
    discovered = discover_agents(tmux_mock, logger_mock)

    # Assert
    assert len(discovered) == 0


def test_discover_agents_exception_handling(tmux_mock, logger_mock) -> None:
    """Test agent discovery exception handling."""
    # Arrange
    tmux_mock.list_sessions.side_effect = RuntimeError("Connection failed")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Agent discovery failed"):
        discover_agents(tmux_mock, logger_mock)


def test_discover_agents_default_excludes(tmux_mock, logger_mock) -> None:
    """Test agent discovery uses default excludes when none provided."""
    # Arrange
    tmux_mock.list_sessions.return_value = [
        {"name": "orchestrator"},
        {"name": "tmux-orc"},
        {"name": "recovery"},
        {"name": "ai-chat"},
    ]
    tmux_mock.list_windows.return_value = [{"index": "0"}]
    tmux_mock.capture_pane.return_value = "│ > Claude interface"

    # Act
    _discovered = discover_agents(tmux_mock, logger_mock)

    # Assert
    # Only ai-chat should be discovered (others are in default excludes)
    tmux_mock.list_windows.assert_called_once_with("ai-chat")


def test_is_claude_agent_with_strong_indicators(tmux_mock, logger_mock) -> None:
    """Test Claude agent detection with strong indicators."""
    # Arrange
    target = "test:0"
    strong_contents = [
        "│ > waiting for input",
        "assistant: I'll help you",
        "claude: Ready to assist",
        "anthropic Claude model",
        "i'll help you with that task",
        "let me analyze this code",
        "human: What should I do?",
    ]

    for content in strong_contents:
        tmux_mock.capture_pane.return_value = content

        # Act
        result = _is_claude_agent(tmux_mock, target, logger_mock)

        # Assert
        assert result is True, f"Failed to detect Claude with content: {content}"


def test_is_claude_agent_with_medium_indicators(tmux_mock, logger_mock) -> None:
    """Test Claude agent detection with multiple medium indicators."""
    # Arrange
    target = "test:0"
    tmux_mock.capture_pane.return_value = (
        "I can certainly help you analyze and implement this solution. "
        "Would you like me to understand the requirements first?"
    )

    # Act
    result = _is_claude_agent(tmux_mock, target, logger_mock)

    # Assert
    assert result is True


def test_is_claude_agent_with_claude_name_and_medium(tmux_mock, logger_mock) -> None:
    """Test Claude agent detection with Claude name and medium indicator."""
    # Arrange
    target = "test:0"
    tmux_mock.capture_pane.return_value = "claude analyze this code please"

    # Act
    result = _is_claude_agent(tmux_mock, target, logger_mock)

    # Assert
    assert result is True


def test_is_claude_agent_with_insufficient_indicators(tmux_mock, logger_mock) -> None:
    """Test Claude agent detection with insufficient indicators."""
    # Arrange
    target = "test:0"
    non_claude_contents = [
        "bash-5.0$ ls -la",
        "npm run dev",
        "just some random text",
        "i can help",  # Only one medium indicator
        "analyze code",  # Only one medium indicator
    ]

    for content in non_claude_contents:
        tmux_mock.capture_pane.return_value = content

        # Act
        result = _is_claude_agent(tmux_mock, target, logger_mock)

        # Assert
        assert result is False, f"Incorrectly detected Claude with content: {content}"


def test_is_claude_agent_empty_content(tmux_mock, logger_mock) -> None:
    """Test Claude agent detection with empty content."""
    # Arrange
    target = "test:0"
    tmux_mock.capture_pane.return_value = ""

    # Act
    result = _is_claude_agent(tmux_mock, target, logger_mock)

    # Assert
    assert result is False


def test_is_claude_agent_exception_handling(tmux_mock, logger_mock) -> None:
    """Test Claude agent detection exception handling."""
    # Arrange
    target = "test:0"
    tmux_mock.capture_pane.side_effect = RuntimeError("Connection failed")

    # Act
    result = _is_claude_agent(tmux_mock, target, logger_mock)

    # Assert
    assert result is False
    logger_mock.debug.assert_called()  # Should log the error
