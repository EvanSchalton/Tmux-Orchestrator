"""Tests for get_messages business logic tool."""

from datetime import datetime

from tmux_orchestrator.server.tools.get_messages import GetMessagesRequest, get_messages


def test_get_messages_invalid_target(mock_tmux) -> None:
    """Test get_messages with invalid target format."""
    request = GetMessagesRequest(target="invalid-target", lines=50)
    result = get_messages(mock_tmux, request)
    assert not result.success
    assert result.error_message == "Target must be in format 'session:window' or 'session:window.pane'"
    assert result.messages == []
    assert result.total_lines_captured == 0


def test_get_messages_session_not_found(mock_tmux) -> None:
    """Test get_messages when session doesn't exist."""
    request = GetMessagesRequest(target="nonexistent:0", lines=50)
    mock_tmux.has_session.return_value = False
    result = get_messages(mock_tmux, request)
    assert not result.success
    assert result.error_message == "Session 'nonexistent' not found"
    mock_tmux.has_session.assert_called_once_with("nonexistent")


def test_get_messages_empty_pane(mock_tmux) -> None:
    """Test get_messages from empty pane."""
    request = GetMessagesRequest(target="test-session:0", lines=50)
    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = ""
    result = get_messages(mock_tmux, request)
    assert result.success
    assert result.messages == []
    assert result.total_lines_captured == 0
    assert result.error_message == "No content found in target pane"


def test_get_messages_human_assistant_conversation(mock_tmux) -> None:
    """Test parsing a typical Human/Assistant conversation."""
    request = GetMessagesRequest(target="test-session:0", lines=50)
    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = "Human: Can you help me with Python?\n\nAssistant: I'd be happy to help you with Python\\! What specific aspect of Python would you like assistance with?\n\nHuman: How do I read a file?\n\nAssistant: Here's how to read a file in Python:\n\n```python\n# Method 1: Read entire file\nwith open('filename.txt', 'r') as file:\n    content = file.read()\n    print(content)\n```\n\nThis is the most common and safe way to read files."
    result = get_messages(mock_tmux, request)
    assert result.success
    assert len(result.messages) == 4
    assert result.messages[0].role == "human"
    assert "help me with Python" in result.messages[0].content
    assert result.messages[1].role == "assistant"
    assert "happy to help" in result.messages[1].content
    assert result.messages[2].role == "human"
    assert "How do I read a file" in result.messages[2].content
    assert result.messages[3].role == "assistant"
    assert "open('filename.txt'" in result.messages[3].content


def test_get_messages_claude_ui_format(mock_tmux) -> None:
    """Test parsing messages from Claude UI format."""
    request = GetMessagesRequest(target="test-session:0", lines=50)
    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = "╭─ Claude Code ─────────────────────────────────────────────────────────────╮\n│                                                                              │\n│ > What is 2 + 2?                                                            │\n│                                                                              │\n╰──────────────────────────────────────────────────────────────────────────────╯\n\nThe answer to 2 + 2 is 4.\n\n╭─ Claude Code ─────────────────────────────────────────────────────────────╮\n│                                                                              │\n│ > Thanks\\!                                                                    │\n│                                                                              │\n╰──────────────────────────────────────────────────────────────────────────────╯\n\nYou're welcome\\!"
    result = get_messages(mock_tmux, request)
    assert result.success
    assert len(result.messages) >= 2
    # Check we can find the human messages
    human_messages = [m for m in result.messages if m.role == "human"]
    assert any("2 + 2" in m.content for m in human_messages)
    assert any("Thanks" in m.content for m in human_messages)


def test_get_messages_with_filter(mock_tmux) -> None:
    """Test filtering messages by pattern."""
    request = GetMessagesRequest(target="test-session:0", lines=50, filter_pattern="error|bug")
    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = "Human: I found a bug in the code\n\nAssistant: I'll help you fix that bug. What error are you seeing?\n\nHuman: The function returns None\n\nAssistant: Let me check the function for issues.\n\nSystem: 🚨 Error detected in line 42"
    result = get_messages(mock_tmux, request)
    assert result.success
    # Only lines containing "error" or "bug" should be included
    assert len(result.messages) > 0
    for message in result.messages:
        assert "error" in message.content.lower() or "bug" in message.content.lower()


