"""Tests for handoff_work business logic."""

from unittest.mock import Mock

import pytest

from tmux_orchestrator.server.tools.handoff_work import HandoffWorkRequest, handoff_work
from tmux_orchestrator.utils.tmux import TMUXManager


class TestHandoffWork:
    """Test cases for handoff_work function."""

    def test_handoff_work_empty_from_agent(self) -> None:
        """Test handoff_work with empty from_agent returns error."""
        tmux = Mock(spec=TMUXManager)
        request = HandoffWorkRequest(
            from_agent="", to_agent="dev:1", work_description="Complete authentication feature"
        )

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "From agent cannot be empty" in result.error_message
        assert result.from_agent == ""
        assert result.to_agent == "dev:1"  # to_agent is still valid, only from_agent is invalid

    def test_handoff_work_empty_to_agent(self) -> None:
        """Test handoff_work with empty to_agent returns error."""
        tmux = Mock(spec=TMUXManager)
        request = HandoffWorkRequest(
            from_agent="dev:0", to_agent="", work_description="Complete authentication feature"
        )

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "To agent cannot be empty" in result.error_message

    def test_handoff_work_empty_work_description(self) -> None:
        """Test handoff_work with empty work_description returns error."""
        tmux = Mock(spec=TMUXManager)
        request = HandoffWorkRequest(from_agent="dev:0", to_agent="dev:1", work_description="")

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Work description cannot be empty" in result.error_message

    def test_handoff_work_invalid_from_agent_format(self) -> None:
        """Test handoff_work with invalid from_agent format returns error."""
        tmux = Mock(spec=TMUXManager)
        request = HandoffWorkRequest(from_agent="invalid-format", to_agent="dev:1", work_description="Complete feature")

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "From agent must be in format 'session:window'" in result.error_message

    def test_handoff_work_invalid_to_agent_format(self) -> None:
        """Test handoff_work with invalid to_agent format returns error."""
        tmux = Mock(spec=TMUXManager)
        request = HandoffWorkRequest(from_agent="dev:0", to_agent="invalid-format", work_description="Complete feature")

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "To agent must be in format 'session:window'" in result.error_message

    def test_handoff_work_same_agent(self) -> None:
        """Test handoff_work with same from and to agent returns error."""
        tmux = Mock(spec=TMUXManager)
        request = HandoffWorkRequest(from_agent="dev:0", to_agent="dev:0", work_description="Complete feature")

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Cannot handoff work to the same agent" in result.error_message

    def test_handoff_work_from_agent_not_found(self) -> None:
        """Test handoff_work when from_agent session/window doesn't exist."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = None  # Session/window not found

        request = HandoffWorkRequest(from_agent="nonexistent:0", to_agent="dev:1", work_description="Complete feature")

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "From agent 'nonexistent:0' not found or not accessible" in result.error_message

    def test_handoff_work_to_agent_not_found(self) -> None:
        """Test handoff_work when to_agent session/window doesn't exist."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.side_effect = ["Context from source", None]  # First call succeeds, second fails

        request = HandoffWorkRequest(from_agent="dev:0", to_agent="nonexistent:1", work_description="Complete feature")

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "To agent 'nonexistent:1' not found or not accessible" in result.error_message

    def test_handoff_work_successful_basic_handoff(self) -> None:
        """Test successful basic work handoff without context preservation."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Mock pane content"
        tmux.send_keys.return_value = True

        request = HandoffWorkRequest(
            from_agent="dev:0",
            to_agent="dev:1",
            work_description="Complete authentication feature",
            preserve_context=False,
        )

        result = handoff_work(tmux, request)

        assert result.success
        assert result.from_agent == "dev:0"
        assert result.to_agent == "dev:1"
        assert result.work_description == "Complete authentication feature"
        assert not result.context_preserved
        assert result.error_message is None

        # Verify handoff message was sent
        tmux.send_keys.assert_called_once()
        call_args = tmux.send_keys.call_args[0]
        assert call_args[0] == "dev:1"  # Target agent
        assert "WORK HANDOFF" in call_args[1]  # Message contains handoff marker

    def test_handoff_work_successful_with_context_preservation(self) -> None:
        """Test successful work handoff with context preservation."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Source context data\nMultiple lines\nOf work context"
        tmux.send_keys.return_value = True

        request = HandoffWorkRequest(
            from_agent="dev:0",
            to_agent="qa:0",
            work_description="Test the completed authentication feature",
            preserve_context=True,
            priority="high",
            deadline="2025-08-10",
        )

        result = handoff_work(tmux, request)

        assert result.success
        assert result.context_preserved
        assert result.priority == "high"
        assert result.deadline == "2025-08-10"

        # Verify handoff message includes context
        tmux.send_keys.assert_called_once()
        call_args = tmux.send_keys.call_args[0]
        message = call_args[1]
        assert "CONTEXT:" in message
        assert "Source context data" in message
        assert "Priority: high" in message
        assert "Deadline: 2025-08-10" in message

    def test_handoff_work_send_keys_failure(self) -> None:
        """Test handoff_work when sending handoff message fails."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Context"
        tmux.send_keys.return_value = False  # Send keys fails

        request = HandoffWorkRequest(from_agent="dev:0", to_agent="dev:1", work_description="Complete feature")

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Failed to send handoff message to dev:1" in result.error_message

    def test_handoff_work_with_additional_notes(self) -> None:
        """Test handoff_work includes additional notes in message."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Context"
        tmux.send_keys.return_value = True

        request = HandoffWorkRequest(
            from_agent="dev:0",
            to_agent="reviewer:0",
            work_description="Review authentication code",
            notes="Please pay special attention to security vulnerabilities and test coverage",
        )

        result = handoff_work(tmux, request)

        assert result.success
        assert result.notes == "Please pay special attention to security vulnerabilities and test coverage"

        # Verify notes are included in message
        call_args = tmux.send_keys.call_args[0]
        message = call_args[1]
        assert "NOTES:" in message
        assert "security vulnerabilities" in message

    def test_handoff_work_long_work_description(self) -> None:
        """Test handoff_work validates work description length."""
        tmux = Mock(spec=TMUXManager)
        request = HandoffWorkRequest(
            from_agent="dev:0", to_agent="dev:1", work_description="x" * 2001  # Exceeds 2000 char limit
        )

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Work description must be 2000 characters or less" in result.error_message

    def test_handoff_work_long_notes(self) -> None:
        """Test handoff_work validates notes length."""
        tmux = Mock(spec=TMUXManager)
        request = HandoffWorkRequest(
            from_agent="dev:0",
            to_agent="dev:1",
            work_description="Complete feature",
            notes="x" * 1001,  # Exceeds 1000 char limit
        )

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Notes must be 1000 characters or less" in result.error_message

    def test_handoff_work_invalid_priority(self) -> None:
        """Test handoff_work validates priority values."""
        tmux = Mock(spec=TMUXManager)
        request = HandoffWorkRequest(
            from_agent="dev:0", to_agent="dev:1", work_description="Complete feature", priority="invalid"
        )

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Priority must be one of: low, medium, high, critical" in result.error_message

    def test_handoff_work_capture_pane_exception(self) -> None:
        """Test handoff_work handles capture_pane exceptions gracefully."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.side_effect = Exception("Connection error")

        request = HandoffWorkRequest(from_agent="dev:0", to_agent="dev:1", work_description="Complete feature")

        result = handoff_work(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Unexpected error during work handoff" in result.error_message

    def test_handoff_work_context_truncation(self) -> None:
        """Test handoff_work truncates very long context appropriately."""
        tmux = Mock(spec=TMUXManager)
        long_context = "x" * 5000  # Very long context
        tmux.capture_pane.return_value = long_context
        tmux.send_keys.return_value = True

        request = HandoffWorkRequest(
            from_agent="dev:0", to_agent="dev:1", work_description="Complete feature", preserve_context=True
        )

        result = handoff_work(tmux, request)

        assert result.success
        assert result.context_preserved

        # Verify context was truncated
        call_args = tmux.send_keys.call_args[0]
        message = call_args[1]
        assert len(message) < 6000  # Should be shorter than original context

    @pytest.mark.parametrize(
        "priority",
        ["low", "medium", "high", "critical"],
    )
    def test_handoff_work_all_valid_priorities(self, priority: str) -> None:
        """Test handoff_work accepts all valid priority levels."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Context"
        tmux.send_keys.return_value = True

        request = HandoffWorkRequest(
            from_agent="dev:0", to_agent="dev:1", work_description="Complete feature", priority=priority
        )

        result = handoff_work(tmux, request)

        assert result.success
        assert result.priority == priority

    def test_handoff_work_message_formatting(self) -> None:
        """Test handoff_work message is properly formatted with all components."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Previous work context"
        tmux.send_keys.return_value = True

        request = HandoffWorkRequest(
            from_agent="dev:0",
            to_agent="qa:0",
            work_description="Test authentication module thoroughly",
            preserve_context=True,
            priority="high",
            deadline="2025-08-15",
            notes="Focus on edge cases and security",
        )

        result = handoff_work(tmux, request)

        assert result.success

        # Verify message structure
        call_args = tmux.send_keys.call_args[0]
        message = call_args[1]

        # Check all required sections are present
        assert "WORK HANDOFF FROM: dev:0" in message
        assert "DESCRIPTION:" in message
        assert "Test authentication module thoroughly" in message
        assert "Priority: high" in message
        assert "Deadline: 2025-08-15" in message
        assert "CONTEXT:" in message
        assert "Previous work context" in message
        assert "NOTES:" in message
        assert "Focus on edge cases and security" in message

    def test_handoff_work_cross_session_handoff(self) -> None:
        """Test handoff_work between agents in different sessions."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Cross-session context"
        tmux.send_keys.return_value = True

        request = HandoffWorkRequest(
            from_agent="frontend:0",
            to_agent="backend:1",
            work_description="Implement API endpoints for frontend integration",
        )

        result = handoff_work(tmux, request)

        assert result.success
        assert result.from_agent == "frontend:0"
        assert result.to_agent == "backend:1"

        # Verify message sent to correct target
        call_args = tmux.send_keys.call_args[0]
        assert call_args[0] == "backend:1"

    def test_handoff_work_metadata_tracking(self) -> None:
        """Test handoff_work tracks comprehensive metadata."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Context"
        tmux.send_keys.return_value = True

        request = HandoffWorkRequest(
            from_agent="dev:0",
            to_agent="qa:0",
            work_description="Complete testing phase",
            preserve_context=True,
            priority="medium",
            deadline="2025-08-12",
        )

        result = handoff_work(tmux, request)

        assert result.success
        assert result.handoff_metadata is not None

        metadata = result.handoff_metadata
        assert "handoff_id" in metadata
        assert "timestamp" in metadata
        assert "from_agent" in metadata
        assert "to_agent" in metadata
        assert metadata["from_agent"] == "dev:0"
        assert metadata["to_agent"] == "qa:0"
        assert metadata["priority"] == "medium"
        assert metadata["context_preserved"] is True
