"""Test PM notification delivery system for monitoring.

This module tests PM notification features:
1. Idle agent notifications are sent immediately
2. Crash notifications work correctly
3. Notification cooldowns are respected
4. PM discovery works properly
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.core.monitor_helpers import AgentState


@pytest.fixture
def monitor(mock_tmux):
    """Create an IdleMonitor instance with mock tmux."""
    return IdleMonitor(mock_tmux)


def test_idle_agent_notification_immediate(mock_tmux, monitor, logger) -> None:
    """Test that idle agents trigger immediate PM notification."""
    target = "session:1"
    pm_target = "session:2"

    # Mock PM discovery
    with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
        # Set up idle agent tracking
        monitor._idle_agents[target] = datetime.now()

        # Call notification method
        monitor._check_idle_notification(mock_tmux, target, logger, {})

    # Verify PM was notified
    mock_tmux.send_message.assert_called_once()
    call_args = mock_tmux.send_message.call_args
    assert call_args[0][0] == pm_target  # PM target
    assert "IDLE AGENT ALERT" in call_args[0][1]  # Message contains alert
    assert target in call_args[0][1]  # Message mentions the idle agent


def test_no_self_notification_for_pm(mock_tmux, monitor, logger) -> None:
    """Test that PM doesn't get notified about their own idle state."""
    pm_target = "session:2"

    # Mock PM discovery to return same target
    with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
        # PM is idle
        monitor._idle_agents[pm_target] = datetime.now()

        # Try to notify about PM's own idle state
        monitor._check_idle_notification(mock_tmux, pm_target, logger, {})

    # Should not send any message
    mock_tmux.send_message.assert_not_called()


def test_crash_notification_with_cooldown(mock_tmux, monitor, logger) -> None:
    """Test crash notifications respect 5-minute cooldown."""
    target = "session:1"
    pm_target = "session:2"

    # Mock PM discovery
    with patch.object(monitor, "_find_pm_target", return_value=pm_target):
        # First notification should work
        monitor._notify_crash(mock_tmux, target, logger, {})

        assert mock_tmux.send_message.called

        # Reset mock
        mock_tmux.send_message.reset_mock()

        # Second notification within 5 minutes should be skipped
        monitor._notify_crash(mock_tmux, target, logger, {})

        assert not mock_tmux.send_message.called


def test_pm_discovery_mechanism(mock_tmux, monitor) -> None:
    """Test PM agent discovery works correctly."""
    # Set up mock sessions and windows
    sessions = [{"name": "monitor-fixes"}, {"name": "backend-dev"}]

    windows = {
        "monitor-fixes": [
            {"index": "0", "name": "orchestrator"},
            {"index": "1", "name": "qa-engineer"},
            {"index": "2", "name": "project-manager"},  # This is the PM
        ],
        "backend-dev": [{"index": "0", "name": "developer"}, {"index": "1", "name": "tester"}],
    }

    # Mock tmux methods
    mock_tmux.list_sessions.return_value = sessions
    mock_tmux.list_windows.side_effect = lambda s: windows.get(s, [])

    # PM window should have Claude interface
    def capture_pane_side_effect(target, lines=10):
        if target == "monitor-fixes:2":
            return "╭─ Claude Code ─╮\n│ > Ready to manage the team\n╰───────────────╯"
        return "bash$ "

    mock_tmux.capture_pane.side_effect = capture_pane_side_effect

    # Find PM
    pm_target = monitor._find_pm_agent(mock_tmux)

    assert pm_target == "monitor-fixes:2"


def test_recovery_notification(mock_tmux, monitor, logger) -> None:
    """Test recovery needed notifications."""
    target = "session:1"
    pm_target = "session:2"

    # Mock PM discovery
    with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
        # Send recovery notification
        monitor._notify_recovery_needed(mock_tmux, target, logger)

    # Verify notification sent
    mock_tmux.send_message.assert_called_once()
    call_args = mock_tmux.send_message.call_args
    assert call_args[0][0] == pm_target
    assert "AGENT RECOVERY NEEDED" in call_args[0][1]
    assert target in call_args[0][1]


