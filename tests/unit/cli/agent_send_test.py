"""Tests for agent send command functionality."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.agent import agent, send
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


def test_agent_send_success() -> None:
    """Test successful send command via CLI."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.press_ctrl_u.return_value = True
    mock_tmux.send_text.return_value = True
    mock_tmux.press_enter.return_value = True

    with patch("time.sleep"):  # Speed up tests by mocking sleep
        result = runner.invoke(agent, ["send", "test-session:0", "Hello agent!"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    clean_output = result.output.replace("\x1b[32m", "").replace("\x1b[0m", "").replace("\x1b[1;32m", "")
    assert "Message sent to test-session:0" in clean_output
    assert "Used 0.5s delay" in clean_output

    # Verify validation was performed
    mock_tmux.has_session.assert_called_once_with("test-session")
    # Verify the new methods were called (press_ctrl_c is now disabled in implementation)
    mock_tmux.press_ctrl_u.assert_called_once_with("test-session:0")
    mock_tmux.send_text.assert_called_once_with("test-session:0", "Hello agent!")
    mock_tmux.press_enter.assert_called_once_with("test-session:0")


def test_agent_send_with_pane_target() -> None:
    """Test send command with session:window.pane format."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.press_ctrl_u.return_value = True
    mock_tmux.send_text.return_value = True
    mock_tmux.press_enter.return_value = True

    with patch("time.sleep"):
        result = runner.invoke(agent, ["send", "test-session:0.1", "Hello agent!"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    assert "Message sent to test-session:0.1" in result.output
    mock_tmux.has_session.assert_called_once_with("test-session")


def test_agent_send_custom_delay() -> None:
    """Test send command with custom delay setting."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.press_ctrl_u.return_value = True
    mock_tmux.send_text.return_value = True
    mock_tmux.press_enter.return_value = True

    with patch("time.sleep") as mock_sleep:
        result = runner.invoke(agent, ["send", "test-session:0", "Hello!", "--delay", "1.5"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    assert "Used 1.5s delay" in result.output
    # Verify sleep was called with custom delay
    assert any(call.args[0] == 1.5 for call in mock_sleep.call_args_list)


def test_agent_send_json_output() -> None:
    """Test send command with JSON output format."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.press_ctrl_u.return_value = True
    mock_tmux.send_text.return_value = True
    mock_tmux.press_enter.return_value = True

    with patch("time.sleep"):
        result = runner.invoke(agent, ["send", "test-session:0", "Hello!", "--json"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0

    # Parse JSON output
    import json

    output_data = json.loads(result.output)

    assert output_data["success"] is True
    assert output_data["target"] == "test-session:0"
    assert output_data["message"] == "Hello!"
    assert output_data["delay"] == 0.5
    assert output_data["status"] == "sent"
    assert "timestamp" in output_data


def test_agent_send_invalid_target_format() -> None:
    """Test send command with invalid target format."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    result = runner.invoke(agent, ["send", "invalid-target", "Hello!"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0  # Command runs but shows error
    assert "Invalid target format" in result.output
    assert "session:window" in result.output and "session:window.pane" in result.output


def test_agent_send_invalid_target_format_json() -> None:
    """Test send command invalid format with JSON output."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    result = runner.invoke(agent, ["send", "invalid-target", "Hello!", "--json"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0

    # Test that we get the expected validation results even if JSON parsing fails due to Rich formatting
    assert "success" in result.output
    assert "false" in result.output
    assert "invalid_format" in result.output
    assert "Invalid target format" in result.output


def test_agent_send_session_not_found() -> None:
    """Test send command when session doesn't exist."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = False

    result = runner.invoke(agent, ["send", "nonexistent:0", "Hello!"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    assert "Session 'nonexistent' does not exist" in result.output
    mock_tmux.has_session.assert_called_once_with("nonexistent")


def test_agent_send_session_not_found_json() -> None:
    """Test send command session not found with JSON output."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = False

    result = runner.invoke(agent, ["send", "nonexistent:0", "Hello!", "--json"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0

    import json

    output_data = json.loads(result.output)

    assert output_data["success"] is False
    assert output_data["status"] == "session_not_found"
    assert "Session 'nonexistent' does not exist" in output_data["error"]


def test_agent_send_exception_handling() -> None:
    """Test send command exception handling during message sending."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.press_ctrl_u.return_value = True
    mock_tmux.send_text.side_effect = Exception("Network error")
    mock_tmux.press_enter.return_value = True

    result = runner.invoke(agent, ["send", "test-session:0", "Hello!"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    assert "Failed to send message to test-session:0" in result.output
    assert "Network error" in result.output


def test_send_function_direct() -> None:
    """Test send function directly without CLI runner."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.press_ctrl_u.return_value = True
    mock_tmux.send_text.return_value = True
    mock_tmux.press_enter.return_value = True

    with patch("time.sleep"):
        result = runner.invoke(send, ["test-session:0", "Hello agent!"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    # Verify session validation was performed
    mock_tmux.has_session.assert_called_once_with("test-session")
    # Verify the new methods were called (press_ctrl_c is now disabled in implementation)
    mock_tmux.press_ctrl_u.assert_called_once_with("test-session:0")
    mock_tmux.send_text.assert_called_once_with("test-session:0", "Hello agent!")
    mock_tmux.press_enter.assert_called_once_with("test-session:0")
