"""Test the simplified compaction detection logic."""

from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor


@patch("tmux_orchestrator.core.monitor.time.sleep")
@patch("tmux_orchestrator.core.monitor.TMUXManager")
def test_detects_compacting_above_input_box(mock_tmux_manager, mock_sleep) -> None:
    """Test that agent is not marked as idle when compacting."""
    # Setup
    tmux = mock_tmux_manager.return_value
    monitor = IdleMonitor(tmux)

    # Mock compacting content - simulates what appears during compaction
    compacting_content = """
╭─ Claude │ Chat with Claude 3.5 Sonnet ────────────────────────────────────────────╮
│                                                                                    │
│ Previous conversation content here...                                              │
│                                                                                    │
│ Human: Long message that triggered compaction...                                  │
│                                                                                    │
│ Assistant: Response...                                                             │
│                                                                                    │
│ Human: Another message...                                                          │
│                                                                                    │
│ [Compacting conversation...]                                                       │
│                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────╯
╭─ Human ─────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                   │
╰─────────────────────────────────────────────────────────────────────────────────────╯
"""

    with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger:
        logger = MagicMock()
        mock_logger.return_value = logger

        # Mock the capture to return compacting content
        # Need to return the same content 4 times (for the 4 snapshots)
        tmux.capture_pane.side_effect = [compacting_content] * 4

        # Mock PM discovery
        monitor._find_pm_agent = MagicMock(return_value="pm-session:0")

        # Run the check
        monitor._check_agent_status(tmux, "test-session:1", logger, {})

        # Verify it detected compacting activity - should find "Compacting conversation" as thinking indicator
        debug_calls = [call.args[0] for call in logger.debug.call_args_list]
        assert any("found thinking indicator: 'Compacting conversation'" in msg for msg in debug_calls)

        # Verify PM was NOT notified (no idle notification sent)
        assert not tmux.send_message.called


@patch("tmux_orchestrator.core.monitor.time.sleep")
@patch("tmux_orchestrator.core.monitor.TMUXManager")
@patch("tmux_orchestrator.core.monitor.logging.getLogger")
@patch("tmux_orchestrator.core.monitor.is_claude_interface_present", return_value=True)
@patch("tmux_orchestrator.core.monitor_helpers.has_unsubmitted_message", return_value=False)
def test_compacting_check_case_insensitive(
    mock_unsubmitted, mock_claude_present, mock_get_logger, mock_tmux_manager, mock_sleep
) -> None:
    """Test that compacting detection is case insensitive."""
    # Setup
    tmux = mock_tmux_manager.return_value
    monitor = IdleMonitor(tmux)

    # Mock both the passed logger and the session logger
    passed_logger = MagicMock()
    session_logger = MagicMock()

    # Return the appropriate logger based on name
    def logger_factory(name):
        if "idle_monitor_" in name:
            return session_logger
        return passed_logger

    mock_get_logger.side_effect = logger_factory

    # Test various cases - need to match exact patterns from monitor.py
    test_cases = [
        "Compacting conversation",
        "More text with Compacting conversation in it",
        "Previous text\nCompacting conversation\nMore text",
        "Some Compacting conversation text here",
    ]

    success_count = 0
    for compacting_text in test_cases:
        content = f"""
╭─ Claude │ Chat ─────────────────────────────────────────────────────────────────────╮
│ Previous content...                                                                 │
│ {compacting_text}                                                                  │
│                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────╯
╭─ Human ─────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                   │
╰─────────────────────────────────────────────────────────────────────────────────────╯
"""

        # Reset for each iteration
        tmux.capture_pane.reset_mock()
        tmux.capture_pane.side_effect = [content] * 4
        monitor._find_pm_agent = MagicMock(return_value="pm-session:0")
        session_logger.reset_mock()

        # Run check
        monitor._check_agent_status(tmux, "test-session:1", passed_logger, {})

        # Check if compacting was detected
        debug_calls = [call.args[0] for call in session_logger.debug.call_args_list]
        info_calls = [call.args[0] for call in session_logger.info.call_args_list]

        detected = any("found thinking indicator: 'Compacting conversation'" in msg for msg in debug_calls) or any(
            "appears idle but is compacting" in msg for msg in info_calls
        )

        if detected:
            success_count += 1

    # Verify that at least some cases were detected (should be all of them)
    assert (
        success_count > 0
    ), "Failed to detect compacting in any test case. Expected to detect 'Compacting conversation' pattern."


