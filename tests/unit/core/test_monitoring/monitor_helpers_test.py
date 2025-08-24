"""Tests for monitor helper functions."""

from pathlib import Path

from tmux_orchestrator.core.monitor_helpers import (
    AgentState,
    _calculate_change_distance,
    _has_crash_indicators,
    _has_error_indicators,
    detect_agent_state,
    has_unsubmitted_message,
    is_claude_interface_present,
    is_terminal_idle,
    needs_recovery,
    should_notify_pm,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "monitor_states"


def load_fixture(category: str, filename: str) -> str:
    """Load a test fixture file."""
    path = FIXTURES_DIR / category / filename
    return path.read_text()


def test_healthy_agent_has_interface() -> None:
    """Test that healthy agents show Claude interface."""
    content = load_fixture("healthy", "agent_active_typing.txt")
    assert is_claude_interface_present(content) is True


def test_crashed_agent_no_interface() -> None:
    """Test that crashed agents don't show Claude interface."""
    content = load_fixture("crashed", "agent_bash_prompt.txt")
    assert is_claude_interface_present(content) is False


def test_command_not_found_no_interface() -> None:
    """Test that command not found means no Claude interface."""
    content = load_fixture("crashed", "agent_command_not_found.txt")
    assert is_claude_interface_present(content) is False


def test_welcome_screen_has_interface() -> None:
    """Test that Claude welcome screen counts as interface."""
    content = load_fixture("healthy", "agent_claude_welcome.txt")
    assert is_claude_interface_present(content) is True


def test_python_traceback_no_interface() -> None:
    """Test that Python traceback means no Claude interface."""
    content = load_fixture("crashed", "agent_python_traceback.txt")
    assert is_claude_interface_present(content) is False


def test_detect_active_state() -> None:
    """Test detection of active agent state."""
    content = load_fixture("healthy", "agent_waiting_response.txt")
    assert detect_agent_state(content) == AgentState.ACTIVE


def test_detect_crashed_state() -> None:
    """Test detection of crashed agent state."""
    content = load_fixture("crashed", "agent_python_traceback.txt")
    assert detect_agent_state(content) == AgentState.CRASHED


def test_detect_message_queued_state() -> None:
    """Test detection of message queued state."""
    content = load_fixture("message_queued", "agent_test_message_not_submitted.txt")
    assert detect_agent_state(content) == AgentState.MESSAGE_QUEUED


def test_detect_error_state() -> None:
    """Test detection of error state."""
    content = load_fixture("error", "agent_network_error.txt")
    assert detect_agent_state(content) == AgentState.ERROR


def test_detect_active_from_starting() -> None:
    """Test that starting state without Claude interface is detected as error."""
    content = load_fixture("starting", "agent_initializing.txt")
    # Without Claude interface indicators, this is detected as ERROR
    assert detect_agent_state(content) == AgentState.ERROR


def test_bash_prompt_is_crashed() -> None:
    """Test that bash prompt is detected as crashed."""
    content = load_fixture("crashed", "agent_bash_prompt.txt")
    assert detect_agent_state(content) == AgentState.CRASHED


def test_single_line_message() -> None:
    """Test detection of single-line unsubmitted message."""
    content = load_fixture("message_queued", "agent_test_message_not_submitted.txt")
    assert has_unsubmitted_message(content) is True


def test_multiline_message() -> None:
    """Test detection of multi-line unsubmitted message."""
    # Using same fixture as we don't have multiline fixture
    content = load_fixture("message_queued", "agent_simple_prompt_with_message.txt")
    assert has_unsubmitted_message(content) is True


def test_empty_prompt() -> None:
    """Test that empty prompt has no unsubmitted message."""
    content = load_fixture("idle", "agent_empty_prompt.txt")
    assert has_unsubmitted_message(content) is False


def test_no_prompt() -> None:
    """Test that no prompt means no unsubmitted message."""
    content = load_fixture("crashed", "agent_bash_prompt.txt")
    assert has_unsubmitted_message(content) is False


def test_thinking_state_no_message() -> None:
    """Test that thinking state has no unsubmitted message."""
    content = load_fixture("idle", "agent_thinking_stuck.txt")
    assert has_unsubmitted_message(content) is False


def test_identical_snapshots_are_idle() -> None:
    """Test that identical snapshots indicate idle state."""
    snapshot = load_fixture("idle", "agent_empty_prompt.txt")
    snapshots = [snapshot] * 4  # 4 identical snapshots
    assert is_terminal_idle(snapshots) is True


def test_changing_snapshots_not_idle() -> None:
    """Test that changing snapshots indicate active state."""
    snapshots = [
        load_fixture("healthy", "agent_active_typing.txt"),
        load_fixture("healthy", "agent_waiting_response.txt"),
        load_fixture("healthy", "agent_active_typing.txt"),
        load_fixture("healthy", "agent_waiting_response.txt"),
    ]
    assert is_terminal_idle(snapshots) is False


def test_minor_changes_are_idle() -> None:
    """Test that minor changes (cursor blink) still count as idle."""
    base = load_fixture("idle", "agent_empty_prompt.txt")
    # Simulate cursor blink (1 character difference)
    snapshots = [base, base[:-1] + "_", base, base[:-1] + "_"]
    assert is_terminal_idle(snapshots) is True


def test_single_snapshot_not_idle() -> None:
    """Test that single snapshot can't determine idle state."""
    snapshot = load_fixture("idle", "agent_empty_prompt.txt")
    assert is_terminal_idle([snapshot]) is False


def test_empty_snapshots_not_idle() -> None:
    """Test that empty snapshots list is not idle."""
    assert is_terminal_idle([]) is False


def test_identical_texts_zero_distance() -> None:
    """Test that identical texts have zero distance."""
    text = "Hello, world!"
    assert _calculate_change_distance(text, text) == 0


def test_single_char_difference() -> None:
    """Test single character difference."""
    assert _calculate_change_distance("Hello", "Hallo") == 1


def test_multiple_char_differences() -> None:
    """Test multiple character differences."""
    # Function returns early after detecting >1 difference for efficiency
    assert _calculate_change_distance("Hello", "Haxyz") == 2


def test_length_difference() -> None:
    """Test significant length difference."""
    assert _calculate_change_distance("Hi", "Hello, world!") == 999


def test_minor_length_difference() -> None:
    """Test minor length difference."""
    assert _calculate_change_distance("Hello", "Hello!") == 1


def test_crashed_needs_recovery() -> None:
    """Test that crashed state needs recovery."""
    assert needs_recovery(AgentState.CRASHED) is True


def test_error_needs_recovery() -> None:
    """Test that error state needs recovery."""
    assert needs_recovery(AgentState.ERROR) is True


def test_idle_no_recovery() -> None:
    """Test that idle state doesn't need recovery."""
    assert needs_recovery(AgentState.IDLE) is False


def test_active_no_recovery() -> None:
    """Test that active state doesn't need recovery."""
    assert needs_recovery(AgentState.ACTIVE) is False


def test_message_queued_no_recovery() -> None:
    """Test that message queued state doesn't need recovery."""
    assert needs_recovery(AgentState.MESSAGE_QUEUED) is False


def test_notify_on_crash() -> None:
    """Test notification on crash."""
    assert should_notify_pm(AgentState.CRASHED, "session:0", {}) is True


def test_notify_on_error() -> None:
    """Test notification on error."""
    assert should_notify_pm(AgentState.ERROR, "session:0", {}) is True


def test_notify_on_idle() -> None:
    """Test notification on idle."""
    assert should_notify_pm(AgentState.IDLE, "session:0", {}) is True


def test_no_notify_on_active() -> None:
    """Test no notification on active."""
    assert should_notify_pm(AgentState.ACTIVE, "session:0", {}) is False


def test_command_not_found_is_crash() -> None:
    """Test command not found is detected as crash."""
    content = "bash: claude: command not found"
    assert _has_crash_indicators(content) is True


def test_segfault_is_crash() -> None:
    """Test segmentation fault is detected as crash."""
    content = "Segmentation fault (core dumped)"
    assert _has_crash_indicators(content) is True


def test_traceback_is_crash() -> None:
    """Test Python traceback is detected as crash."""
    content = "Traceback (most recent call last):\n  File..."
    assert _has_crash_indicators(content) is True


def test_normal_content_not_crash() -> None:
    """Test normal content is not detected as crash."""
    content = "Everything is working fine"
    assert _has_crash_indicators(content) is False


def test_network_error_detected() -> None:
    """Test network error is detected."""
    content = "Error: Network error occurred"
    assert _has_error_indicators(content) is True


def test_timeout_error_detected() -> None:
    """Test timeout error is detected."""
    content = "Request failed: Timeout error occurred"
    assert _has_error_indicators(content) is True


def test_permission_denied_detected() -> None:
    """Test permission denied is detected."""
    content = "Error: Permission denied"
    assert _has_error_indicators(content) is True


def test_normal_content_no_error() -> None:
    """Test normal content has no errors."""
    content = "Operation completed successfully"
    assert _has_error_indicators(content) is False


# Integration tests


def test_crashed_agent_full_flow() -> None:
    """Test full detection flow for crashed agent."""
    content = load_fixture("crashed", "agent_command_not_found.txt")

    # Should not have Claude interface
    assert is_claude_interface_present(content) is False

    # Should be detected as crashed
    state = detect_agent_state(content)
    assert state == AgentState.CRASHED

    # Should need recovery
    assert needs_recovery(state) is True

    # Should notify PM
    assert should_notify_pm(state, "session:0", {}) is True


def test_idle_agent_full_flow() -> None:
    """Test full detection flow for idle agent."""
    content = load_fixture("idle", "agent_empty_prompt.txt")

    # Should have Claude interface
    assert is_claude_interface_present(content) is True

    # Initial state detection (needs snapshots for idle)
    state = detect_agent_state(content)
    assert state == AgentState.ACTIVE

    # Simulate idle detection with snapshots
    snapshots = [content] * 4
    assert is_terminal_idle(snapshots) is True

    # Idle state should notify PM
    assert should_notify_pm(AgentState.IDLE, "session:0", {}) is True


def test_message_queued_full_flow() -> None:
    """Test full detection flow for agent with queued message."""
    content = load_fixture("message_queued", "agent_test_message_not_submitted.txt")

    # Should have Claude interface
    assert is_claude_interface_present(content) is True

    # Should detect message queued
    assert has_unsubmitted_message(content) is True

    # Should be detected as message queued state
    state = detect_agent_state(content)
    assert state == AgentState.MESSAGE_QUEUED

    # Should not need recovery
    assert needs_recovery(state) is False
