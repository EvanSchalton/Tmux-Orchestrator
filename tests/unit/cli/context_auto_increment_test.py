#!/usr/bin/env python3
"""
Test suite for context spawn auto-increment functionality.
Tests the context command's handling of window indices.
"""

import unittest
from unittest.mock import MagicMock, patch

import click
from click.testing import CliRunner

from tmux_orchestrator.cli.context import context

# TMUXManager import removed - using comprehensive_mock_tmux fixture


class TestContextAutoIncrement(unittest.TestCase):
    """Test cases for context spawn with auto-increment"""

    def setUp(self):
        """Set up test fixtures"""
        self.runner = CliRunner()
        # TMUXManager removed - tests will use comprehensive_mock_tmux fixture

    @patch("subprocess.run")
    @patch("tmux_orchestrator.cli.context.load_context")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.list_sessions")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.list_windows")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.send_keys")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.send_message")
    @patch("time.sleep")
    def test_context_spawn_ignores_window_index(
        self,
        mock_sleep,
        mock_send_msg,
        mock_send_keys,
        mock_list_windows,
        mock_list_sessions,
        mock_load_context,
        mock_run,
    ):
        """Test that context spawn ignores window index in session:window format"""
        # Setup mocks
        mock_load_context.return_value = "PM context content"
        mock_list_sessions.return_value = [{"name": "test-session"}]
        mock_list_windows.side_effect = [
            # First call after window creation
            [{"name": "existing", "index": 0}, {"name": "Claude-pm", "index": 1}]
        ]
        mock_run.return_value = MagicMock(returncode=0)
        mock_send_msg.return_value = True

        # Run context spawn with window index (should be ignored)
        result = self.runner.invoke(context, ["spawn", "pm", "--session", "test-session:5"])

        # Should succeed with warning about ignored index
        self.assertEqual(result.exit_code, 0)
        self.assertIn("will be ignored", result.output)

        # Verify new-window was called without specific index
        mock_run.assert_called_with(
            ["tmux", "new-window", "-t", "test-session", "-n", "Claude-pm"], capture_output=True, timeout=3
        )

    @patch("subprocess.run")
    @patch("tmux_orchestrator.cli.context.load_context")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.list_sessions")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.list_windows")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.send_keys")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.send_message")
    @patch("time.sleep")
    def test_context_spawn_creates_at_end(
        self,
        mock_sleep,
        mock_send_msg,
        mock_send_keys,
        mock_list_windows,
        mock_list_sessions,
        mock_load_context,
        mock_run,
    ):
        """Test that context spawn creates windows at the end of session"""
        # Setup mocks for session with gaps
        mock_load_context.return_value = "Orchestrator context"
        mock_list_sessions.return_value = [{"name": "main"}]
        mock_list_windows.side_effect = [
            # Windows with gaps: 0, 2, 5
            [
                {"name": "window0", "index": 0},
                {"name": "window2", "index": 2},
                {"name": "window5", "index": 5},
                {"name": "Claude-orchestrator", "index": 6},  # New window at end
            ]
        ]
        mock_run.return_value = MagicMock(returncode=0)
        mock_send_msg.return_value = True

        # Run context spawn
        result = self.runner.invoke(context, ["spawn", "orchestrator", "--session", "main"])

        # Should succeed
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Created window: main:6", result.output)

    @patch("subprocess.run")
    @patch("tmux_orchestrator.cli.context.load_context")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.list_sessions")
    def test_context_spawn_creates_new_session(self, mock_list_sessions, mock_load_context, mock_run):
        """Test that context spawn creates session if it doesn't exist"""
        # Setup mocks
        mock_load_context.return_value = "PM context"
        mock_list_sessions.return_value = []  # No existing sessions
        mock_run.side_effect = [
            MagicMock(returncode=0),  # new-session
            MagicMock(returncode=0),  # new-window
        ]

        # Mock the rest to prevent actual execution
        with patch("tmux_orchestrator.utils.tmux.TMUXManager.list_windows") as mock_list_windows:
            with patch("tmux_orchestrator.utils.tmux.TMUXManager.send_keys"):
                with patch("tmux_orchestrator.utils.tmux.TMUXManager.send_message"):
                    with patch("time.sleep"):
                        mock_list_windows.return_value = [{"name": "Claude-pm", "index": 0}]

                        # Run context spawn
                        result = self.runner.invoke(context, ["spawn", "pm", "--session", "new-project"])

        # Should create session first
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Creating new session", result.output)

        # Verify session creation
        session_create_call = mock_run.call_args_list[0]
        self.assertEqual(session_create_call[0][0], ["tmux", "new-session", "-d", "-s", "new-project"])

    @patch("subprocess.run")
    @patch("tmux_orchestrator.cli.context.load_context")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.list_sessions")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.list_windows")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.send_keys")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.send_message")
    @patch("time.sleep")
    def test_context_spawn_with_extension(
        self,
        mock_sleep,
        mock_send_msg,
        mock_send_keys,
        mock_list_windows,
        mock_list_sessions,
        mock_load_context,
        mock_run,
    ):
        """Test context spawn with --extend option"""
        # Setup mocks
        mock_load_context.return_value = "PM context"
        mock_list_sessions.return_value = [{"name": "project"}]
        mock_list_windows.return_value = [{"name": "Claude-pm", "index": 0}]
        mock_run.return_value = MagicMock(returncode=0)
        mock_send_msg.return_value = True

        # Run with extension
        result = self.runner.invoke(
            context, ["spawn", "pm", "--session", "project", "--extend", "Focus on API refactoring"]
        )

        # Should succeed
        self.assertEqual(result.exit_code, 0)

        # Verify extended message was sent
        mock_send_msg.assert_called_once()
        sent_message = mock_send_msg.call_args[0][1]
        self.assertIn("Additional Instructions", sent_message)
        self.assertIn("Focus on API refactoring", sent_message)

    def test_context_spawn_invalid_role(self):
        """Test context spawn with invalid role"""
        with patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.side_effect = click.ClickException("Context 'developer' not found")

            result = self.runner.invoke(context, ["spawn", "developer", "--session", "test"])

            # The command returns with exit code 0 but displays an error message
            self.assertEqual(result.exit_code, 0)
            # The error handling in context spawn now shows "Error:" prefix from Click
            self.assertIn("Context 'developer' not found", result.output)
            self.assertIn("Only system roles", result.output)

    @patch("subprocess.run")
    @patch("tmux_orchestrator.cli.context.load_context")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.list_sessions")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.list_windows")
    def test_context_spawn_window_creation_failure(
        self, mock_list_windows, mock_list_sessions, mock_load_context, mock_run
    ):
        """Test handling of window creation failure"""
        # Setup mocks
        mock_load_context.return_value = "PM context"
        mock_list_sessions.return_value = [{"name": "test"}]
        # Mock run to return failure (returncode != 0)
        mock_run.return_value = MagicMock(returncode=1)

        # Run context spawn
        result = self.runner.invoke(context, ["spawn", "pm", "--session", "test"])

        # The command returns with exit code 0 but displays an error message
        self.assertEqual(result.exit_code, 0)
        # Check for the actual error message from the implementation
        self.assertIn("Failed to create window", result.output)

    @patch("subprocess.run")
    @patch("tmux_orchestrator.cli.context.load_context")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.list_sessions")
    @patch("tmux_orchestrator.utils.tmux.TMUXManager.list_windows")
    def test_context_spawn_window_not_found_after_creation(
        self,
        mock_list_windows,
        mock_list_sessions,
        mock_load_context,
        mock_run,
    ):
        """Test handling when created window is not found"""
        # Setup mocks
        mock_load_context.return_value = "PM context"
        mock_list_sessions.return_value = [{"name": "test"}]
        mock_list_windows.return_value = []  # Window not found after creation
        mock_run.return_value = MagicMock(returncode=0)

        # Run context spawn - this should now succeed with the fallback logic
        result = self.runner.invoke(context, ["spawn", "pm", "--session", "test"])

        # The command returns with exit code 0 but displays an error message
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Window created but not found", result.output)


