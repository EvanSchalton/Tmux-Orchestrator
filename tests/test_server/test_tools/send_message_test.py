"""Tests for send_message MCP tool."""

from tmux_orchestrator.server.tools.send_message import (
    SendMessageRequest,
    SendMessageResult,
    send_message,
)


def test_send_message_success(mock_tmux) -> None:
    """Test successful message sending."""
    request = SendMessageRequest(target="myproject:Claude-PM", message="Please work on the login feature", urgent=False)

    result = send_message(mock_tmux, request)

    assert isinstance(result, SendMessageResult)
    assert result.success is True
    assert result.target == "myproject:Claude-PM"
    assert result.message_sent == "Please work on the login feature"
    assert result.error_message is None

    # Verify tmux method was called correctly
    mock_tmux.send_message.assert_called_once_with("myproject:Claude-PM", "Please work on the login feature")


def test_send_message_urgent(mock_tmux) -> None:
    """Test sending urgent message."""
    request = SendMessageRequest(
        target="critical:Claude-Developer", message="URGENT: Fix production bug immediately", urgent=True
    )

    result = send_message(mock_tmux, request)

    assert result.success is True
    assert result.target == "critical:Claude-Developer"
    assert "URGENT" in result.message_sent

    # For urgent messages, the message should be sent as-is
    mock_tmux.send_message.assert_called_once_with(
        "critical:Claude-Developer", "URGENT: Fix production bug immediately"
    )


def test_send_message_failure(mock_tmux) -> None:
    """Test message sending failure."""
    request = SendMessageRequest(target="broken:window", message="Test message", urgent=False)

    mock_tmux.send_message.return_value = False

    result = send_message(mock_tmux, request)

    assert result.success is False
    assert result.target == "broken:window"
    assert result.message_sent == "Test message"
    assert "Failed to send message" in result.error_message


def test_send_message_exception(mock_tmux) -> None:
    """Test message sending when tmux raises exception."""
    request = SendMessageRequest(target="test:agent", message="Hello", urgent=False)

    mock_tmux.send_message.side_effect = Exception("Connection lost")

    result = send_message(mock_tmux, request)

    assert result.success is False
    assert result.target == "test:agent"
    assert result.message_sent == "Hello"
    assert "Connection lost" in result.error_message


def test_send_message_empty_target(mock_tmux) -> None:
    """Test sending message with empty target."""
    request = SendMessageRequest(target="", message="Test message", urgent=False)

    result = send_message(mock_tmux, request)

    assert result.success is False
    assert result.target == ""
    assert result.message_sent == "Test message"
    assert "Target must be in format" in result.error_message

    # Should not call tmux methods
    mock_tmux.send_message.assert_not_called()


def test_send_message_empty_message(mock_tmux) -> None:
    """Test sending empty message."""
    request = SendMessageRequest(target="test:agent", message="", urgent=False)

    result = send_message(mock_tmux, request)

    assert result.success is False
    assert result.target == "test:agent"
    assert result.message_sent == ""
    assert "Message cannot be empty" in result.error_message

    # Should not call tmux methods
    mock_tmux.send_message.assert_not_called()


def test_send_message_whitespace_target(mock_tmux) -> None:
    """Test sending message with whitespace-only target."""
    request = SendMessageRequest(target="   \t\n   ", message="Test message", urgent=False)

    result = send_message(mock_tmux, request)

    assert result.success is False
    assert "Target must be in format" in result.error_message


def test_send_message_whitespace_message(mock_tmux) -> None:
    """Test sending whitespace-only message."""
    request = SendMessageRequest(target="test:agent", message="   \t\n   ", urgent=False)

    result = send_message(mock_tmux, request)

    # The actual implementation treats whitespace as empty
    assert result.success is False
    assert result.message_sent == "   \t\n   "
    assert "Message cannot be empty" in result.error_message


def test_send_message_long_message(mock_tmux) -> None:
    """Test sending very long message."""
    long_message = "A" * 10000  # 10k character message
    request = SendMessageRequest(target="test:agent", message=long_message, urgent=False)

    result = send_message(mock_tmux, request)

    assert result.success is True
    assert result.message_sent == long_message
    mock_tmux.send_message.assert_called_once_with("test:agent", long_message)


def test_send_message_special_characters(mock_tmux) -> None:
    """Test sending message with special characters."""
    special_message = 'Message with "quotes", \n newlines, and émojis 🚀'
    request = SendMessageRequest(target="test:agent", message=special_message, urgent=False)

    result = send_message(mock_tmux, request)

    assert result.success is True
    assert result.message_sent == special_message


def test_send_message_multiline(mock_tmux) -> None:
    """Test sending multiline message."""
    multiline_message = """This is a multiline message.
It has multiple lines.
Each line should be preserved."""

    request = SendMessageRequest(target="test:agent", message=multiline_message, urgent=False)

    result = send_message(mock_tmux, request)

    assert result.success is True
    assert result.message_sent == multiline_message
    assert "\n" in result.message_sent


def test_send_message_request_defaults() -> None:
    """Test SendMessageRequest default values."""
    request = SendMessageRequest(target="test:agent", message="Hello")

    assert request.target == "test:agent"
    assert request.message == "Hello"
    assert request.urgent is False  # Default value


def test_send_message_result_dataclass() -> None:
    """Test SendMessageResult dataclass structure."""
    result = SendMessageResult(success=True, target="test:agent", message_sent="Hello world", error_message=None)

    assert result.success is True
    assert result.target == "test:agent"
    assert result.message_sent == "Hello world"
    assert result.error_message is None


def test_send_message_result_with_error() -> None:
    """Test SendMessageResult with error."""
    result = SendMessageResult(success=False, target="broken:target", message_sent="", error_message="Target not found")

    assert result.success is False
    assert result.target == "broken:target"
    assert result.message_sent == ""
    assert result.error_message == "Target not found"


def test_send_message_complex_target_format(mock_tmux) -> None:
    """Test sending message to complex target formats."""
    test_cases = [
        "simple-session:0",
        "complex-session-name:window-name",
        "session_with_underscores:Claude-Developer-123",
        "session:very-long-window-name-with-many-parts",
    ]

    for target in test_cases:
        request = SendMessageRequest(target=target, message="Test", urgent=False)
        result = send_message(mock_tmux, request)

        assert result.success is True
        assert result.target == target
        mock_tmux.send_message.assert_called_with(target, "Test")


def test_send_message_invalid_target_formats(mock_tmux) -> None:
    """Test sending message to invalid target formats."""
    # Only targets without colons fail validation
    no_colon_targets = ["no-colon-separator"]

    for target in no_colon_targets:
        request = SendMessageRequest(target=target, message="Test", urgent=False)
        result = send_message(mock_tmux, request)

        assert result.success is False
        assert result.target == target
        assert "Target must be in format" in result.error_message

    # Targets with colons pass basic validation (but may fail due to session not found)
    mock_tmux.has_session.return_value = False  # Mock session not found

    with_colon_targets = [
        "multiple:colons:here",
        ":empty-session",
        "session:",
    ]

    for target in with_colon_targets:
        request = SendMessageRequest(target=target, message="Test", urgent=False)
        result = send_message(mock_tmux, request)

        assert result.success is False
        assert result.target == target
        assert "not found" in result.error_message
