"""Tests for context spawn command."""

from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.context import context


class TestContextSpawn:
    """Test context spawn command functionality."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_tmux(self):
        """Mock TMUXManager."""
        with patch("tmux_orchestrator.utils.tmux.TMUXManager") as mock:
            tmux_instance = MagicMock()
            mock.return_value = tmux_instance
            tmux_instance.list_sessions.return_value = [{"name": "test"}]
            tmux_instance.send_message.return_value = True
            tmux_instance.create_window.return_value = True
            tmux_instance.list_windows.return_value = [{"name": "Claude-pm", "index": "1"}]
            tmux_instance.send_keys.return_value = True
            yield tmux_instance

    def test_spawn_pm_sends_instruction(self, runner, mock_tmux):
        """Test spawning PM sends instruction message."""
        with patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "PM context"
            with patch("time.sleep"):
                result = runner.invoke(context, ["spawn", "pm", "--session", "test:1"])

        assert result.exit_code == 0
        assert "Successfully spawned pm agent" in result.output

        # Verify instruction message was sent
        mock_tmux.send_message.assert_called_once()
        call_args = mock_tmux.send_message.call_args[0]
        assert call_args[0] == "test:1"  # Target session
        # Check that the message contains the expected instruction
        assert "You're the PM for our team" in call_args[1]
        assert "tmux-orc context show pm" in call_args[1]

    def test_spawn_orchestrator_sends_instruction(self, runner, mock_tmux):
        """Test spawning orchestrator sends instruction message."""
        mock_tmux.list_windows.return_value = [{"name": "Claude-orc", "index": "0"}]
        with patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "Orc context"
            with patch("time.sleep"):
                result = runner.invoke(context, ["spawn", "orc", "--session", "test:0"])

        assert result.exit_code == 0
        assert "Successfully spawned" in result.output
        assert "orc" in result.output.lower()

        # Verify instruction message was sent
        mock_tmux.send_message.assert_called_once()
        session, message = mock_tmux.send_message.call_args[0]
        assert session == "test:0"
        assert "You're the orchestrator for our team" in message
        assert "tmux-orc context show" in message

    def test_spawn_with_extend(self, runner, mock_tmux):
        """Test spawning with --extend adds additional instructions."""
        with patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "PM context"
            with patch("time.sleep"):
                result = runner.invoke(
                    context, ["spawn", "pm", "--session", "test:1", "--extend", "Focus on performance"]
                )

        assert result.exit_code == 0

        # Verify extended message was sent
        mock_tmux.send_message.assert_called_once()
        session, message = mock_tmux.send_message.call_args[0]
        assert session == "test:1"
        assert "You're the PM for our team" in message
        assert "## Additional Instructions" in message
        assert "Focus on performance" in message

    def test_spawn_invalid_session_format(self, runner, mock_tmux):
        """Test session without window index is accepted (auto-increments)."""
        with patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "PM context"
            with patch("time.sleep"):
                result = runner.invoke(context, ["spawn", "pm", "--session", "invalid"])

        # Session name without window index is now accepted
        assert result.exit_code == 0
        # Should create window successfully
        assert "Successfully spawned" in result.output or "Created window" in result.output

    def test_spawn_creates_new_session(self, runner, mock_tmux):
        """Test spawn creates new session if needed."""
        mock_tmux.list_sessions.return_value = []  # No existing sessions
        mock_tmux.create_session.return_value = True

        with patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.return_value = "PM context"
            with patch("time.sleep"):
                result = runner.invoke(context, ["spawn", "pm", "--session", "newsession:1"])

        assert result.exit_code == 0
        # Check that session creation was mentioned
        assert "Creating new session" in result.output or "newsession" in result.output
        # Verify create_session was called
        mock_tmux.create_session.assert_called_once_with("newsession")

    def test_spawn_unsupported_role(self, runner, mock_tmux):
        """Test spawning unsupported role shows error."""
        with patch("tmux_orchestrator.cli.context.load_context") as mock_load:
            mock_load.side_effect = click.ClickException("Context 'developer' not found")
            result = runner.invoke(context, ["spawn", "developer", "--session", "test:2"])

        assert result.exit_code == 0
        assert "Only system roles" in result.output
        assert "custom briefings" in result.output