class TestContextCommands(unittest.TestCase):
    """Test other context commands"""

    def setUp(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    @patch("tmux_orchestrator.cli.context.get_available_contexts")
    def test_context_list(self, mock_get_contexts):
        """Test context list command"""
        # Mock available contexts
        from pathlib import Path

        mock_contexts = {
            "pm": MagicMock(spec=Path, read_text=lambda: "# PM Context\nProject Manager role"),
            "orchestrator": MagicMock(spec=Path, read_text=lambda: "# Orchestrator\nMain orchestrator role"),
        }
        mock_get_contexts.return_value = mock_contexts

        # Run list command
        result = self.runner.invoke(context, ["list"])

        # Should succeed and show contexts
        self.assertEqual(result.exit_code, 0)
        self.assertIn("pm", result.output)
        self.assertIn("orchestrator", result.output)
        self.assertIn("Project Manager role", result.output)

    @patch("tmux_orchestrator.cli.context.load_context")
    def test_context_show(self, mock_load_context):
        """Test context show command"""
        mock_load_context.return_value = "# PM Context\n\nThis is the PM context content."

        # Run show command
        result = self.runner.invoke(context, ["show", "pm"])

        # Should succeed and display content
        self.assertEqual(result.exit_code, 0)
        self.assertIn("PM Context", result.output)

    @patch("tmux_orchestrator.cli.context.load_context")
    def test_context_show_raw(self, mock_load_context):
        """Test context show with --raw flag"""
        mock_load_context.return_value = "# PM Context\n\nRaw content here."

        # Run show command with --raw
        result = self.runner.invoke(context, ["show", "pm", "--raw"])

        # Should output raw content
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output.strip(), "# PM Context\n\nRaw content here.")

    @patch("tmux_orchestrator.cli.context.load_context")
    def test_context_export(self, mock_load_context):
        """Test context export command"""
        mock_load_context.return_value = "# PM Context\n\nOriginal content."

        with self.runner.isolated_filesystem():
            # Run export command
            result = self.runner.invoke(context, ["export", "my-pm.md", "--role", "pm", "--project", "Test Project"])

            # Should succeed
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Exported pm context", result.output)

            # Verify file created with correct content
            from pathlib import Path

            exported = Path("my-pm.md").read_text()
            self.assertIn("# PM Context", exported)
            self.assertIn("Original content", exported)
            self.assertIn("## Project: Test Project", exported)


if __name__ == "__main__":
    unittest.main()
