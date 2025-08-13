"""Test for compaction detection to prevent false idle alerts."""

from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor


@patch("tmux_orchestrator.core.monitor.time.sleep")
@patch("tmux_orchestrator.core.monitor.TMUXManager")
def test_compaction_prevents_idle_alert(mock_tmux, mock_sleep) -> None:
    """Test that agents compacting are marked as ACTIVE, preventing false idle alerts."""
    tmux = mock_tmux.return_value
    monitor = IdleMonitor(tmux)

    # Content with compacting message - agent appears idle but is actually compacting
    content = """╭─ Claude Code ──────────────────────────────────────────────────────────────╮
│                                                                             │
│ Previous conversation...                                                    │
│                                                                             │
│ [Compacting conversation...]                                                │
│                                                                             │
│ >                                                                           │
│                                                                             │
╰─────────────────────────────────────────────────────────────────────────────╯"""

    # Mock to return same content 4 times (would normally indicate idle)
    tmux.capture_pane.side_effect = [content] * 4

    with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger:
        logger = MagicMock()
        mock_logger.return_value = logger
        monitor._find_pm_agent = MagicMock(return_value="pm:0")

        # Run check
        monitor._check_agent_status(tmux, "test:1", logger, {})

        # Get logs
        info_logs = [call.args[0] for call in logger.info.call_args_list]
        debug_logs = [call.args[0] for call in logger.debug.call_args_list]

        # Agent should be marked as ACTIVE because "Compacting conversation" is detected
        assert any("is ACTIVE" in log for log in info_logs), f"Expected ACTIVE, got info logs: {info_logs}"

        # Should detect the compacting as a thinking indicator
        assert any(
            "found thinking indicator" in log and "Compacting conversation" in log for log in debug_logs
        ), f"Expected compacting detection in debug logs: {debug_logs}"

        # PM should NOT be notified (no idle alert)
        assert not tmux.send_message.called, "PM should not be notified when agent is compacting"


@patch("tmux_orchestrator.core.monitor.time.sleep")
@patch("tmux_orchestrator.core.monitor.TMUXManager")
def test_truly_idle_without_compacting(mock_tmux, mock_sleep) -> None:
    """Test that truly idle agents (not compacting) still get notified."""
    tmux = mock_tmux.return_value
    monitor = IdleMonitor(tmux)

    # Mock idle content without any compacting message
    idle_content = """╭─ Claude │ Chat with Claude 3.5 Sonnet ────────────────────────────────────────────╮
│                                                                                    │
│ Human: Previous task completed                                                     │
│                                                                                    │
│ Assistant: Task is done. Let me know if you need anything else.                  │
│                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────╯
╭─ Human ─────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                   │
╰─────────────────────────────────────────────────────────────────────────────────────╯"""

    with patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger:
        logger = MagicMock()
        mock_logger.return_value = logger

        tmux.capture_pane.side_effect = [idle_content] * 4
        monitor._find_pm_agent = MagicMock(return_value="pm-session:0")

        # Clear any previous notifications
        monitor._idle_notifications = {}

        # Run check
        monitor._check_agent_status(tmux, "test-session:1", logger, {})

        # Get logs
        info_calls = [call.args[0] for call in logger.info.call_args_list]

        # Verify it was marked as idle (no compacting detected)
        assert any("is IDLE" in msg for msg in info_calls), f"Expected IDLE in logs: {info_calls}"
        assert any(
            "is idle without active work" in msg for msg in info_calls
        ), f"Expected idle notification in logs: {info_calls}"

        # Verify PM WAS notified
        assert tmux.send_message.called, "PM should be notified for truly idle agents"
        notification = tmux.send_message.call_args[0][1]
        assert "IDLE AGENT ALERT" in notification


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