def test_get_messages_system_messages(mock_tmux) -> None:
    """Test parsing system messages."""
    request = GetMessagesRequest(target="test-session:0", lines=50)
    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = "System: 🚀 Agent started successfully\n\nHuman: Status?\n\nAssistant: I'm ready to help\\!\n\n⚠️ Warning: Low memory\n\nSystem: Connection established"
    result = get_messages(mock_tmux, request)
    assert result.success
    system_messages = [m for m in result.messages if m.role == "system"]
    assert len(system_messages) >= 2
    assert any("Agent started" in m.content for m in system_messages)
    assert any("Warning" in m.content for m in system_messages)


def test_get_messages_exception_handling(mock_tmux) -> None:
    """Test handling of exceptions."""
    request = GetMessagesRequest(target="test-session:0", lines=50)
    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.side_effect = Exception("Tmux error")
    result = get_messages(mock_tmux, request)
    assert not result.success
    assert result.error_message and "Unexpected error retrieving messages" in result.error_message


def test_get_messages_limited_lines(mock_tmux) -> None:
    """Test retrieving limited number of lines."""
    request = GetMessagesRequest(target="test-session:0", lines=10)
    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = "Short conversation\nHuman: Hi\nAssistant: Hello\\!"
    result = get_messages(mock_tmux, request)
    assert result.success
    assert result.total_lines_captured == 3
    mock_tmux.capture_pane.assert_called_with("test-session:0", lines=10)


def test_get_messages_with_timestamps(mock_tmux) -> None:
    """Test parsing messages with timestamps."""
    request = GetMessagesRequest(target="test-session:0", lines=50, include_timestamps=True)
    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = "[2024-01-15 14:30:00]\nHuman: What time is it?\n\n[14:30:15]\nAssistant: Based on the timestamp above, it's 2:30 PM.\n\n[14:31] System: 🚀 Task completed"
    result = get_messages(mock_tmux, request)
    assert result.success
    assert len(result.messages) == 3
    # Check that timestamps were extracted
    assert result.messages[0].role == "human"
    assert result.messages[0].timestamp is not None
    assert result.messages[0].timestamp.hour == 14
    assert result.messages[0].timestamp.minute == 30
    assert result.messages[1].role == "assistant"
    assert result.messages[1].timestamp is not None
    assert result.messages[2].role == "system"
    assert result.messages[2].timestamp is not None


def test_get_messages_role_filter(mock_tmux) -> None:
    """Test filtering messages by role."""
    request = GetMessagesRequest(target="test-session:0", lines=50, role_filter="human")
    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = "Human: First question\nAssistant: First answer\nHuman: Second question\nAssistant: Second answer\nSystem: Status update"
    result = get_messages(mock_tmux, request)
    assert result.success
    assert len(result.messages) == 2
    assert all(msg.role == "human" for msg in result.messages)
    assert "First question" in result.messages[0].content
    assert "Second question" in result.messages[1].content


def test_get_messages_since_timestamp(mock_tmux) -> None:
    """Test filtering messages since a specific timestamp."""
    since_time = datetime(2024, 1, 15, 14, 30, 0)
    request = GetMessagesRequest(target="test-session:0", lines=50, include_timestamps=True, since_timestamp=since_time)
    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = "[2024-01-15 14:29:00]\nHuman: Too early\n\n[2024-01-15 14:30:00]\nHuman: Right on time\n\n[2024-01-15 14:31:00]\nAssistant: After the cutoff"
    result = get_messages(mock_tmux, request)
    assert result.success
    assert len(result.messages) == 2  # Only messages at or after 14:30:00
    assert "Too early" not in " ".join(msg.content for msg in result.messages)
    assert "Right on time" in result.messages[0].content
    assert "After the cutoff" in result.messages[1].content
