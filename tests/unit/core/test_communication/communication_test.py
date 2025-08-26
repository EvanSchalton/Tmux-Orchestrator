"""Unit tests for core/communication module.

This module tests all communication functions including send_message and broadcast_message.
Focused on validating business logic with mocked TMUXManager for fast execution.
"""

import time
from unittest.mock import Mock, call, patch

import pytest

from tmux_orchestrator.core.communication.broadcast_message import broadcast_message
from tmux_orchestrator.core.communication.send_message import send_message
from tmux_orchestrator.utils.tmux import TMUXManager

# TMUXManager import removed - using comprehensive_mock_tmux fixture


class TestSendMessage:
    """Test send_message function with comprehensive scenarios."""

    @pytest.fixture
    def mock_tmux(self):
        """Create a mock TMUXManager for testing."""
        mock = Mock(spec=TMUXManager)
        mock.has_session.return_value = True
        mock.send_message.return_value = True
        return mock

    def test_send_message_success(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test successful message sending - happy path."""
        # Arrange
        target = "test-session:dev-window"
        message = "Hello developer!"

        # Act
        start_time = time.time()
        success, result_message = send_message(mock_tmux, target, message)
        execution_time = time.time() - start_time

        # Assert
        assert success is True
        assert "Message sent to" in result_message
        assert target in result_message
        assert execution_time < 1.0, f"send_message took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

        # Verify TMUXManager calls
        mock_tmux.has_session.assert_called_once_with("test-session")
        mock_tmux.send_message.assert_called_once_with(target, message, delay=0.5)

    def test_send_message_with_timeout(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test message sending with custom timeout."""
        # Arrange
        target = "test-session:window-1"
        message = "Test message"
        timeout = 15.0

        # Act
        success, result_message = send_message(mock_tmux, target, message, timeout)

        # Assert
        assert success is True
        assert "Message sent to" in result_message
        mock_tmux.send_message.assert_called_once_with(target, message, delay=0.5)

    def test_send_message_invalid_inputs(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test send_message with invalid input parameters."""
        # Test empty target
        success, message = send_message(mock_tmux, "", "test message")
        assert success is False
        assert "required" in message

        # Test empty message
        success, message = send_message(mock_tmux, "session:window", "")
        assert success is False
        assert "required" in message

        # Test None target
        success, message = send_message(mock_tmux, None, "test message")
        assert success is False
        assert "required" in message

        # Test None message
        success, message = send_message(mock_tmux, "session:window", None)
        assert success is False
        assert "required" in message

    def test_send_message_invalid_target_format(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test handling of invalid target format."""
        # Test missing colon
        success, message = send_message(mock_tmux, "session-window", "test message")
        assert success is False
        assert "Invalid target format" in message

        # Test multiple colons
        success, message = send_message(mock_tmux, "session:window:extra", "test message")
        assert success is False
        assert "Invalid target format" in message

        # Test empty session part
        success, message = send_message(mock_tmux, ":window", "test message")
        assert success is False
        assert "Invalid target format" in message

        # Test empty window part
        success, message = send_message(mock_tmux, "session:", "test message")
        assert success is False
        assert "Invalid target format" in message

    def test_send_message_session_not_found(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test handling when target session doesn't exist."""
        # Arrange
        mock_tmux.has_session.return_value = False

        # Act
        success, message = send_message(mock_tmux, "nonexistent:window", "test message")

        # Assert
        assert success is False
        assert "Session 'nonexistent' not found" in message
        mock_tmux.has_session.assert_called_once_with("nonexistent")

    def test_send_message_tmux_failure_with_fallback(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test fallback to script when TMUXManager send_message fails."""
        # Arrange
        mock_tmux.send_message.return_value = False
        target = "test-session:window"
        message = "test message"

        with patch("pathlib.Path.exists") as mock_exists, patch("subprocess.run") as mock_run:
            mock_exists.return_value = True
            mock_run.return_value = Mock(returncode=0, stderr="")

            # Act
            success, result_message = send_message(mock_tmux, target, message)

        # Assert
        assert success is True
        assert "via fallback method" in result_message
        mock_run.assert_called_once()

    def test_send_message_complete_failure(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test complete failure when both primary and fallback methods fail."""
        # Arrange
        mock_tmux.send_message.return_value = False

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            # Act
            success, message = send_message(mock_tmux, "test:window", "test message")

        # Assert
        assert success is False
        assert "no fallback script available" in message

    def test_send_message_fallback_script_failure(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test handling when fallback script also fails."""
        # Arrange
        mock_tmux.send_message.return_value = False

        with patch("pathlib.Path.exists") as mock_exists, patch("subprocess.run") as mock_run:
            mock_exists.return_value = True
            mock_run.return_value = Mock(returncode=1, stderr="Script error")

            # Act
            success, message = send_message(mock_tmux, "test:window", "test message")

        # Assert
        assert success is False
        assert "Fallback send failed" in message
        assert "Script error" in message

    def test_send_message_timeout_exception(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test handling of timeout exceptions."""
        # Arrange
        import subprocess

        mock_tmux.send_message.return_value = False

        with patch("pathlib.Path.exists") as mock_exists, patch("subprocess.run") as mock_run:
            mock_exists.return_value = True
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

            # Act
            success, message = send_message(mock_tmux, "test:window", "test message")

        # Assert
        assert success is False
        assert "Timeout sending message" in message

    def test_send_message_general_exception(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test handling of general exceptions."""
        # Arrange
        mock_tmux.has_session.side_effect = Exception("Unexpected error")

        # Act
        success, message = send_message(mock_tmux, "test:window", "test message")

        # Assert
        assert success is False
        assert "Error sending message" in message
        assert "Unexpected error" in message


class TestBroadcastMessage:
    """Test broadcast_message function with comprehensive scenarios."""

    @pytest.fixture
    def mock_tmux(self):
        """Create a mock TMUXManager for testing."""
        mock = Mock(spec=TMUXManager)
        mock.has_session.return_value = True
        mock.list_windows.return_value = [
            {"name": "developer", "index": "1"},
            {"name": "qa", "index": "2"},
            {"name": "pm", "index": "3"},
        ]
        return mock

    @pytest.fixture
    def mock_send_message(self):
        """Mock the send_message function for broadcast testing."""
        with patch("tmux_orchestrator.core.communication.broadcast_message.send_message") as mock:
            mock.return_value = (True, "Message sent")
            yield mock

    def test_broadcast_message_success_all_agents(
        self, mock_tmux: Mock, mock_send_message: Mock, test_uuid: str
    ) -> None:
        """Test successful broadcast to all agents in session."""
        # Arrange
        session = "test-session"
        message = "Team meeting in 5 minutes!"

        # Act
        start_time = time.time()
        success, result_message = broadcast_message(mock_tmux, session, message)
        execution_time = time.time() - start_time

        # Assert
        assert success is True
        assert "Message broadcast to 3 agents" in result_message
        assert execution_time < 1.0, f"broadcast_message took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

        # Verify all windows were targeted
        expected_calls = [
            call(mock_tmux, "test-session:1", message),
            call(mock_tmux, "test-session:2", message),
            call(mock_tmux, "test-session:3", message),
        ]
        mock_send_message.assert_has_calls(expected_calls, any_order=True)

    def test_broadcast_message_with_agent_types_filter(
        self, mock_tmux: Mock, mock_send_message: Mock, test_uuid: str
    ) -> None:
        """Test broadcast with agent type filtering."""
        # Arrange
        session = "test-session"
        message = "Developer meeting!"
        agent_types = ["developer", "qa"]

        # Act
        success, result_message = broadcast_message(mock_tmux, session, message, agent_types=agent_types)

        # Assert
        assert success is True
        assert "Message broadcast to 2 agents" in result_message

        # Verify only matching agent types were targeted
        expected_calls = [
            call(mock_tmux, "test-session:1", message),  # developer
            call(mock_tmux, "test-session:2", message),  # qa
        ]
        mock_send_message.assert_has_calls(expected_calls, any_order=True)
        assert mock_send_message.call_count == 2

    def test_broadcast_message_with_exclude_windows(
        self, mock_tmux: Mock, mock_send_message: Mock, test_uuid: str
    ) -> None:
        """Test broadcast with window exclusion."""
        # Arrange
        session = "test-session"
        message = "All hands meeting!"
        exclude_windows = ["pm", "3"]  # Exclude by name and index

        # Act
        success, result_message = broadcast_message(mock_tmux, session, message, exclude_windows=exclude_windows)

        # Assert
        assert success is True
        assert "Message broadcast to 2 agents" in result_message

        # Verify excluded windows were not targeted
        expected_calls = [
            call(mock_tmux, "test-session:1", message),  # developer
            call(mock_tmux, "test-session:2", message),  # qa
        ]
        mock_send_message.assert_has_calls(expected_calls, any_order=True)
        assert mock_send_message.call_count == 2

    def test_broadcast_message_invalid_inputs(self, mock_tmux: Mock, mock_send_message: Mock, test_uuid: str) -> None:
        """Test broadcast_message with invalid input parameters."""
        # Test empty session
        success, message = broadcast_message(mock_tmux, "", "test message")
        assert success is False
        assert "required" in message

        # Test empty message
        success, message = broadcast_message(mock_tmux, "session", "")
        assert success is False
        assert "required" in message

        # Test None session
        success, message = broadcast_message(mock_tmux, None, "test message")
        assert success is False
        assert "required" in message

        # Test None message
        success, message = broadcast_message(mock_tmux, "session", None)
        assert success is False
        assert "required" in message

    def test_broadcast_message_session_not_found(
        self, mock_tmux: Mock, mock_send_message: Mock, test_uuid: str
    ) -> None:
        """Test handling when target session doesn't exist."""
        # Arrange
        mock_tmux.has_session.return_value = False

        # Act
        success, message = broadcast_message(mock_tmux, "nonexistent", "test message")

        # Assert
        assert success is False
        assert "Session 'nonexistent' not found" in message
        mock_tmux.has_session.assert_called_once_with("nonexistent")
        mock_send_message.assert_not_called()

    def test_broadcast_message_no_windows(self, mock_tmux: Mock, mock_send_message: Mock, test_uuid: str) -> None:
        """Test handling when session has no windows."""
        # Arrange
        mock_tmux.list_windows.return_value = []

        # Act
        success, message = broadcast_message(mock_tmux, "empty-session", "test message")

        # Assert
        assert success is False
        assert "No windows found" in message
        mock_send_message.assert_not_called()

    def test_broadcast_message_no_matching_windows(
        self, mock_tmux: Mock, mock_send_message: Mock, test_uuid: str
    ) -> None:
        """Test handling when no windows match the criteria."""
        # Arrange
        agent_types = ["nonexistent-type"]

        # Act
        success, message = broadcast_message(mock_tmux, "test-session", "test message", agent_types=agent_types)

        # Assert
        assert success is False
        assert "No target windows found matching criteria" in message
        mock_send_message.assert_not_called()

    def test_broadcast_message_partial_success(self, mock_tmux: Mock, mock_send_message: Mock, test_uuid: str) -> None:
        """Test handling of partial broadcast success."""
        # Arrange
        mock_send_message.side_effect = [
            (True, "Success"),
            (False, "Failed to send"),
            (True, "Success"),
        ]

        # Act
        success, message = broadcast_message(mock_tmux, "test-session", "test message")

        # Assert
        assert success is False
        assert "Partial success: 2/3 agents reached" in message
        assert "Failures:" in message

    def test_broadcast_message_complete_failure(self, mock_tmux: Mock, mock_send_message: Mock, test_uuid: str) -> None:
        """Test handling when all message sends fail."""
        # Arrange
        mock_send_message.return_value = (False, "Send failed")

        # Act
        success, message = broadcast_message(mock_tmux, "test-session", "test message")

        # Assert
        assert success is False
        assert "Broadcast failed: No agents reached" in message

    def test_broadcast_message_exception_handling(
        self, mock_tmux: Mock, mock_send_message: Mock, test_uuid: str
    ) -> None:
        """Test proper exception handling during broadcast."""
        # Arrange
        mock_tmux.list_windows.side_effect = Exception("Unexpected error")

        # Act
        success, message = broadcast_message(mock_tmux, "test-session", "test message")

        # Assert
        assert success is False
        assert "Error broadcasting message" in message
        assert "Unexpected error" in message

    def test_broadcast_message_many_failures_summary(
        self, mock_tmux: Mock, mock_send_message: Mock, test_uuid: str
    ) -> None:
        """Test failure summary truncation for many failures."""
        # Arrange - Add more windows to test failure truncation
        mock_tmux.list_windows.return_value = [
            {"name": f"agent-{i}", "index": str(i)}
            for i in range(1, 11)  # 10 windows
        ]
        mock_send_message.return_value = (False, "Send failed")

        # Act
        success, message = broadcast_message(mock_tmux, "test-session", "test message")

        # Assert
        assert success is False
        assert "and 7 more" in message  # Should truncate to first 3 failures + "and X more"


class TestCommunicationPerformance:
    """Performance tests for communication functions."""

    @pytest.fixture
    def mock_tmux(self):
        """Create a mock TMUXManager for performance testing."""
        mock = Mock(spec=TMUXManager)
        mock.has_session.return_value = True
        mock.send_message.return_value = True
        mock.list_windows.return_value = [
            {"name": f"agent-{i}", "index": str(i)}
            for i in range(1, 21)  # 20 agents
        ]
        return mock

    def test_send_message_performance_batch(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test send_message performance for batch operations."""
        targets = [f"session:window-{i}" for i in range(1, 51)]  # 50 targets
        message = "Performance test message"

        start_time = time.time()
        for target in targets:
            success, result_message = send_message(mock_tmux, target, message)
            assert success is True, f"Message send failed for {target} - Test ID: {test_uuid}"

        total_time = time.time() - start_time
        avg_time_per_message = total_time / len(targets)

        assert total_time < 5.0, f"Batch send took {total_time:.3f}s (>5s limit) - Test ID: {test_uuid}"
        assert (
            avg_time_per_message < 0.1
        ), f"Average send time {avg_time_per_message:.3f}s too slow - Test ID: {test_uuid}"

    def test_broadcast_message_performance_large_team(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test broadcast_message performance with large team (20 agents)."""
        with patch("tmux_orchestrator.core.communication.broadcast_message.send_message") as mock_send:
            mock_send.return_value = (True, "Message sent")

            start_time = time.time()
            success, message = broadcast_message(mock_tmux, "large-session", "Performance test broadcast")
            execution_time = time.time() - start_time

            assert success is True
            assert (
                execution_time < 2.0
            ), f"Large broadcast took {execution_time:.3f}s (>2s limit) - Test ID: {test_uuid}"
            assert mock_send.call_count == 20


class TestCommunicationEdgeCases:
    """Edge case tests for communication functions."""

    @pytest.fixture
    def mock_tmux(self):
        """Create a mock TMUXManager for edge case testing."""
        mock = Mock(spec=TMUXManager)
        mock.has_session.return_value = True
        mock.send_message.return_value = True
        return mock

    def test_send_message_unicode_content(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test message sending with unicode characters."""
        unicode_message = "Hello 世界! 🚀 Testing émojis and special chars: àáâãäå"

        success, result_message = send_message(mock_tmux, "test:window", unicode_message)

        assert success is True
        mock_tmux.send_message.assert_called_once_with("test:window", unicode_message, delay=0.5)

    def test_send_message_very_long_content(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test message sending with very long content."""
        long_message = "This is a very long message. " * 200  # ~6000 chars

        success, result_message = send_message(mock_tmux, "test:window", long_message)

        assert success is True
        mock_tmux.send_message.assert_called_once_with("test:window", long_message, delay=0.5)

    def test_broadcast_message_mixed_window_formats(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test broadcast with mixed window name/index formats."""
        mock_tmux.list_windows.return_value = [
            {"name": "developer", "index": "1"},
            {"name": "", "index": "2"},  # Window with no name
            {"name": "qa-engineer", "index": "window-3"},  # Non-numeric index
        ]

        with patch("tmux_orchestrator.core.communication.broadcast_message.send_message") as mock_send:
            mock_send.return_value = (True, "Message sent")

            success, message = broadcast_message(mock_tmux, "test-session", "test message")

            assert success is True
            assert mock_send.call_count == 3

    def test_broadcast_message_case_insensitive_agent_filtering(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test that agent type filtering is case-insensitive."""
        mock_tmux.list_windows.return_value = [
            {"name": "Developer", "index": "1"},
            {"name": "QA-Engineer", "index": "2"},
            {"name": "pm", "index": "3"},
        ]

        with patch("tmux_orchestrator.core.communication.broadcast_message.send_message") as mock_send:
            mock_send.return_value = (True, "Message sent")

            # Use lowercase agent types to test case-insensitive matching
            success, message = broadcast_message(
                mock_tmux, "test-session", "test message", agent_types=["developer", "qa"]
            )

            assert success is True
            assert mock_send.call_count == 2  # Should match "Developer" and "QA-Engineer"

    def test_send_message_special_target_formats(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test send_message with various valid target formats."""
        valid_targets = [
            "session-name:window-name",
            "session_name:window_name",
            "session.name:window.name",
            "session123:456",
            "my-project-session:backend-dev",
        ]

        for target in valid_targets:
            success, message = send_message(mock_tmux, target, "test message")
            assert success is True, f"Failed with valid target format: {target} - Test ID: {test_uuid}"

    def test_broadcast_message_empty_lists(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test broadcast with empty agent_types and exclude_windows lists."""
        mock_tmux.list_windows.return_value = [
            {"name": "developer", "index": "1"},
            {"name": "qa", "index": "2"},
        ]

        with patch("tmux_orchestrator.core.communication.broadcast_message.send_message") as mock_send:
            mock_send.return_value = (True, "Message sent")

            # Test with empty lists
            success, message = broadcast_message(
                mock_tmux, "test-session", "test message", agent_types=[], exclude_windows=[]
            )

            assert success is True
            assert mock_send.call_count == 2  # Should target all windows
