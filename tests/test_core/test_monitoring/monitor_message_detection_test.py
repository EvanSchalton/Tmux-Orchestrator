#!/usr/bin/env python3
"""Test monitor message detection for cases that were missed."""

from pathlib import Path

import pytest

from tmux_orchestrator.core.monitor_helpers import AgentState, detect_agent_state, has_unsubmitted_message

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "monitor_states"


def test_agent_test_message_not_submitted() -> None:
    """Test detection of 'Another test message' that wasn't auto-submitted."""
    fixture_path = FIXTURES_DIR / "message_queued" / "agent_test_message_not_submitted.txt"
    content = fixture_path.read_text()

    # Should detect unsubmitted message
    assert has_unsubmitted_message(content), "Failed to detect 'Another test message' as unsubmitted"

    # Should detect state as MESSAGE_QUEUED
    state = detect_agent_state(content)
    assert state == AgentState.MESSAGE_QUEUED, f"Expected MESSAGE_QUEUED but got {state}"


def get_message_queued_fixtures():
    """Get all message_queued fixture files."""
    message_queued_dir = FIXTURES_DIR / "message_queued"
    return list(message_queued_dir.glob("*.txt"))


@pytest.mark.parametrize("fixture_file", get_message_queued_fixtures())
def test_all_message_queued_fixtures(fixture_file) -> None:
    """Test all message_queued fixtures are detected correctly."""
    content = fixture_file.read_text()

    # Should detect unsubmitted message
    has_msg = has_unsubmitted_message(content)
    assert has_msg, f"{fixture_file.name}: Failed to detect unsubmitted message"

    # Should detect state as MESSAGE_QUEUED
    state = detect_agent_state(content)
    assert state == AgentState.MESSAGE_QUEUED, f"{fixture_file.name}: Expected MESSAGE_QUEUED but got {state}"


if __name__ == "__main__":
    # Run pytest when executed directly
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
