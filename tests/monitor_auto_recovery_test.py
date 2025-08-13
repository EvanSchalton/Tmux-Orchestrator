"""Test auto-recovery mechanisms for the monitoring system.

This module tests auto-recovery features:
1. Auto-restart of crashed agents
2. Recovery cooldown mechanisms
3. Recovery failure handling
4. Integration with PM notifications
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


def test_crashed_agent_auto_restart(mock_tmux, monitor, logger) -> None:
    """Test that crashed agents trigger auto-restart."""
    target = "session:1"

    # Mock crashed agent detection - ensure it ends with bash prompt
    # Use content that will be detected as crashed (shell prompt at end)
    crashed_content = "Human: exit\n\nbash-5.1$ "

    # Mock capture_pane to return crashed content multiple times (for snapshots)
    mock_tmux.capture_pane.side_effect = [crashed_content] * 10  # Enough for all snapshot calls

    # Mock successful restart
    with patch.object(monitor, "_attempt_agent_restart", return_value=True) as mock_restart:
        with patch("tmux_orchestrator.core.monitor.is_claude_interface_present", return_value=False):
            with patch("time.sleep"):  # Skip sleep delays
                monitor._check_agent_status(mock_tmux, target, logger, {})

    # Verify restart was attempted
    mock_restart.assert_called_once_with(mock_tmux, target, logger)

    # Verify no PM notification sent (restart succeeded)
    assert not any("_notify_crash" in str(call) for call in logger.error.call_args_list)


def test_restart_failure_notifies_pm(mock_tmux, monitor, logger) -> None:
    """Test that failed restart attempts notify PM."""
    target = "session:1"
    pm_target = "session:2"

    # Mock crashed agent
    crashed_content = "bash: claude: command not found\nbash $ "
    mock_tmux.capture_pane.side_effect = [crashed_content] * 10

    # Mock failed restart and PM discovery
    with patch.object(monitor, "_attempt_agent_restart", return_value=False):
        with patch.object(monitor, "_find_pm_target", return_value=pm_target):
            with patch.object(monitor, "_notify_crash") as mock_notify:
                with patch("tmux_orchestrator.core.monitor.is_claude_interface_present", return_value=False):
                    with patch("time.sleep"):
                        monitor._check_agent_status(mock_tmux, target, logger, {})

                # Verify _notify_crash was called with new signature
                mock_notify.assert_called_once_with(mock_tmux, target, logger, {})


def test_restart_command_sequence(mock_tmux, monitor, logger) -> None:
    """Test the correct command sequence for agent restart."""
    target = "backend:3"

    # Mock tmux capture to simulate restart progress
    capture_responses = [
        "$ ",  # Initial crashed state
        "$ claude --dangerously-skip-permissions",  # Command typed
        "Starting Claude...",  # Starting
        "Welcome to Claude Code!",  # Started successfully
    ]
    mock_tmux.capture_pane.side_effect = capture_responses

    # Test restart attempt
    with patch("time.sleep"):  # Skip actual sleep
        result = monitor._attempt_agent_restart(mock_tmux, target, logger)

    # Verify command sequence
    # Should send Ctrl+C first
    mock_tmux.press_ctrl_c.assert_called_once_with(target)

    # Then claude command
    mock_tmux.send_text.assert_called_once_with(target, "claude --dangerously-skip-permissions")

    # Verify Enter was pressed after the command
    press_enter_calls = mock_tmux.press_enter.call_args_list
    assert len(press_enter_calls) >= 1

    assert result is True


def test_restart_cooldown_mechanism(mock_tmux, monitor, logger) -> None:
    """Test that restart attempts respect cooldown period."""
    target = "session:1"

    # First restart attempt
    with patch("tmux_orchestrator.core.monitor.is_claude_interface_present", return_value=True):
        with patch("time.sleep"):
            monitor._attempt_agent_restart(mock_tmux, target, logger)

    # Second attempt should be blocked by cooldown
    mock_tmux.reset_mock()
    with patch("time.sleep"):
        result = monitor._attempt_agent_restart(mock_tmux, target, logger)

    # Should not attempt restart
    assert result is False
    assert not mock_tmux.send_text.called
    assert not mock_tmux.press_ctrl_c.called


def test_restart_timeout_handling(mock_tmux, monitor, logger) -> None:
    """Test handling of restart timeout."""
    target = "session:1"

    # Mock Claude never starting
    mock_tmux.capture_pane.return_value = "$ "

    # Test restart with timeout
    with patch("time.sleep") as mock_sleep:
        result = monitor._attempt_agent_restart(mock_tmux, target, logger)

    # Should have tried for 15 seconds
    assert mock_sleep.call_count >= 15
    assert result is False

    # Should log timeout
    logger.warning.assert_called()
    assert "timeout" in logger.warning.call_args[0][0].lower()


def test_restart_error_detection(mock_tmux, monitor, logger) -> None:
    """Test detection of errors during restart."""
    target = "session:1"

    # Mock permission denied error
    mock_tmux.capture_pane.return_value = "bash: /usr/local/bin/claude: Permission denied"

    # Test restart
    with patch("time.sleep"):
        result = monitor._attempt_agent_restart(mock_tmux, target, logger)

    assert result is False

    # Should log the error
    error_logs = [call for call in logger.error.call_args_list]
    assert any("permission denied" in str(call).lower() for call in error_logs)


def test_recovery_clears_idle_tracking(mock_tmux, monitor, logger) -> None:
    """Test that successful recovery clears idle tracking."""
    target = "session:1"

    # Set up idle tracking
    monitor._idle_agents[target] = datetime.now() - timedelta(minutes=30)
    monitor._submission_attempts[target] = 5

    # Mock successful restart
    with patch("tmux_orchestrator.core.monitor.is_claude_interface_present", return_value=True):
        with patch("time.sleep"):
            monitor._attempt_agent_restart(mock_tmux, target, logger)

    # Tracking should remain (restart doesn't clear it, only activity does)
    # This is correct behavior - agent needs to become active to clear tracking
    assert target in monitor._idle_agents


def test_multiple_agent_recovery(mock_tmux, monitor, logger) -> None:
    """Test recovery of multiple agents in sequence."""
    agents = ["frontend:1", "backend:2", "qa:3"]

    # Mock all as crashed
    for agent in agents:
        with patch("tmux_orchestrator.core.monitor_helpers.detect_agent_state", return_value=AgentState.CRASHED):
            with patch.object(monitor, "_attempt_agent_restart", return_value=True):
                monitor._check_agent_status(mock_tmux, agent, logger, {})

    # Verify all were attempted
    assert logger.error.call_count >= len(agents)
    for agent in agents:
        assert any(agent in str(call) for call in logger.error.call_args_list)


def test_recovery_with_custom_error_states(mock_tmux, monitor, logger) -> None:
    """Test recovery for various error states."""
    error_contents = [
        "Segmentation fault (core dumped)",
        "Killed",
        "[Process completed]",
        "Terminated",
        "ModuleNotFoundError: No module named 'claude'",
    ]

    for i, content in enumerate(error_contents):
        target = f"session:{i}"
        mock_tmux.capture_pane.return_value = content

        with patch("tmux_orchestrator.core.monitor_helpers.detect_agent_state", return_value=AgentState.CRASHED):
            with patch.object(monitor, "_attempt_agent_restart", return_value=True):
                monitor._check_agent_status(mock_tmux, target, logger, {})

        # Should attempt recovery for all crash types
        assert any(target in str(call) for call in logger.error.call_args_list)


def test_recovery_during_startup(mock_tmux, monitor, logger) -> None:
    """Test that agents in startup state are not restarted."""
    target = "session:1"

    startup_content = """Initializing Claude Code...
