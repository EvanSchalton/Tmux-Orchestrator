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
def test_compacting_check_case_insensitive(mock_tmux_manager, mock_sleep) -> None:
    """Test that compacting detection is case insensitive."""
    # Setup
    tmux = mock_tmux_manager.return_value
    monitor = IdleMonitor(tmux)

    # Test various cases - need to match exact patterns from monitor.py
    test_cases = [
        "Compacting conversation",
        "More text with Compacting conversation in it",
        "Previous text\nCompacting conversation\nMore text",
        "Some Compacting conversation text here",
    ]

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

        with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger:
            logger = MagicMock()
            mock_logger.return_value = logger

            tmux.capture_pane.side_effect = [content] * 4
            monitor._find_pm_agent = MagicMock(return_value="pm-session:0")

            # Run check
            monitor._check_agent_status(tmux, "test-session:1", logger, {})

            # Verify compacting was detected as thinking indicator
            debug_calls = [call.args[0] for call in logger.debug.call_args_list]
            assert any(
                "found thinking indicator:" in msg and "compacting" in msg.lower() for msg in debug_calls
            ), f"Failed to detect compacting for: {compacting_text}"


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

        # Clear any previous notifications
        monitor._idle_notifications = {}

        # Run check
        monitor._check_agent_status(tmux, "test-session:1", logger, {})

        # Verify it was marked as idle (no compacting detected)
        info_calls = [call.args[0] for call in logger.info.call_args_list]
        assert any("is IDLE" in msg for msg in info_calls)
        assert any("is idle without active work" in msg for msg in info_calls)

        # Verify PM WAS notified
        assert tmux.send_message.called
        notification = tmux.send_message.call_args[0][1]
        assert "IDLE AGENT ALERT" in notification


@patch("tmux_orchestrator.core.monitor.time.sleep")
@patch("tmux_orchestrator.core.monitor.TMUXManager")
def test_compacting_only_checked_near_input_box(mock_tmux_manager, mock_sleep) -> None:
    """Test that compacting is only detected near the input box (2-3 lines above)."""
    # Setup
    tmux = mock_tmux_manager.return_value
    monitor = IdleMonitor(tmux)

    # Mock content with "compacting" far from input box (should NOT prevent idle)
    content = """
╭─ Claude │ Chat ─────────────────────────────────────────────────────────────────────╮
│ [Compacting old conversation from earlier...]                                      │
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

        tmux.capture_pane.return_value = content
        monitor._find_pm_agent = MagicMock(return_value="pm-session:0")
        monitor._idle_notifications = {}

        # Run check
        monitor._check_agent_status(tmux, "test-session:1", logger, {})

        # Verify compacting was NOT detected (too far from input)
        debug_calls = [call.args[0] for call in logger.debug.call_args_list]
        assert not any("found thinking indicator:" in msg and "compacting" in msg.lower() for msg in debug_calls)

        # Verify agent was marked as idle and PM was notified
        assert tmux.send_message.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
