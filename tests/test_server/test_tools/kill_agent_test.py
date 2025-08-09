"""Tests for kill_agent business logic tool."""

from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.server.tools.kill_agent import KillAgentRequest, kill_agent


@pytest.fixture
def mock_tmux():
    """Create a mock TMUXManager for testing."""
    return MagicMock()


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


class TestKillAgent:
    """Test kill_agent function."""

    def test_kill_agent_invalid_target_format(self, mock_tmux):
        """Test kill_agent with invalid target format."""
        # Arrange
        request = KillAgentRequest(
            target="invalid-target",
            reason="Test termination",
        )

        # Act
        result = kill_agent(mock_tmux, request)

        # Assert
        assert not result.success
        assert result.target == "invalid-target"
        assert result.reason == "Test termination"
        assert result.error_message == "Target must be in format 'session:window' or 'session:window.pane'"
        assert not result.graceful_shutdown
        assert not result.pm_notified

    def test_kill_agent_session_not_found(self, mock_tmux):
        """Test kill_agent when session doesn't exist."""
        # Arrange
        request = KillAgentRequest(
            target="nonexistent:1",
            reason="Test termination",
        )
        mock_tmux.has_session.return_value = False

        # Act
        result = kill_agent(mock_tmux, request)

        # Assert
        assert not result.success
        assert result.error_message == "Session 'nonexistent' not found"
        mock_tmux.has_session.assert_called_once_with("nonexistent")

    def test_kill_agent_graceful_shutdown_success(self, mock_tmux, mock_logger):
        """Test successful graceful shutdown."""
        # Arrange
        request = KillAgentRequest(
            target="test-session:1",
            reason="Test graceful termination",
            force=False,
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.send_keys.return_value = True
        # Capture fails immediately (pane gone after exit command)
        mock_tmux.capture_pane.side_effect = Exception("Pane not found")

        # Act
        with patch("time.sleep"):  # Mock sleep to speed up test
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                result = kill_agent(mock_tmux, request)

        # Assert
        assert result.success
        assert result.graceful_shutdown
        mock_tmux.send_keys.assert_called_once_with("test-session:1", "exit")
        mock_logger.info.assert_called()

    def test_kill_agent_force_kill(self, mock_tmux, mock_logger):
        """Test force kill without graceful shutdown."""
        # Arrange
        request = KillAgentRequest(
            target="test-session:2",
            reason="Force termination",
            force=True,
            notify_pm=False,
        )
        mock_tmux.has_session.return_value = True

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = kill_agent(mock_tmux, request)

        # Assert
        assert result.success
        assert not result.graceful_shutdown  # No graceful shutdown attempted
        assert not result.pm_notified  # PM notification disabled
        mock_tmux.send_keys.assert_not_called()  # No exit command sent

    def test_kill_agent_with_pm_notification(self, mock_tmux, mock_logger):
        """Test killing agent with PM notification."""
        # Arrange
        request = KillAgentRequest(
            target="test-session:3",
            reason="Agent unresponsive",
            force=True,
            notify_pm=True,
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.list_windows.return_value = [{"id": "5", "name": "Project-Manager"}]
        mock_tmux.send_message.return_value = True

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = kill_agent(mock_tmux, request)

        # Assert
        assert result.success
        assert result.pm_notified
        # Check PM notification was sent
        mock_tmux.send_message.assert_called_once()
        call_args = mock_tmux.send_message.call_args[0]
        assert "tmux-orc-dev:5" == call_args[0]
        assert "AGENT TERMINATED" in call_args[1]
        assert "test-session:3" in call_args[1]
        assert "Agent unresponsive" in call_args[1]

    def test_kill_agent_pane_target(self, mock_tmux, mock_logger):
        """Test killing a specific pane."""
        # Arrange
        request = KillAgentRequest(
            target="test-session:1.2",
            reason="Kill specific pane",
            force=True,
        )
        mock_tmux.has_session.return_value = True

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = kill_agent(mock_tmux, request)

        # Assert
        assert result.success
        mock_run.assert_called_once_with(
            ["tmux", "kill-pane", "-t", "test-session:1.2"],
            capture_output=True,
            text=True,
        )

    def test_kill_agent_kill_fails(self, mock_tmux, mock_logger):
        """Test when kill operation fails."""
        # Arrange
        request = KillAgentRequest(
            target="test-session:4",
            reason="Test failed kill",
            force=True,
        )
        mock_tmux.has_session.return_value = True

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1  # Simulate failure
            result = kill_agent(mock_tmux, request)

        # Assert
        assert not result.success
        assert result.error_message == "Failed to kill target pane/window"

    def test_kill_agent_unexpected_error(self, mock_tmux):
        """Test handling of unexpected errors."""
        # Arrange
        request = KillAgentRequest(
            target="test-session:5",
            reason="Test error handling",
        )
        mock_tmux.has_session.side_effect = Exception("Unexpected tmux error")

        # Act
        result = kill_agent(mock_tmux, request)

        # Assert
        assert not result.success
        assert "Unexpected error killing agent: Unexpected tmux error" in result.error_message

    def test_kill_agent_no_pm_found(self, mock_tmux, mock_logger):
        """Test when PM cannot be found for notification."""
        # Arrange
        request = KillAgentRequest(
            target="test-session:6",
            reason="Test no PM",
            force=True,
            notify_pm=True,
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.list_sessions.return_value = []  # No sessions with PM

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = kill_agent(mock_tmux, request)

        # Assert
        assert result.success
        assert not result.pm_notified  # PM notification failed but kill succeeded
        mock_tmux.send_message.assert_not_called()

    def test_kill_agent_graceful_shutdown_timeout(self, mock_tmux, mock_logger):
        """Test graceful shutdown that times out and falls back to force."""
        # Arrange
        request = KillAgentRequest(
            target="test-session:7",
            reason="Test graceful timeout",
            force=False,
        )
        mock_tmux.has_session.return_value = True
        mock_tmux.send_keys.return_value = True
        # Pane still exists after exit command
        mock_tmux.capture_pane.return_value = "still alive"

        # Act
        with patch("time.sleep"):  # Mock sleep to speed up test
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                result = kill_agent(mock_tmux, request)

        # Assert
        assert result.success
        assert not result.graceful_shutdown  # Graceful shutdown failed
        mock_tmux.send_keys.assert_called_once_with("test-session:7", "exit")
