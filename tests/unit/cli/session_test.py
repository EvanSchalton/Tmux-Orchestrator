"""Tests for session management CLI commands."""

import json
import os
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.session import session
from tmux_orchestrator.utils.tmux import TMUXManager

# TMUXManager import removed - using comprehensive_mock_tmux fixture


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_tmux() -> Mock:
    """Create a mock TMUXManager."""
    return Mock(spec=TMUXManager)


class TestSessionList:
    """Tests for the 'session list' command."""

    def test_list_no_sessions(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test listing when no sessions exist."""
        mock_tmux.list_sessions.return_value = []

        result = runner.invoke(session, ["list"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "No tmux sessions found" in result.output
        mock_tmux.list_sessions.assert_called_once()

    def test_list_with_sessions(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test listing sessions with rich table output."""
        mock_sessions = [
            {"name": "dev-session", "created": "2024-01-15 10:30:00", "attached": True},
            {"name": "test-session", "created": "2024-01-15 11:00:00", "attached": False},
        ]
        mock_tmux.list_sessions.return_value = mock_sessions
        mock_tmux.list_windows.side_effect = [
            [{"window": "0", "name": "main"}, {"window": "1", "name": "vim"}],  # dev-session windows
            [{"window": "0", "name": "tests"}],  # test-session windows
        ]

        result = runner.invoke(session, ["list"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Tmux Sessions" in result.output
        assert "dev-session" in result.output
        assert "test-session" in result.output
        assert "Total sessions: 2" in result.output
        # Check window counts
        assert "2" in result.output  # dev-session has 2 windows
        assert "1" in result.output  # test-session has 1 window

        # Verify tmux calls
        mock_tmux.list_sessions.assert_called_once()
        assert mock_tmux.list_windows.call_count == 2
        mock_tmux.list_windows.assert_any_call("dev-session")
        mock_tmux.list_windows.assert_any_call("test-session")

    def test_list_json_output_no_sessions(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test JSON output when no sessions exist."""
        mock_tmux.list_sessions.return_value = []

        result = runner.invoke(session, ["list", "--json"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data == {"sessions": [], "count": 0}
        mock_tmux.list_sessions.assert_called_once()

    def test_list_json_output_with_sessions(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test JSON output with sessions."""
        mock_sessions = [{"name": "dev-session", "created": "2024-01-15 10:30:00", "attached": True}]
        mock_tmux.list_sessions.return_value = mock_sessions
        mock_tmux.list_windows.return_value = [{"window": "0", "name": "main"}, {"window": "1", "name": "vim"}]

        result = runner.invoke(session, ["list", "--json"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["count"] == 1
        assert len(output_data["sessions"]) == 1
        assert output_data["sessions"][0]["name"] == "dev-session"
        assert output_data["sessions"][0]["window_count"] == "2"  # window_count is stored as string

        mock_tmux.list_sessions.assert_called_once()
        mock_tmux.list_windows.assert_called_once_with("dev-session")

    def test_list_exception_handling(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test error handling when tmux operations fail."""
        mock_tmux.list_sessions.side_effect = Exception("TMUX connection failed")

        result = runner.invoke(session, ["list"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Failed to list sessions" in result.output
        assert "TMUX connection failed" in result.output

    def test_list_exception_handling_json(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test error handling in JSON mode."""
        mock_tmux.list_sessions.side_effect = Exception("TMUX connection failed")

        result = runner.invoke(session, ["list", "--json"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert "error" in output_data
        assert "Failed to list sessions" in output_data["error"]


class TestSessionAttach:
    """Tests for the 'session attach' command."""

    def test_attach_session_not_exists(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test attaching to a non-existent session."""
        mock_tmux.has_session.return_value = False
        mock_tmux.list_sessions.return_value = [{"name": "existing-session"}, {"name": "another-session"}]

        result = runner.invoke(session, ["attach", "nonexistent"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Session 'nonexistent' does not exist" in result.output
        assert "Available sessions:" in result.output
        assert "existing-session" in result.output
        assert "another-session" in result.output

        mock_tmux.has_session.assert_called_once_with("nonexistent")
        mock_tmux.list_sessions.assert_called_once()

    def test_attach_no_available_sessions(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test attaching when no sessions exist at all."""
        mock_tmux.has_session.return_value = False
        mock_tmux.list_sessions.return_value = []

        result = runner.invoke(session, ["attach", "nonexistent"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Session 'nonexistent' does not exist" in result.output
        assert "No sessions available" in result.output

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    def test_attach_success(self, mock_subprocess: Mock, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test successful session attachment."""
        mock_tmux.has_session.return_value = True

        result = runner.invoke(session, ["attach", "dev-session"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Attaching to session 'dev-session'" in result.output

        mock_tmux.has_session.assert_called_once_with("dev-session")
        mock_subprocess.assert_called_once_with(["tmux", "attach-session", "-t", "dev-session"])

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    def test_attach_read_only(self, mock_subprocess: Mock, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test attaching in read-only mode."""
        mock_tmux.has_session.return_value = True

        result = runner.invoke(session, ["attach", "dev-session", "--read-only"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Attaching to session 'dev-session'" in result.output

        mock_subprocess.assert_called_once_with(["tmux", "attach-session", "-t", "dev-session", "-r"])

    @patch.dict(os.environ, {"TMUX": "/tmp/tmux-1000/default,1234,0"})
    def test_attach_already_in_tmux(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test attaching when already inside a tmux session."""
        mock_tmux.has_session.return_value = True

        result = runner.invoke(session, ["attach", "dev-session"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Already inside a tmux session" in result.output
        assert "tmux switch-client -t dev-session" in result.output

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    def test_attach_exception_handling(self, mock_subprocess: Mock, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test error handling during attachment."""
        mock_tmux.has_session.return_value = True
        mock_subprocess.side_effect = Exception("Failed to attach")

        result = runner.invoke(session, ["attach", "dev-session"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Failed to attach to session" in result.output
        assert "Failed to attach" in result.output


class TestSessionCommandGroup:
    """Tests for the session command group itself."""

    def test_session_help(self, runner: CliRunner) -> None:
        """Test session command help text."""
        result = runner.invoke(session, ["--help"])

        assert result.exit_code == 0
        assert "Manage tmux sessions" in result.output
        assert "list" in result.output
        assert "attach" in result.output

    def test_session_list_help(self, runner: CliRunner) -> None:
        """Test session list command help."""
        result = runner.invoke(session, ["list", "--help"])

        assert result.exit_code == 0
        assert "List all tmux sessions" in result.output
        assert "--json" in result.output

    def test_session_attach_help(self, runner: CliRunner) -> None:
        """Test session attach command help."""
        result = runner.invoke(session, ["attach", "--help"])

        assert result.exit_code == 0
        assert "Attach to an existing tmux session" in result.output
        assert "--read-only" in result.output
        assert "SESSION_NAME" in result.output