def test_notification_format(mock_tmux, monitor, logger) -> None:
    """Test notification message format and content."""
    target = "backend:3"
    pm_target = "monitor:2"

    # Set up idle duration
    idle_start = datetime.now() - timedelta(minutes=15)
    monitor._idle_agents[target] = idle_start

    with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
        with patch.object(monitor, "_determine_agent_type", return_value="Backend Developer"):
            monitor._check_idle_notification(mock_tmux, target, logger, {})

    # Check message format
    call_args = mock_tmux.send_message.call_args
    message = call_args[0][1]

    assert "🚨 IDLE AGENT ALERT:" in message
    assert "backend:3 (Backend Developer)" in message
    assert "automated notification" in message


def test_no_pm_found_handling(mock_tmux, monitor, logger) -> None:
    """Test graceful handling when no PM is found."""
    target = "session:1"

    # Mock no PM found
    with patch.object(monitor, "_find_pm_agent", return_value=None):
        # Should not crash, just log warning
        monitor._check_idle_notification(mock_tmux, target, logger, {})

    # Verify warning was logged
    logger.warning.assert_called()
    assert "No PM found" in logger.warning.call_args[0][0]

    # No message should be sent
    mock_tmux.send_message.assert_not_called()


def test_notification_delivery_failure(mock_tmux, monitor, logger) -> None:
    """Test handling of notification delivery failures."""
    target = "session:1"
    pm_target = "session:2"

    # Mock PM discovery
    with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
        # Mock send_message to fail
        mock_tmux.send_message.return_value = False

        # Send notification
        monitor._check_idle_notification(mock_tmux, target, logger, {})

    # Verify error was logged
    error_logs = [call for call in logger.error.call_args_list]
    assert any("Failed to notify PM" in str(call) for call in error_logs)


def test_idle_notification_cooldown_from_helper() -> None:
    """Test that idle notifications are always allowed (no cooldown for idle state)."""
    from tmux_orchestrator.core.monitor_helpers import should_notify_pm

    target = "session:1"
    notification_history = {}

    # First notification should be allowed
    assert should_notify_pm(AgentState.IDLE, target, notification_history) is True

    # Add to history - idle notifications don't use cooldown
    notification_history[f"idle_{target}"] = datetime.now()

    # Second notification should still be allowed (no cooldown for idle)
    assert should_notify_pm(AgentState.IDLE, target, notification_history) is True

    # Even with recent notification, idle should still be allowed
    notification_history[f"idle_{target}"] = datetime.now() - timedelta(seconds=30)
    assert should_notify_pm(AgentState.IDLE, target, notification_history) is True


def test_crash_notification_cooldown_from_helper() -> None:
    """Test that crash notifications use cooldown from helper function."""
    from tmux_orchestrator.core.monitor_helpers import should_notify_pm

    target = "session:1"
    notification_history = {}

    # First crash notification should be allowed
    assert should_notify_pm(AgentState.CRASHED, target, notification_history) is True

    # Add to history with crash prefix
    notification_history[f"crash_{target}"] = datetime.now()

    # Immediate second notification should be blocked
    assert should_notify_pm(AgentState.CRASHED, target, notification_history) is False

    # After 5 minutes, should be allowed
    notification_history[f"crash_{target}"] = datetime.now() - timedelta(minutes=6)
    assert should_notify_pm(AgentState.CRASHED, target, notification_history) is True


def test_full_idle_detection_to_notification_flow(mock_tmux, monitor, logger) -> None:
    """Test complete flow from idle detection to PM notification."""
    agent_target = "backend:1"
    pm_target = "monitor:2"

    # Set up agent content (idle with Claude interface, no message)
    idle_content = """╭─ Claude Code ─────────────────────────────────────────────────╮
│ Task completed successfully!                                     │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > _                                                             │
╰─────────────────────────────────────────────────────────────────╯"""

    # Mock tmux methods
    mock_tmux.capture_pane.return_value = idle_content

    # Clear notification history to ensure fresh state
    monitor._idle_notifications = {}

    # Mock PM discovery
    with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
        # Mock helper functions
        with patch("tmux_orchestrator.core.monitor_helpers.detect_agent_state", return_value=AgentState.IDLE):
            with patch("tmux_orchestrator.core.monitor_helpers.is_terminal_idle", return_value=True):
                with patch("tmux_orchestrator.core.monitor_helpers.is_claude_interface_present", return_value=True):
                    with patch("tmux_orchestrator.core.monitor_helpers.has_unsubmitted_message", return_value=False):
                        with patch("tmux_orchestrator.core.monitor_helpers.should_notify_pm", return_value=True):
                            # Run status check
                            monitor._check_agent_status(mock_tmux, agent_target, logger, {})

    # Verify notification was sent
    mock_tmux.send_message.assert_called()
    call_args = mock_tmux.send_message.call_args
    assert call_args[0][0] == pm_target
    assert "IDLE AGENT ALERT" in call_args[0][1]
    assert agent_target in call_args[0][1]