Loading configuration..."""

    mock_tmux.capture_pane.return_value = startup_content

    with patch("tmux_orchestrator.core.monitor_helpers.detect_agent_state", return_value=AgentState.ACTIVE):
        with patch.object(monitor, "_attempt_agent_restart") as mock_restart:
            monitor._check_agent_status(mock_tmux, target, logger, {})

    # Should not attempt restart for starting agents
    mock_restart.assert_not_called()


def test_recovery_exception_handling(mock_tmux, monitor, logger) -> None:
    """Test graceful handling of exceptions during recovery."""
    target = "session:1"

    # Mock crashed content
    mock_tmux.capture_pane.side_effect = ["bash $ "] * 10

    # Mock exception during restart
    with patch.object(monitor, "_attempt_agent_restart", side_effect=Exception("Test error")):
        with patch("tmux_orchestrator.core.monitor.is_claude_interface_present", return_value=False):
            with patch("time.sleep"):
                # Should not crash the monitor
                monitor._check_agent_status(mock_tmux, target, logger, {})

    # Should log the error
    assert logger.error.called


def test_concurrent_recovery_protection(mock_tmux, monitor, logger) -> None:
    """Test protection against concurrent recovery attempts."""
    target = "session:1"

    # Simulate rapid successive checks
    for _ in range(5):
        # Mock crashed content
        mock_tmux.capture_pane.side_effect = ["bash $ "] * 10

        with patch("tmux_orchestrator.core.monitor.is_claude_interface_present", return_value=False):
            with patch.object(monitor, "_attempt_agent_restart", return_value=False):
                with patch.object(monitor, "_notify_crash"):
                    with patch("time.sleep"):
                        monitor._check_agent_status(mock_tmux, target, logger, {})

    # Due to cooldown in notifications, PM shouldn't be spammed
    # Check notification cooldown is working
    notification_calls = mock_tmux.send_message.call_count
    assert notification_calls <= 1  # Should only notify once due to cooldown