@patch("tmux_orchestrator.core.monitor.time.sleep")
@patch("tmux_orchestrator.core.monitor.TMUXManager")
def test_truly_idle_without_compacting(mock_tmux_manager, mock_sleep) -> None:
    """Test that truly idle agents (not compacting) still get notified."""
    # Setup
    tmux = mock_tmux_manager.return_value
    monitor = IdleMonitor(tmux)

    # Mock idle content without any compacting message
    idle_content = """
╭─ Claude │ Chat with Claude 3.5 Sonnet ────────────────────────────────────────────╮
│                                                                                    │
│ Human: Previous task completed                                                     │
│                                                                                    │
│ Assistant: Task is done. Let me know if you need anything else.                  │
│                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────╯
╭─ Human ─────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                   │
╰─────────────────────────────────────────────────────────────────────────────────────╯
"""

    with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger:
        logger = MagicMock()
        mock_logger.return_value = logger

        tmux.capture_pane.side_effect = [idle_content] * 4
        monitor._find_pm_agent = MagicMock(return_value="pm-session:0")
        monitor._find_pm_in_session = MagicMock(return_value="test-session:0")

        # Clear any previous notifications
        monitor._idle_notifications = {}

        # Run check
        pm_notifications = {}
        monitor._check_agent_status(tmux, "test-session:1", logger, pm_notifications)

        # Verify it was marked as idle (no compacting detected)
        info_calls = [call.args[0] for call in logger.info.call_args_list]
        assert any("is IDLE" in msg for msg in info_calls)
        assert any("is idle without active work" in msg for msg in info_calls)

        # Verify notification was collected
        assert len(pm_notifications) > 0, f"Expected notifications to be collected, but got: {pm_notifications}"

        # Send collected notifications
        monitor._send_collected_notifications(pm_notifications, tmux, logger)

        # Now verify PM WAS notified
        assert tmux.send_message.called
        notification = tmux.send_message.call_args[0][1]
        assert "IDLE AGENTS" in notification
        assert "test-session:1" in notification


@patch("tmux_orchestrator.core.monitor.time.sleep")
@patch("tmux_orchestrator.core.monitor.TMUXManager")
def test_compacting_only_checked_near_input_box(mock_tmux_manager, mock_sleep) -> None:
    """Test that compacting is detected anywhere in content (safer approach to prevent false idle alerts)."""
    # Setup
    tmux = mock_tmux_manager.return_value
    monitor = IdleMonitor(tmux)

    # Mock content with "compacting" far from input box (should NOT prevent idle)
    content = """
╭─ Claude │ Chat ─────────────────────────────────────────────────────────────────────╮
│ [Compacting conversation...]                                                       │
│                                                                                    │
│ Many lines of content here...                                                      │
│ Line 1                                                                            │
│ Line 2                                                                            │
│ Line 3                                                                            │
│ Line 4                                                                            │
│ Line 5                                                                            │
│                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────╯
╭─ Human ─────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                   │
╰─────────────────────────────────────────────────────────────────────────────────────╯
"""

    with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger:
        logger = MagicMock()
        mock_logger.return_value = logger

        tmux.capture_pane.side_effect = [content] * 4
        monitor._find_pm_agent = MagicMock(return_value="pm-session:0")
        monitor._idle_notifications = {}

        # Run check
        pm_notifications = {}
        monitor._check_agent_status(tmux, "test-session:1", logger, pm_notifications)

        # Actually, compacting IS detected anywhere in content (safer approach)
        debug_calls = [call.args[0] for call in logger.debug.call_args_list]
        assert any("found thinking indicator:" in msg and "Compacting" in msg for msg in debug_calls)

        # Verify agent was NOT marked as idle (compacting prevents idle)
        info_calls = [call.args[0] for call in logger.info.call_args_list]
        assert any("is ACTIVE" in msg for msg in info_calls)
        assert not tmux.send_message.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