def test_idle_pm_receives_idle_agent_notifications(mock_tmux, monitor, logger) -> None:
    """CRITICAL: Test that idle PMs receive notifications about other idle agents.

    This tests the fix for the bug where PMs don't receive notifications about
    other idle agents when the PM is also idle.
    """
    pm_target = "session:1"
    idle_agent_target = "session:2"

    # Mock idle agent content (Claude interface present but no activity)
    idle_agent_content = """╭─ Claude Code ───────────────────────────────────────────────────╮
│ > _                                                             │
╰─────────────────────────────────────────────────────────────────╯

? for shortcuts"""

    # Mock tmux to return identical snapshots for idle detection
    # The activity detection takes 4 snapshots, all must be identical for idle
    mock_tmux.capture_pane.return_value = idle_agent_content

    # Clear notification history to ensure fresh state
    monitor._idle_notifications = {}

    # Mock PM discovery to find the PM
    with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
        # Mock helper functions to simulate idle agent with Claude interface
        with patch("tmux_orchestrator.core.monitor_helpers.detect_agent_state", return_value=AgentState.IDLE):
            with patch("tmux_orchestrator.core.monitor_helpers.is_claude_interface_present", return_value=True):
                with patch("tmux_orchestrator.core.monitor_helpers.has_unsubmitted_message", return_value=False):
                    with patch("tmux_orchestrator.core.monitor_helpers.should_notify_pm", return_value=True):
                        with patch("time.sleep"):  # Skip sleep delays
                            # Check idle agent status - this should trigger PM notification
                            monitor._check_agent_status(mock_tmux, idle_agent_target, logger, {})

    # Verify PM notification was sent
    assert mock_tmux.send_message.called
    pm_notification_calls = [call for call in mock_tmux.send_message.call_args_list if call[0][0] == pm_target]
    assert len(pm_notification_calls) == 1

    # Verify notification content mentions the idle agent
    notification_message = pm_notification_calls[0][0][1]
    assert idle_agent_target in notification_message
    assert "IDLE AGENT ALERT" in notification_message


def test_pm_self_notification_prevention_still_works(mock_tmux, monitor, logger) -> None:
    """Test that the bug fix doesn't break self-notification prevention."""
    pm_target = "session:1"

    # Mock PM as idle
    pm_idle_content = """╭─ Claude Code ───────────────────────────────────────────────────╮
│ > _                                                             │
╰─────────────────────────────────────────────────────────────────╯"""

    mock_tmux.capture_pane.return_value = pm_idle_content

    # Mock PM discovery to find the PM (same as target)
    with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
        # Mock helper functions to simulate idle PM
        with patch("tmux_orchestrator.core.monitor_helpers.is_claude_interface_present", return_value=True):
            with patch("tmux_orchestrator.core.monitor_helpers.has_unsubmitted_message", return_value=False):
                with patch("tmux_orchestrator.core.monitor_helpers.should_notify_pm", return_value=True):
                    with patch("time.sleep"):
                        # Check PM's own status - should NOT trigger self-notification
                        monitor._check_agent_status(mock_tmux, pm_target, logger, {})

    # Verify no self-notification was sent (the key test)
    pm_notification_calls = [
        call
        for call in mock_tmux.send_message.call_args_list
        if call[0][0] == pm_target and "IDLE AGENT ALERT" in call[0][1]
    ]
    assert len(pm_notification_calls) == 0

    # Verify that no notification messages were sent at all for this scenario
    assert not mock_tmux.send_message.called or all(
        not ("IDLE AGENT ALERT" in str(call) and call[0][0] == pm_target)
        for call in mock_tmux.send_message.call_args_list
    )
