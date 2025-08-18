#!/usr/bin/env python3
"""Comprehensive tests for claude_interface.py module."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, call, mock_open, patch

import pytest

from tmux_orchestrator.utils.claude_interface import (
    BRIEFINGS_DIR,
    PROJECT_DIR,
    ClaudeAgentManager,
    ClaudeInterface,
)


class TestClaudeInterface:
    """Test ClaudeInterface class methods."""

    def test_send_message_to_claude_success(self):
        """Test successful message sending to Claude."""
        with (
            patch.object(ClaudeInterface, "_get_pane_content") as mock_get_content,
            patch.object(ClaudeInterface, "_is_claude_ready", return_value=True) as mock_ready,
            patch.object(ClaudeInterface, "_clear_input") as mock_clear,
            patch.object(ClaudeInterface, "_method_standard_submit", return_value=True) as mock_submit,
            patch.object(ClaudeInterface, "_message_was_submitted", return_value=True) as mock_submitted,
            patch("time.sleep"),
        ):
            mock_get_content.side_effect = ["old content", "new content"]

            success, error = ClaudeInterface.send_message_to_claude("session:0", "test message")

            assert success is True
            assert error == ""
            mock_ready.assert_called_once_with("old content")
            mock_clear.assert_called_once_with("session:0")
            mock_submit.assert_called_once_with("session:0", "test message")
            mock_submitted.assert_called_once_with("old content", "new content", "test message")

    def test_send_message_claude_not_ready(self):
        """Test sending message when Claude interface is not ready."""
        with (
            patch.object(ClaudeInterface, "_get_pane_content", return_value="bash prompt"),
            patch.object(ClaudeInterface, "_is_claude_ready", return_value=False) as mock_ready,
        ):
            success, error = ClaudeInterface.send_message_to_claude("session:0", "test message")

            assert success is False
            assert error == "Claude interface not ready or not found"
            mock_ready.assert_called_once_with("bash prompt")

    def test_send_message_all_methods_fail(self):
        """Test when all submission methods fail."""
        with (
            patch.object(ClaudeInterface, "_get_pane_content") as mock_get_content,
            patch.object(ClaudeInterface, "_is_claude_ready", return_value=True),
            patch.object(ClaudeInterface, "_clear_input"),
            patch.object(ClaudeInterface, "_method_standard_submit", return_value=False),
            patch.object(ClaudeInterface, "_method_paste_and_submit", return_value=False),
            patch.object(ClaudeInterface, "_method_literal_keys", return_value=False),
            patch.object(ClaudeInterface, "_method_multiple_enters", return_value=False),
            patch.object(ClaudeInterface, "_method_escape_sequence", return_value=False),
            patch("time.sleep"),
        ):
            mock_get_content.return_value = "claude content"

            success, error = ClaudeInterface.send_message_to_claude("session:0", "test message")

            assert success is False
            assert error == "All submission methods failed"

    def test_send_message_exception_handling(self):
        """Test exception handling in send_message_to_claude."""
        with patch.object(ClaudeInterface, "_get_pane_content", side_effect=Exception("test error")):
            success, error = ClaudeInterface.send_message_to_claude("session:0", "test message")

            assert success is False
            assert error == "test error"

    def test_get_pane_content_success(self):
        """Test successful pane content retrieval."""
        mock_result = Mock()
        mock_result.stdout = "Claude interface content"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            content = ClaudeInterface._get_pane_content("session:0")

            assert content == "Claude interface content"
            mock_run.assert_called_once_with(
                ["tmux", "capture-pane", "-t", "session:0", "-p", "-S", "-100"],
                capture_output=True,
                text=True,
                check=True,
            )

    def test_get_pane_content_exception(self):
        """Test _get_pane_content with subprocess exception."""
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "tmux")):
            content = ClaudeInterface._get_pane_content("session:0")
            assert content == ""

    @pytest.mark.parametrize(
        "content,expected",
        [
            ("│ > ", True),
            ("> ", True),
            ("Type a message", True),
            ("Claude Code 1.0", True),
            ("bash-4.2$", False),
            ("", False),
            ("random text", False),
        ],
    )
    def test_is_claude_ready(self, content, expected):
        """Test Claude readiness detection."""
        assert ClaudeInterface._is_claude_ready(content) == expected

    def test_clear_input(self):
        """Test input clearing functionality."""
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            ClaudeInterface._clear_input("session:0")

            expected_calls = [
                call(["tmux", "send-keys", "-t", "session:0", "C-c"], check=False),
                call(["tmux", "send-keys", "-t", "session:0", "C-u"], check=False),
                call(["tmux", "send-keys", "-t", "session:0", "Escape"], check=False),
                call(["tmux", "send-keys", "-t", "session:0", "C-a"], check=False),
                call(["tmux", "send-keys", "-t", "session:0", "C-k"], check=False),
            ]

            mock_run.assert_has_calls(expected_calls)

    def test_method_standard_submit_success(self):
        """Test standard submission method."""
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            result = ClaudeInterface._method_standard_submit("session:0", "test message")

            assert result is True
            expected_calls = [
                call(["tmux", "send-keys", "-t", "session:0", "test message"], check=True),
                call(["tmux", "send-keys", "-t", "session:0", "C-Enter"], check=True),
            ]
            mock_run.assert_has_calls(expected_calls)

    def test_method_standard_submit_failure(self):
        """Test standard submission method with exception."""
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "tmux")):
            result = ClaudeInterface._method_standard_submit("session:0", "test message")
            assert result is False

    def test_method_paste_and_submit_success(self):
        """Test paste buffer submission method."""
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            result = ClaudeInterface._method_paste_and_submit("session:0", "test message")

            assert result is True
            expected_calls = [
                call(["tmux", "set-buffer", "test message"], check=True),
                call(["tmux", "paste-buffer", "-t", "session:0"], check=True),
                call(["tmux", "send-keys", "-t", "session:0", "C-Enter"], check=True),
            ]
            mock_run.assert_has_calls(expected_calls)

    def test_method_paste_and_submit_failure(self):
        """Test paste buffer submission method with exception."""
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "tmux")):
            result = ClaudeInterface._method_paste_and_submit("session:0", "test message")
            assert result is False

    def test_method_literal_keys_success(self):
        """Test literal keys submission method."""
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            result = ClaudeInterface._method_literal_keys("session:0", "test message")

            assert result is True
            expected_calls = [
                call(["tmux", "send-keys", "-t", "session:0", "-l", "test message"], check=True),
                call(["tmux", "send-keys", "-t", "session:0", "C-Enter"], check=True),
            ]
            mock_run.assert_has_calls(expected_calls)

    def test_method_literal_keys_failure(self):
        """Test literal keys submission method with exception."""
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "tmux")):
            result = ClaudeInterface._method_literal_keys("session:0", "test message")
            assert result is False

    def test_method_multiple_enters_success(self):
        """Test multiple enters submission method."""
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            result = ClaudeInterface._method_multiple_enters("session:0", "test message")

            assert result is True
            expected_calls = [
                call(["tmux", "send-keys", "-t", "session:0", "test message"], check=True),
                call(["tmux", "send-keys", "-t", "session:0", "C-Enter"], check=True),
            ]
            mock_run.assert_has_calls(expected_calls)

    def test_method_multiple_enters_failure(self):
        """Test multiple enters submission method with exception."""
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "tmux")):
            result = ClaudeInterface._method_multiple_enters("session:0", "test message")
            assert result is False

    def test_method_escape_sequence_success(self):
        """Test escape sequence submission method."""
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            result = ClaudeInterface._method_escape_sequence("session:0", "test message")

            assert result is True
            expected_calls = [
                call(["tmux", "send-keys", "-t", "session:0", "test message\n"], check=True),
                call(["tmux", "send-keys", "-t", "session:0", "\r"], check=True),
            ]
            mock_run.assert_has_calls(expected_calls)

    def test_method_escape_sequence_failure(self):
        """Test escape sequence submission method with exception."""
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "tmux")):
            result = ClaudeInterface._method_escape_sequence("session:0", "test message")
            assert result is False

    @pytest.mark.parametrize(
        "old_content,new_content,message,expected",
        [
            ("old content", "new content without message", "test message", False),  # Message disappeared
            (
                "old content",
                "new content with test message",
                "test message",
                False,
            ),  # Message still there, no response indicators
            (
                "line1\nline2 test",
                "line1\nline2 test\nClaude: response",
                "test",
                True,
            ),  # Claude responded with message present
            (
                "line1\nline2 test",
                "line1\nline2 test\nI'll help you",
                "test",
                True,
            ),  # Response indicator with message present
            (
                "line1\nline2 test",
                "line1\nline2 test\nline3\nline4\nline5",
                "test",
                True,
            ),  # More lines added with message present
            ("content", "content", "test", False),  # No change
        ],
    )
    def test_message_was_submitted(self, old_content, new_content, message, expected):
        """Test message submission detection."""
        result = ClaudeInterface._message_was_submitted(old_content, new_content, message)
        assert result == expected


class TestClaudeAgentManager:
    """Test ClaudeAgentManager class methods."""

    def test_initialize_agent_success(self):
        """Test successful agent initialization."""
        with (
            patch.object(ClaudeInterface, "_get_pane_content") as mock_get_content,
            patch.object(ClaudeInterface, "_is_claude_ready", return_value=True) as mock_ready,
            patch.object(ClaudeInterface, "send_message_to_claude", return_value=(True, "")) as mock_send,
            patch("time.sleep"),
        ):
            mock_get_content.return_value = "Claude ready"

            result = ClaudeAgentManager.initialize_agent("test-session", "0", "Test briefing")

            assert result is True
            mock_ready.assert_called_once_with("Claude ready")
            mock_send.assert_called_once_with("test-session:0", "Test briefing")

    def test_initialize_agent_claude_not_ready_timeout(self):
        """Test agent initialization when Claude never becomes ready."""
        with (
            patch.object(ClaudeInterface, "_get_pane_content", return_value="bash prompt") as mock_get_content,
            patch.object(ClaudeInterface, "_is_claude_ready", return_value=False) as mock_ready,
            patch("time.sleep"),
        ):
            result = ClaudeAgentManager.initialize_agent("test-session", "0", "Test briefing")

            assert result is False
            # Should attempt 30 times (max_attempts)
            assert mock_get_content.call_count == 30
            assert mock_ready.call_count == 30

    def test_initialize_agent_briefing_failure_with_file_fallback(self):
        """Test agent initialization with briefing failure and file fallback."""
        with (
            patch.object(ClaudeInterface, "_get_pane_content", return_value="Claude ready"),
            patch.object(ClaudeInterface, "_is_claude_ready", return_value=True),
            patch.object(ClaudeInterface, "send_message_to_claude") as mock_send,
            patch("builtins.open", mock_open()) as mock_file,
            patch("time.sleep"),
        ):
            # First call fails (briefing), second call succeeds (file read command)
            mock_send.side_effect = [(False, "submission failed"), (True, "")]

            result = ClaudeAgentManager.initialize_agent("test-session", "0", "Test briefing")

            assert result is False  # Original briefing failed

            # Verify file was created
            expected_path = BRIEFINGS_DIR / "briefing_test-session_0.txt"
            mock_file.assert_called_once_with(expected_path, "w")
            mock_file().write.assert_called_once_with("BRIEFING: Test briefing\n")

            # Verify both send attempts
            assert mock_send.call_count == 2
            mock_send.assert_any_call("test-session:0", "Test briefing")
            # Second call should be the file read command
            second_call_args = mock_send.call_args_list[1][0]
            assert "Please read the briefing at" in second_call_args[1]
            assert str(expected_path) in second_call_args[1]

    def test_initialize_agent_file_fallback_exception(self):
        """Test agent initialization with file fallback exception."""
        with (
            patch.object(ClaudeInterface, "_get_pane_content", return_value="Claude ready"),
            patch.object(ClaudeInterface, "_is_claude_ready", return_value=True),
            patch.object(ClaudeInterface, "send_message_to_claude", return_value=(False, "failed")),
            patch("builtins.open", side_effect=OSError("Permission denied")),
            patch("time.sleep"),
        ):
            result = ClaudeAgentManager.initialize_agent("test-session", "0", "Test briefing")

            assert result is False

    def test_initialize_agent_claude_becomes_ready_after_wait(self):
        """Test agent initialization when Claude becomes ready after waiting."""
        with (
            patch.object(ClaudeInterface, "_get_pane_content") as mock_get_content,
            patch.object(ClaudeInterface, "_is_claude_ready") as mock_ready,
            patch.object(ClaudeInterface, "send_message_to_claude", return_value=(True, "")) as mock_send,
            patch("time.sleep"),
        ):
            # Claude not ready for first 5 checks, then ready
            mock_get_content.side_effect = ["bash"] * 5 + ["Claude ready"]
            mock_ready.side_effect = [False] * 5 + [True]

            result = ClaudeAgentManager.initialize_agent("test-session", "0", "Test briefing")

            assert result is True
            assert mock_get_content.call_count == 6
            assert mock_ready.call_count == 6
            mock_send.assert_called_once_with("test-session:0", "Test briefing")


class TestModuleConstants:
    """Test module-level constants and initialization."""

    def test_project_directory_creation(self):
        """Test that project directories are created."""
        # These should be created when the module is imported
        assert PROJECT_DIR.exists()
        assert BRIEFINGS_DIR.exists()
        assert BRIEFINGS_DIR.parent == PROJECT_DIR

    def test_project_directory_path(self):
        """Test that project directory is in the correct location."""
        expected_path = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")
        assert PROJECT_DIR == expected_path

    def test_briefings_directory_path(self):
        """Test that briefings directory is in the correct location."""
        expected_path = PROJECT_DIR / "briefings"
        assert BRIEFINGS_DIR == expected_path


class TestIntegrationScenarios:
    """Integration tests for complex scenarios."""

    def test_full_agent_communication_flow(self):
        """Test complete flow of agent communication."""
        with (
            patch.object(ClaudeInterface, "_get_pane_content") as mock_get_content,
            patch.object(ClaudeInterface, "_is_claude_ready", return_value=True),
            patch.object(ClaudeInterface, "_clear_input"),
            patch.object(ClaudeInterface, "_method_standard_submit", return_value=True),
            patch.object(ClaudeInterface, "_message_was_submitted", return_value=True),
            patch("time.sleep"),
        ):
            # Mock pane content for before and after
            mock_get_content.side_effect = ["│ > ", "Claude: response"]

            # Test the full flow
            success, error = ClaudeInterface.send_message_to_claude("session:0", "Hello Claude")

            assert success is True
            assert error == ""

    def test_agent_initialization_robust_flow(self):
        """Test robust agent initialization under various conditions."""
        with (
            patch.object(ClaudeInterface, "_get_pane_content") as mock_content,
            patch.object(ClaudeInterface, "_is_claude_ready") as mock_ready,
            patch.object(ClaudeInterface, "send_message_to_claude") as mock_send,
            patch("time.sleep"),
        ):
            # Simulate Claude starting up (not ready -> ready)
            mock_content.side_effect = ["starting...", "loading...", "│ > "]
            mock_ready.side_effect = [False, False, True]
            mock_send.return_value = (True, "")

            result = ClaudeAgentManager.initialize_agent("session", "window", "briefing")

            assert result is True
            assert mock_content.call_count == 3
            assert mock_ready.call_count == 3
            mock_send.assert_called_once_with("session:window", "briefing")
