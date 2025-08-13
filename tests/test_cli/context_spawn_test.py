"""Tests for context spawn command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.context import spawn


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
            yield tmux_instance

    def test_spawn_pm_sends_instruction(self, runner, mock_tmux):
        """Test spawning PM sends instruction message."""
        with patch("subprocess.run"):
            with patch("time.sleep"):
                result = runner.invoke(spawn, ["pm", "--session", "test:1"])

        assert result.exit_code == 0
        assert "Successfully spawned pm agent" in result.output

        # Verify instruction message was sent
        mock_tmux.send_message.assert_called_once()
        session, message = mock_tmux.send_message.call_args[0]
        assert session == "test:1"
        assert (
            message
            == "You're the PM for our team, please run 'tmux-orc context show pm' for more information about your role"
        )

    def test_spawn_orchestrator_sends_instruction(self, runner, mock_tmux):
        """Test spawning orchestrator sends instruction message."""
        with patch("subprocess.run"):
            with patch("time.sleep"):
                result = runner.invoke(spawn, ["orchestrator", "--session", "test:0"])

        assert result.exit_code == 0
        assert "Successfully spawned orchestrator agent" in result.output

        # Verify instruction message was sent
        mock_tmux.send_message.assert_called_once()
        session, message = mock_tmux.send_message.call_args[0]
        assert session == "test:0"
        assert (
            message
            == "You're the orchestrator for our team, please run 'tmux-orc context show orchestrator' for more information about your role"
        )

    def test_spawn_with_extend(self, runner, mock_tmux):
        """Test spawning with --extend adds additional instructions."""
        with patch("subprocess.run"):
            with patch("time.sleep"):
                result = runner.invoke(spawn, ["pm", "--session", "test:1", "--extend", "Focus on performance"])

        assert result.exit_code == 0

        # Verify extended message was sent
        mock_tmux.send_message.assert_called_once()
        session, message = mock_tmux.send_message.call_args[0]
        assert session == "test:1"
        assert "You're the PM for our team" in message
        assert "## Additional Instructions" in message
        assert "Focus on performance" in message

    def test_spawn_invalid_session_format(self, runner, mock_tmux):
        """Test invalid session format shows error."""
        result = runner.invoke(spawn, ["pm", "--session", "invalid"])

        assert result.exit_code == 0  # Click doesn't exit non-zero by default
        assert "Invalid session format" in result.output
        assert "Use 'session:window'" in result.output

    def test_spawn_creates_new_session(self, runner, mock_tmux):
        """Test spawn creates new session if needed."""
        mock_tmux.list_sessions.return_value = []  # No existing sessions

        with patch("subprocess.run") as mock_subprocess:
            with patch("time.sleep"):
                result = runner.invoke(spawn, ["pm", "--session", "newsession:1"])

        assert result.exit_code == 0
        assert "Creating new session: newsession" in result.output

        # Verify tmux new-session was called
        mock_subprocess.assert_any_call(["tmux", "new-session", "-d", "-s", "newsession"], check=True)

    def test_spawn_unsupported_role(self, runner, mock_tmux):
        """Test spawning unsupported role shows error."""
        result = runner.invoke(spawn, ["developer", "--session", "test:2"])

        assert result.exit_code == 0
        assert "Only system roles (orchestrator, pm) have standard contexts" in result.output
        assert "Other agents should be spawned with custom briefings" in result.output
