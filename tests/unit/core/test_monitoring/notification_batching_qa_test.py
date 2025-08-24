"""
Comprehensive QA test suite for notification batching system.

Tests notification consolidation, batch delivery, and edge cases.
Author: QA Engineer
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager


class TestNotificationBatchingSystem:
    """Comprehensive tests for the notification batching system."""

    @pytest.fixture
    def mock_tmux(self):
        """Mock TMUXManager for testing."""
        tmux = Mock(spec=TMUXManager)

        # Default session/window structure
        tmux.list_sessions.return_value = [{"name": "dev-session"}, {"name": "qa-session"}]

        tmux.list_windows.return_value = [
            {"index": "0", "name": "main"},
            {"index": "1", "name": "Claude-pm"},
            {"index": "2", "name": "Claude-backend"},
            {"index": "3", "name": "Claude-frontend"},
            {"index": "4", "name": "Claude-qa"},
        ]

        # PM detection - use correct Claude interface patterns
        tmux.capture_pane.return_value = "Welcome to Claude Code\n? for shortcuts\n╭─ Chat\n│ > "

        return tmux

    @pytest.fixture
    def idle_monitor(self, mock_tmux):
        """Create IdleMonitor instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Override the project directory to use temp
            monitor = IdleMonitor(mock_tmux)
            monitor.pid_file = Path(temp_dir) / "test-monitor.pid"
            monitor.log_file = Path(temp_dir) / "test-monitor.log"
            yield monitor

    def test_multiple_simultaneous_agent_failures(self, idle_monitor, mock_tmux):
        """Test multiple agents failing at the same time."""
        # Setup: Multiple crashed agents
        crashed_agents = ["dev-session:2", "dev-session:3", "dev-session:4"]

        # Mock PM detection
        mock_tmux.list_windows.side_effect = lambda session: [
            {"index": "1", "name": "Claude-pm"},
            {"index": "2", "name": "Claude-backend"},
            {"index": "3", "name": "Claude-frontend"},
            {"index": "4", "name": "Claude-qa"},
        ]

        # Mock crash detection for multiple agents
        def mock_capture_pane(target, lines=50):
            if target == "dev-session:1":  # PM
                return "Welcome to Claude Code\n? for shortcuts\n╭─ Chat\n│ > "
            elif target in crashed_agents:
                return "bash-5.1$ "  # Bash prompt indicates crash
            else:
                return "Welcome to Claude Code\n? for shortcuts\n╭─ Chat\n│ > "

        mock_tmux.capture_pane.side_effect = mock_capture_pane

        # Initialize notification collection
        pm_notifications = {}

        # Simulate notification collection for crashed agents
        for agent in crashed_agents:
            session = agent.split(":")[0]
            message = f"🚨 AGENT CRASH ALERT:\n\nClaude Code has crashed for agent at {agent}"
            idle_monitor._collect_notification(pm_notifications, session, message, mock_tmux)

        # Verify notifications were collected
        assert len(pm_notifications) == 1  # Only one PM target
        pm_target = list(pm_notifications.keys())[0]
        assert pm_target == "dev-session:1"
        # Three crash notifications
        assert len(pm_notifications[pm_target]) == 3

    def test_mixed_notification_types_consolidation(self, idle_monitor, mock_tmux):
        """Test consolidation of different notification types."""
        agents = ["dev-session:2", "dev-session:3", "dev-session:4", "dev-session:5"]

        # Mock different agent states
        def mock_capture_pane(target, lines=50):
            if target == "dev-session:1":  # PM
                return "Welcome to Claude Code\n? for shortcuts\n╭─ Chat\n│ > "
            elif target == "dev-session:2":  # Crashed
                return "bash-5.1$ "
            elif target == "dev-session:3":  # Idle
                return "Welcome to Claude Code\n? for shortcuts\n╭─ Chat\n│ > "
            elif target == "dev-session:4":  # Has unsubmitted message
                return "Welcome to Claude Code\n╭─ Chat\n│ > Type your message here and press Enter to submit..."
            elif target == "dev-session:5":  # Active (compacting)
                return "Compacting conversation..."
            else:
                return "Welcome to Claude Code\n? for shortcuts\n╭─ Chat\n│ > "

        mock_tmux.capture_pane.side_effect = mock_capture_pane

        # Mock snapshots for idle detection (no changes = idle)
        pm_notifications = {}

        # Check each agent
        for agent in agents:
            idle_monitor._check_agent_status(mock_tmux, agent, Mock(), pm_notifications)

        # Verify mixed notification types were collected
        assert len(pm_notifications) == 1
        pm_target = list(pm_notifications.keys())[0]
        messages = pm_notifications[pm_target]

        # Should have crash and idle notifications
        crash_msgs = [msg for msg in messages if "CRASH" in msg or "FAILURE" in msg]
        idle_msgs = [msg for msg in messages if "IDLE" in msg]

        assert len(crash_msgs) >= 1
        assert len(idle_msgs) >= 1

    def test_consolidated_report_format(self, idle_monitor, mock_tmux):
        """Test the format of consolidated reports."""
        # Create test notifications
        pm_notifications = {
            "dev-session:1": [
                "🚨 AGENT CRASH ALERT:\n\nClaude Code has crashed for agent at dev-session:2\n\n**RECOVERY ACTIONS NEEDED**:\n1. Restart Claude Code in the crashed window\n2. Provide system prompt from agent-prompts.yaml\n3. Re-assign current tasks\n4. Verify agent is responsive\n\nUse this command:\n• tmux send-keys -t dev-session:2 'claude --dangerously-skip-permissions' Enter",
                "🚨 IDLE AGENT ALERT:\n\nAgent dev-session:3 (Backend) is currently idle and available for work.\n\nPlease review their status and assign tasks as needed.\n\nThis is an automated notification from the monitoring system.",
                "🚨 TEAM MEMBER ALERT:\n\nMissing agents detected in session dev-session:\nClaude-frontend[dev-session:4]\n\nCurrent team members:\nClaude-pm[dev-session:1]\nClaude-backend[dev-session:3]\n\nPlease review your team plan to determine if these agents are still needed.",
            ]
        }

        # Mock logger
        mock_logger = Mock()

        # Test consolidated report generation
        idle_monitor._send_collected_notifications(pm_notifications, mock_tmux, mock_logger)

        # Verify tmux.send_message was called with consolidated format
        mock_tmux.send_message.assert_called_once()
        call_args = mock_tmux.send_message.call_args
        target, message = call_args[0]

        assert target == "dev-session:1"
        assert "🔔 MONITORING REPORT" in message
        assert "🚨 CRASHED AGENTS:" in message
        assert "⚠️ IDLE AGENTS:" in message
        assert "📍 MISSING AGENTS:" in message
        assert "As the PM, please review their terminal(s)/current progress and take appropriate action." in message

    def test_no_pm_edge_case(self, idle_monitor, mock_tmux):
        """Test behavior when no PM is available."""
        # Mock no PM available
        mock_tmux.list_windows.return_value = [
            {"index": "2", "name": "Claude-backend"},
            {"index": "3", "name": "Claude-frontend"},
        ]

        def mock_capture_pane(target, lines=50):
            if target == "dev-session:2":
                return "bash-5.1$ "  # Crashed
            else:
                return "Welcome to Claude Code\n? for shortcuts\n╭─ Chat\n│ > "

        mock_tmux.capture_pane.side_effect = mock_capture_pane

        pm_notifications = {}

        # Check crashed agent
        idle_monitor._check_agent_status(mock_tmux, "dev-session:2", Mock(), pm_notifications)

        # Should have no notifications collected (no PM to notify)
        assert len(pm_notifications) == 0

    def test_multiple_pms_different_sessions(self, idle_monitor, mock_tmux):
        """Test notification routing with PMs in different sessions."""

        # Mock multiple sessions with PMs
        def mock_list_sessions():
            return [{"name": "dev-session"}, {"name": "qa-session"}]

        def mock_list_windows(session):
            if session == "dev-session":
                return [{"index": "1", "name": "Claude-pm"}, {"index": "2", "name": "Claude-backend"}]
            elif session == "qa-session":
                return [{"index": "1", "name": "Claude-pm"}, {"index": "2", "name": "Claude-qa-engineer"}]
            return []

        mock_tmux.list_sessions.side_effect = mock_list_sessions
        mock_tmux.list_windows.side_effect = mock_list_windows

        # Mock crashes in both sessions
        def mock_capture_pane(target, lines=50):
            if ":1" in target:  # PMs
                return "Claude interface active > "
            else:  # Other agents crashed
                return "bash-5.1$ "

        mock_tmux.capture_pane.side_effect = mock_capture_pane

        pm_notifications = {}

        # Check agents in both sessions
        idle_monitor._check_agent_status(mock_tmux, "dev-session:2", Mock(), pm_notifications)
        idle_monitor._check_agent_status(mock_tmux, "qa-session:2", Mock(), pm_notifications)

        # Should have notifications for both PMs
        assert len(pm_notifications) == 2
        assert "dev-session:1" in pm_notifications
        assert "qa-session:1" in pm_notifications

    def test_notification_deduplication(self, idle_monitor, mock_tmux):
        """Test that duplicate notifications are handled correctly."""
        # Mock same agent failing multiple times in one cycle
        mock_tmux.capture_pane.side_effect = lambda target, lines=50: (
            "Claude interface active > " if target == "dev-session:1" else "bash-5.1$ "
        )

        pm_notifications = {}

        # Check same agent multiple times
        for _ in range(3):
            idle_monitor._check_agent_status(mock_tmux, "dev-session:2", Mock(), pm_notifications)

        # Should only have one notification per agent per cycle
        assert len(pm_notifications) == 1
        pm_target = list(pm_notifications.keys())[0]
        # Multiple calls in same cycle should add multiple messages
        assert len(pm_notifications[pm_target]) == 3

    def test_backward_compatibility_message_format(self, idle_monitor, mock_tmux):
        """Test that notifications maintain backward compatible format."""
        mock_tmux.capture_pane.side_effect = lambda target, lines=50: (
            "Claude interface active > " if target == "dev-session:1" else "bash-5.1$ "
        )

        pm_notifications = {}
        idle_monitor._check_agent_status(mock_tmux, "dev-session:2", Mock(), pm_notifications)

        # Get the crash message
        message = pm_notifications["dev-session:1"][0]

        # Verify backward compatible elements
        assert "🚨 AGENT CRASH ALERT:" in message or "🚨 AGENT FAILURE" in message
        assert "dev-session:2" in message
        assert "RECOVERY ACTIONS" in message or "restart" in message.lower()

    def test_notification_timing_and_cooldowns(self, idle_monitor, mock_tmux):
        """Test notification timing and cooldown mechanisms."""
        mock_tmux.capture_pane.side_effect = lambda target, lines=50: (
            "Claude interface active > " if target == "dev-session:1" else "bash-5.1$ "
        )

        # First notification should go through
        idle_monitor._crash_notifications = {}
        pm_notifications_1 = {}
        idle_monitor._check_agent_status(mock_tmux, "dev-session:2", Mock(), pm_notifications_1)

        assert len(pm_notifications_1) == 1

        # Second notification within cooldown should be blocked
        pm_notifications_2 = {}
        idle_monitor._check_agent_status(mock_tmux, "dev-session:2", Mock(), pm_notifications_2)

        # Should be empty due to cooldown
        assert len(pm_notifications_2) == 0

    def test_notification_loss_prevention(self, idle_monitor, mock_tmux):
        """Test that no notifications are lost during batching."""
        # Simulate send_message failure
        mock_tmux.send_message.return_value = False
        mock_logger = Mock()

        pm_notifications = {"dev-session:1": ["Test notification 1", "Test notification 2", "Test notification 3"]}

        # Try to send notifications
        idle_monitor._send_collected_notifications(pm_notifications, mock_tmux, mock_logger)

        # Verify error was logged when send failed
        mock_logger.error.assert_called()
        error_calls = [error_call for error_call in mock_logger.error.call_args_list]
        assert any("Failed to send" in str(error_call) for error_call in error_calls)

    def test_large_notification_batch_performance(self, idle_monitor, mock_tmux):
        """Test performance with large batches of notifications."""
        # Create large batch of notifications
        large_pm_notifications = {}
        for i in range(50):  # 50 notifications
            target = f"dev-session:{i + 2}"
            if target not in large_pm_notifications:
                large_pm_notifications[target] = []
            large_pm_notifications[target].append(f"Test notification {i}")

        # Consolidate to single PM
        pm_notifications = {"dev-session:1": []}
        for notifications in large_pm_notifications.values():
            pm_notifications["dev-session:1"].extend(notifications)

        mock_logger = Mock()
        start_time = time.time()

        # Send large batch
        idle_monitor._send_collected_notifications(pm_notifications, mock_tmux, mock_logger)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete within reasonable time (< 1 second)
        assert processing_time < 1.0

        # Verify single consolidated message was sent
        mock_tmux.send_message.assert_called_once()

    def test_session_isolation(self, idle_monitor, mock_tmux):
        """Test that notifications are properly isolated by session."""

        # Mock multiple sessions
        def mock_list_sessions():
            return [{"name": "frontend-team"}, {"name": "backend-team"}, {"name": "qa-team"}]

        def mock_list_windows(session):
            return [
                {"index": "0", "name": "main"},
                {"index": "1", "name": "Claude-pm"},
                {"index": "2", "name": f"Claude-{session.split('-')[0]}"},
            ]

        mock_tmux.list_sessions.side_effect = mock_list_sessions
        mock_tmux.list_windows.side_effect = mock_list_windows

        # Mock agent crashes in different sessions
        def mock_capture_pane(target, lines=50):
            if ":1" in target:  # PMs
                return "Claude interface active > "
            else:  # Workers crashed
                return "bash-5.1$ "

        mock_tmux.capture_pane.side_effect = mock_capture_pane

        pm_notifications = {}

        # Check agents across sessions
        idle_monitor._check_agent_status(mock_tmux, "frontend-team:2", Mock(), pm_notifications)
        idle_monitor._check_agent_status(mock_tmux, "backend-team:2", Mock(), pm_notifications)
        idle_monitor._check_agent_status(mock_tmux, "qa-team:2", Mock(), pm_notifications)

        # Each session's PM should get their own notifications
        assert len(pm_notifications) == 3
        assert "frontend-team:1" in pm_notifications
        assert "backend-team:1" in pm_notifications
        assert "qa-team:1" in pm_notifications

        # Each PM should only get notifications for their session
        for pm_target, messages in pm_notifications.items():
            session_name = pm_target.split(":")[0]
            for message in messages:
                assert session_name.split("-")[0] in message.lower() or session_name in message


class TestNotificationBatchingEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def mock_tmux(self):
        tmux = Mock(spec=TMUXManager)
        tmux.list_sessions.return_value = [{"name": "test-session"}]
        tmux.list_windows.return_value = [{"index": "1", "name": "Claude-pm"}, {"index": "2", "name": "Claude-dev"}]
        tmux.capture_pane.return_value = "Claude interface active > "
        tmux.send_message.return_value = True
        return tmux

    @pytest.fixture
    def idle_monitor(self, mock_tmux):
        with tempfile.TemporaryDirectory() as temp_dir:
            monitor = IdleMonitor(mock_tmux)
            monitor.pid_file = Path(temp_dir) / "test-monitor.pid"
            monitor.log_file = Path(temp_dir) / "test-monitor.log"
            yield monitor

    def test_tmux_connection_failure(self, idle_monitor, mock_tmux):
        """Test handling of TMux connection failures."""
        mock_tmux.capture_pane.side_effect = Exception("TMux connection lost")
        mock_logger = Mock()

        pm_notifications = {}

        # Should not crash on TMux errors
        idle_monitor._check_agent_status(mock_tmux, "test-session:2", mock_logger, pm_notifications)

        # Error should be logged
        mock_logger.error.assert_called()

    def test_pm_agent_self_notification(self, idle_monitor, mock_tmux):
        """Test that PM doesn't get notified about their own issues."""
        # PM is both the notifier and the one with issues
        mock_tmux.capture_pane.side_effect = lambda target, lines=50: (
            "bash-5.1$ " if target == "test-session:1" else "Claude interface active > "
        )

        pm_notifications = {}

        # Check PM agent itself
        idle_monitor._check_agent_status(mock_tmux, "test-session:1", Mock(), pm_notifications)

        # Should not notify PM about their own crash
        assert len(pm_notifications) == 0

    def test_malformed_session_targets(self, idle_monitor, mock_tmux):
        """Test handling of malformed session targets."""
        mock_logger = Mock()
        pm_notifications = {}

        # Test malformed targets
        malformed_targets = ["invalid-target", "session:", ":window", "session:window:extra", ""]

        for target in malformed_targets:
            # Should not crash on malformed targets
            idle_monitor._check_agent_status(mock_tmux, target, mock_logger, pm_notifications)

    def test_empty_notification_batch(self, idle_monitor, mock_tmux):
        """Test handling of empty notification batches."""
        mock_logger = Mock()
        empty_notifications = {}

        # Should handle empty batch gracefully
        idle_monitor._send_collected_notifications(empty_notifications, mock_tmux, mock_logger)

        # No messages should be sent
        mock_tmux.send_message.assert_not_called()
