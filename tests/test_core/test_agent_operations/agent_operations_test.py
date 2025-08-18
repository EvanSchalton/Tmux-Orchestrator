"""Unit tests for core/agent_operations module.

This module tests all agent operation functions including spawn_agent and restart_agent.
Focused on validating business logic with mocked TMUXManager for fast execution.
"""

import time
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.agent_operations.spawn_agent import _send_agent_message, spawn_agent
from tmux_orchestrator.utils.tmux import TMUXManager


class TestSpawnAgent:
    """Test spawn_agent function with comprehensive scenarios."""

    @pytest.fixture
    def mock_tmux(self):
        """Create a mock TMUXManager for testing."""
        mock = Mock(spec=TMUXManager)
        mock.has_session.return_value = True
        mock.create_session.return_value = True
        mock.create_window.return_value = True
        mock.send_keys.return_value = True
        mock.press_enter.return_value = True
        mock.send_message.return_value = True
        return mock

    def test_spawn_agent_success_existing_session(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test spawning agent in existing session - happy path."""
        # Arrange
        agent_type = "developer"
        session = "test-session"
        window = "dev-window"

        # Act
        start_time = time.time()
        success, message = spawn_agent(mock_tmux, agent_type, session, window)
        execution_time = time.time() - start_time

        # Assert
        assert success is True
        assert "spawned successfully" in message
        assert execution_time < 1.0, f"spawn_agent took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

        # Verify TMUXManager calls
        mock_tmux.has_session.assert_called_once_with(session)
        mock_tmux.create_window.assert_called_once_with(session, window, None)
        mock_tmux.send_keys.assert_called_once_with(f"{session}:{window}", "claude --dangerously-skip-permissions")
        mock_tmux.press_enter.assert_called_once_with(f"{session}:{window}")

    def test_spawn_agent_success_new_session(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test spawning agent with new session creation."""
        # Arrange
        mock_tmux.has_session.return_value = False
        agent_type = "qa"
        session = "new-session"

        # Act
        start_time = time.time()
        success, message = spawn_agent(mock_tmux, agent_type, session)
        execution_time = time.time() - start_time

        # Assert
        assert success is True
        assert "spawned successfully" in message
        assert execution_time < 1.0, f"spawn_agent took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

        # Verify session creation
        mock_tmux.has_session.assert_called_once_with(session)
        mock_tmux.create_session.assert_called_once_with(session, agent_type, None)

    def test_spawn_agent_with_briefing(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test spawning agent with initial briefing message."""
        # Arrange
        agent_type = "pm"
        session = "test-session"
        briefing = "You are the project manager for this team."

        # Act
        success, message = spawn_agent(mock_tmux, agent_type, session, briefing=briefing)

        # Assert
        assert success is True
        assert "spawned successfully" in message

        # Verify briefing was sent
        expected_target = f"{session}:{agent_type}"
        mock_tmux.send_message.assert_called_with(expected_target, briefing)

    def test_spawn_agent_with_context_file(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test spawning agent with context file loading."""
        # Arrange
        agent_type = "developer"
        session = "test-session"
        context_content = "This is the project context..."

        with patch("pathlib.Path.exists") as mock_exists, patch("pathlib.Path.read_text") as mock_read:
            mock_exists.return_value = True
            mock_read.return_value = context_content

            # Act
            success, message = spawn_agent(mock_tmux, agent_type, session, context_file="/path/to/context.md")

        # Assert
        assert success is True
        assert "spawned successfully" in message

        # Verify context was loaded
        expected_target = f"{session}:{agent_type}"
        context_calls = [
            call for call in mock_tmux.send_message.call_args_list if f"Context: {context_content}" in str(call)
        ]
        assert len(context_calls) > 0, "Context should have been sent to agent"

    def test_spawn_agent_with_start_directory(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test spawning agent with specific starting directory."""
        # Arrange
        agent_type = "devops"
        session = "test-session"
        start_dir = "/workspaces/project"

        # Act
        success, message = spawn_agent(mock_tmux, agent_type, session, start_directory=start_dir)

        # Assert
        assert success is True
        assert "spawned successfully" in message

        # Verify start directory was passed
        mock_tmux.create_window.assert_called_once_with(session, agent_type, start_dir)

    def test_spawn_agent_invalid_inputs(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test spawn_agent with invalid input parameters."""
        # Test missing agent_type
        success, message = spawn_agent(mock_tmux, "", "session")
        assert success is False
        assert "required" in message

        # Test missing session
        success, message = spawn_agent(mock_tmux, "developer", "")
        assert success is False
        assert "required" in message

        # Test None values
        success, message = spawn_agent(mock_tmux, None, "session")
        assert success is False
        assert "required" in message

    def test_spawn_agent_session_creation_failure(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test handling of session creation failures."""
        # Arrange
        mock_tmux.has_session.return_value = False
        mock_tmux.create_session.return_value = False

        # Act
        success, message = spawn_agent(mock_tmux, "developer", "test-session")

        # Assert
        assert success is False
        assert "Failed to create session" in message

    def test_spawn_agent_window_creation_failure(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test handling of window creation failures."""
        # Arrange
        mock_tmux.create_window.return_value = False

        # Act
        success, message = spawn_agent(mock_tmux, "developer", "test-session", "test-window")

        # Assert
        assert success is False
        assert "Failed to create window" in message

    def test_spawn_agent_claude_start_failure(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test handling of Claude startup failures."""
        # Arrange
        mock_tmux.send_keys.return_value = False

        # Act
        success, message = spawn_agent(mock_tmux, "developer", "test-session")

        # Assert
        assert success is False
        assert "Failed to start Claude" in message

    def test_spawn_agent_press_enter_failure(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test handling of command submission failures."""
        # Arrange
        mock_tmux.press_enter.return_value = False

        # Act
        success, message = spawn_agent(mock_tmux, "developer", "test-session")

        # Assert
        assert success is False
        assert "Failed to submit Claude command" in message

    def test_spawn_agent_exception_handling(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test proper exception handling during agent spawn."""
        # Arrange
        mock_tmux.send_keys.side_effect = Exception("Unexpected error")

        # Act
        success, message = spawn_agent(mock_tmux, "developer", "test-session")

        # Assert
        assert success is False
        assert "Error spawning agent" in message
        assert "Unexpected error" in message

    def test_spawn_agent_context_file_not_found(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test behavior when context file doesn't exist."""
        # Arrange
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            # Act
            success, message = spawn_agent(
                mock_tmux, "developer", "test-session", context_file="/nonexistent/context.md"
            )

        # Assert - Should still succeed, just skip context loading
        assert success is True
        assert "spawned successfully" in message


class TestSendAgentMessage:
    """Test _send_agent_message helper function."""

    @pytest.fixture
    def mock_tmux(self):
        """Create a mock TMUXManager for testing."""
        mock = Mock(spec=TMUXManager)
        mock.send_message.return_value = True
        return mock

    def test_send_agent_message_success(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test successful message sending via TMUXManager."""
        # Arrange
        target = "session:window"
        message = "Test message"

        # Act
        start_time = time.time()
        result = _send_agent_message(mock_tmux, target, message)
        execution_time = time.time() - start_time

        # Assert
        assert result is True
        assert (
            execution_time < 1.0
        ), f"_send_agent_message took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"
        mock_tmux.send_message.assert_called_once_with(target, message)

    def test_send_agent_message_tmux_failure_with_fallback(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test fallback to script when TMUXManager fails."""
        # Arrange
        mock_tmux.send_message.side_effect = Exception("TMUXManager failed")
        target = "session:window"
        message = "Test message"

        with patch("pathlib.Path.exists") as mock_exists, patch("subprocess.run") as mock_run:
            mock_exists.return_value = True
            mock_run.return_value = Mock(returncode=0)

            # Act
            result = _send_agent_message(mock_tmux, target, message)

        # Assert
        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert target in call_args
        assert message in call_args

    def test_send_agent_message_complete_failure(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test complete failure when both methods fail."""
        # Arrange
        mock_tmux.send_message.side_effect = Exception("TMUXManager failed")

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            # Act
            result = _send_agent_message(mock_tmux, "session:window", "Test message")

        # Assert
        assert result is False

    def test_send_agent_message_script_failure(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test handling of script execution failures."""
        # Arrange
        mock_tmux.send_message.side_effect = Exception("TMUXManager failed")

        with patch("pathlib.Path.exists") as mock_exists, patch("subprocess.run") as mock_run:
            mock_exists.return_value = True
            mock_run.return_value = Mock(returncode=1)  # Script failed

            # Act
            result = _send_agent_message(mock_tmux, "session:window", "Test message")

        # Assert
        assert result is False

    def test_send_agent_message_script_exception(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test handling of script execution exceptions."""
        # Arrange
        mock_tmux.send_message.side_effect = Exception("TMUXManager failed")

        with patch("pathlib.Path.exists") as mock_exists, patch("subprocess.run") as mock_run:
            mock_exists.return_value = True
            mock_run.side_effect = Exception("Script execution failed")

            # Act
            result = _send_agent_message(mock_tmux, "session:window", "Test message")

        # Assert
        assert result is False


class TestAgentOperationsPerformance:
    """Performance tests for agent operations."""

    @pytest.fixture
    def mock_tmux(self):
        """Create a mock TMUXManager for performance testing."""
        mock = Mock(spec=TMUXManager)
        mock.has_session.return_value = True
        mock.create_window.return_value = True
        mock.send_keys.return_value = True
        mock.press_enter.return_value = True
        mock.send_message.return_value = True
        return mock

    def test_spawn_agent_performance_under_load(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test spawn_agent performance under concurrent load simulation."""
        import queue
        import threading

        results = queue.Queue()

        def spawn_worker():
            start_time = time.time()
            success, message = spawn_agent(mock_tmux, "worker", "test-session")
            execution_time = time.time() - start_time
            results.put((success, execution_time))

        # Simulate 10 concurrent spawns
        threads = []
        for i in range(10):
            thread = threading.Thread(target=spawn_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Collect results
        execution_times = []
        while not results.empty():
            success, exec_time = results.get()
            assert success is True, f"Spawn failed under load - Test ID: {test_uuid}"
            execution_times.append(exec_time)

        # Verify all executions were fast
        max_time = max(execution_times)
        avg_time = sum(execution_times) / len(execution_times)

        assert max_time < 1.0, f"Max execution time {max_time:.3f}s exceeded 1s limit - Test ID: {test_uuid}"
        assert avg_time < 0.5, f"Average execution time {avg_time:.3f}s too slow - Test ID: {test_uuid}"

    def test_send_agent_message_batch_performance(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test message sending performance for batch operations."""
        target = "session:window"
        messages = [f"Message {i}" for i in range(50)]

        start_time = time.time()
        for message in messages:
            result = _send_agent_message(mock_tmux, target, message)
            assert result is True, f"Message sending failed in batch - Test ID: {test_uuid}"

        total_time = time.time() - start_time
        avg_time_per_message = total_time / len(messages)

        assert total_time < 5.0, f"Batch messaging took {total_time:.3f}s (>5s limit) - Test ID: {test_uuid}"
        assert (
            avg_time_per_message < 0.1
        ), f"Average message time {avg_time_per_message:.3f}s too slow - Test ID: {test_uuid}"


class TestAgentOperationsEdgeCases:
    """Edge case tests for agent operations."""

    @pytest.fixture
    def mock_tmux(self):
        """Create a mock TMUXManager for edge case testing."""
        mock = Mock(spec=TMUXManager)
        mock.has_session.return_value = True
        mock.create_window.return_value = True
        mock.send_keys.return_value = True
        mock.press_enter.return_value = True
        mock.send_message.return_value = True
        return mock

    def test_spawn_agent_with_special_characters(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test agent spawning with special characters in names."""
        special_chars = ["test-agent", "test_agent", "test.agent", "test@agent"]

        for agent_type in special_chars:
            success, message = spawn_agent(mock_tmux, agent_type, "test-session")
            assert success is True, f"Failed with agent type '{agent_type}' - Test ID: {test_uuid}"

    def test_spawn_agent_with_unicode_briefing(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test agent spawning with unicode characters in briefing."""
        unicode_briefing = "你好，世界！🚀 This is a test briefing with émojis and accénts."

        success, message = spawn_agent(mock_tmux, "developer", "test-session", briefing=unicode_briefing)

        assert success is True
        # Verify unicode briefing was sent
        mock_tmux.send_message.assert_called_with("test-session:developer", unicode_briefing)

    def test_spawn_agent_with_very_long_briefing(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test agent spawning with very long briefing message."""
        long_briefing = "This is a very long briefing message. " * 100  # ~3600 chars

        success, message = spawn_agent(mock_tmux, "developer", "test-session", briefing=long_briefing)

        assert success is True
        mock_tmux.send_message.assert_called_with("test-session:developer", long_briefing)

    def test_spawn_agent_default_window_name(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test that window name defaults to agent_type when not specified."""
        agent_type = "qa-engineer"

        success, message = spawn_agent(mock_tmux, agent_type, "test-session")

        assert success is True
        # Verify window was created with agent_type as name
        mock_tmux.create_window.assert_called_once_with("test-session", agent_type, None)

    def test_spawn_agent_empty_string_inputs(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test spawn_agent behavior with empty string inputs."""
        # Empty agent_type
        success, message = spawn_agent(mock_tmux, "", "test-session")
        assert success is False
        assert "required" in message.lower()

        # Empty session
        success, message = spawn_agent(mock_tmux, "developer", "")
        assert success is False
        assert "required" in message.lower()

        # Empty window name should work (defaults to agent_type)
        success, message = spawn_agent(mock_tmux, "developer", "test-session", window="")
        assert success is True  # Empty window should default to agent_type

    def test_spawn_agent_whitespace_inputs(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test spawn_agent behavior with whitespace-only inputs."""
        # Whitespace agent_type
        success, message = spawn_agent(mock_tmux, "   ", "test-session")
        assert success is False
        assert "required" in message.lower()

        # Whitespace session
        success, message = spawn_agent(mock_tmux, "developer", "   ")
        assert success is False
        assert "required" in message.lower()
