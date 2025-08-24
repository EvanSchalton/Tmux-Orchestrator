"""
Comprehensive tests for NotificationManager class.

Tests the extracted notification management functionality to ensure
no functionality loss during refactoring.
"""

import logging
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.notification_manager import NotificationManager
from tmux_orchestrator.core.monitoring.types import IdleType, NotificationEvent, NotificationType
from tmux_orchestrator.utils.tmux import TMUXManager


class TestNotificationManagerInitialization:
    """Test NotificationManager initialization and basic functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.notification_manager = NotificationManager(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_initialization_success(self):
        """Test successful NotificationManager initialization."""
        result = self.notification_manager.initialize()

        assert result is True
        self.logger.info.assert_called_with("Initializing NotificationManager")

    def test_initialization_failure(self):
        """Test NotificationManager initialization failure."""
        # Patch initialization to fail
        with patch.object(self.notification_manager, "logger") as mock_logger:
            mock_logger.info.side_effect = Exception("Initialization failed")

            result = self.notification_manager.initialize()

            assert result is False

    def test_cleanup(self):
        """Test NotificationManager cleanup."""
        # Add some data to queues
        self.notification_manager._queued_notifications.append(Mock())
        self.notification_manager._pm_notifications["test:1"] = ["test message"]

        self.notification_manager.cleanup()

        assert len(self.notification_manager._queued_notifications) == 0
        assert len(self.notification_manager._pm_notifications) == 0
        self.logger.info.assert_called_with("Cleaning up NotificationManager")


class TestNotificationQueuing:
    """Test notification queuing functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.notification_manager = NotificationManager(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_queue_notification_success(self):
        """Test successful notification queuing."""
        event = NotificationEvent(
            type=NotificationType.AGENT_CRASH,
            target="test:1",
            message="Test crash message",
            timestamp=datetime.now(),
            session="test",
            metadata={},
        )

        self.notification_manager.queue_notification(event)

        assert len(self.notification_manager._queued_notifications) == 1
        assert self.notification_manager._queued_notifications[0] == event

    def test_queue_notification_throttling(self):
        """Test notification throttling for duplicates."""
        event1 = NotificationEvent(
            type=NotificationType.AGENT_CRASH,
            target="test:1",
            message="First crash message",
            timestamp=datetime.now(),
            session="test",
            metadata={},
        )

        event2 = NotificationEvent(
            type=NotificationType.AGENT_CRASH,
            target="test:1",
            message="Second crash message",
            timestamp=datetime.now(),
            session="test",
            metadata={},
        )

        # Queue first notification
        self.notification_manager.queue_notification(event1)
        assert len(self.notification_manager._queued_notifications) == 1

        # Second notification should be throttled
        self.notification_manager.queue_notification(event2)
        assert len(self.notification_manager._queued_notifications) == 1  # Still only 1

    def test_queue_notification_different_types(self):
        """Test queuing different notification types."""
        crash_event = NotificationEvent(
            type=NotificationType.AGENT_CRASH,
            target="test:1",
            message="Crash message",
            timestamp=datetime.now(),
            session="test",
            metadata={},
        )

        idle_event = NotificationEvent(
            type=NotificationType.AGENT_IDLE,
            target="test:1",
            message="Idle message",
            timestamp=datetime.now(),
            session="test",
            metadata={},
        )

        self.notification_manager.queue_notification(crash_event)
        self.notification_manager.queue_notification(idle_event)

        # Different types should both be queued
        assert len(self.notification_manager._queued_notifications) == 2


class TestSpecificNotificationTypes:
    """Test specific notification type methods."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.notification_manager = NotificationManager(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_notify_agent_crash(self):
        """Test agent crash notification."""
        self.notification_manager.notify_agent_crash(
            target="test:1", error_type="rate_limit", session="test", metadata={"additional": "info"}
        )

        assert len(self.notification_manager._queued_notifications) == 1
        event = self.notification_manager._queued_notifications[0]

        assert event.type == NotificationType.AGENT_CRASH
        assert event.target == "test:1"
        assert "AGENT CRASH" in event.message
        assert "rate_limit" in event.message
        assert event.metadata["error_type"] == "rate_limit"

    def test_notify_agent_idle(self):
        """Test agent idle notification."""
        self.notification_manager.notify_agent_idle(target="test:1", idle_type=IdleType.NEWLY_IDLE, session="test")

        assert len(self.notification_manager._queued_notifications) == 1
        event = self.notification_manager._queued_notifications[0]

        assert event.type == NotificationType.AGENT_IDLE
        assert event.target == "test:1"
        assert "AGENT IDLE" in event.message
        assert event.metadata["idle_type"] == "newly_idle"

    def test_notify_agent_idle_compaction_skip(self):
        """Test that compaction state idle notifications are skipped."""
        self.notification_manager.notify_agent_idle(
            target="test:1", idle_type=IdleType.COMPACTION_STATE, session="test"
        )

        # Should not queue notification for compaction state
        assert len(self.notification_manager._queued_notifications) == 0

    def test_notify_fresh_agent(self):
        """Test fresh agent notification."""
        self.notification_manager.notify_fresh_agent(target="test:1", session="test")

        assert len(self.notification_manager._queued_notifications) == 1
        event = self.notification_manager._queued_notifications[0]

        assert event.type == NotificationType.AGENT_FRESH
        assert event.target == "test:1"
        assert "FRESH AGENT ALERT" in event.message

    def test_notify_team_idle(self):
        """Test team idle notification."""
        self.notification_manager.notify_team_idle(session="test", agent_count=3)

        assert len(self.notification_manager._queued_notifications) == 1
        event = self.notification_manager._queued_notifications[0]

        assert event.type == NotificationType.TEAM_IDLE
        assert event.target == "test"
        assert "TEAM IDLE" in event.message
        assert event.metadata["agent_count"] == 3

    def test_notify_recovery_needed(self):
        """Test recovery needed notification."""
        self.notification_manager.notify_recovery_needed(target="test:1", issue="Agent not responding", session="test")

        assert len(self.notification_manager._queued_notifications) == 1
        event = self.notification_manager._queued_notifications[0]

        assert event.type == NotificationType.RECOVERY_NEEDED
        assert event.target == "test:1"
        assert "RECOVERY NEEDED" in event.message
        assert event.metadata["issue"] == "Agent not responding"


class TestPMDiscovery:
    """Test PM discovery functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.notification_manager = NotificationManager(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_find_pm_in_session_success(self):
        """Test successful PM discovery in session."""
        self.tmux.list_windows.return_value = [
            {"index": "0", "name": "shell"},
            {"index": "1", "name": "pm"},
            {"index": "2", "name": "developer"},
        ]

        pm_target = self.notification_manager._find_pm_in_session("test")

        assert pm_target == "test:1"

    def test_find_pm_in_session_project_manager(self):
        """Test PM discovery with 'project-manager' name."""
        self.tmux.list_windows.return_value = [
            {"index": "0", "name": "shell"},
            {"index": "1", "name": "project-manager"},
            {"index": "2", "name": "developer"},
        ]

        pm_target = self.notification_manager._find_pm_in_session("test")

        assert pm_target == "test:1"

    def test_find_pm_in_session_not_found(self):
        """Test PM discovery when no PM exists."""
        self.tmux.list_windows.return_value = [
            {"index": "0", "name": "shell"},
            {"index": "1", "name": "developer"},
            {"index": "2", "name": "qa"},
        ]

        pm_target = self.notification_manager._find_pm_in_session("test")

        assert pm_target is None

    def test_find_pm_in_session_error(self):
        """Test PM discovery error handling."""
        self.tmux.list_windows.side_effect = Exception("Window listing failed")

        pm_target = self.notification_manager._find_pm_in_session("test")

        assert pm_target is None
        self.logger.error.assert_called()


class TestNotificationBatching:
    """Test notification batching and collection."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.notification_manager = NotificationManager(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_collect_notification_for_pm_success(self):
        """Test successful notification collection for PM."""
        # Mock PM discovery
        self.tmux.list_windows.return_value = [{"index": "1", "name": "pm"}]

        event = NotificationEvent(
            type=NotificationType.AGENT_CRASH,
            target="test:2",
            message="🚨 AGENT CRASH: test:2 - rate_limit",
            timestamp=datetime.now(),
            session="test",
            metadata={},
        )

        self.notification_manager._collect_notification_for_pm(event)

        # Should collect for PM
        assert "test:1" in self.notification_manager._pm_notifications
        assert len(self.notification_manager._pm_notifications["test:1"]) == 1

    def test_collect_notification_for_pm_no_pm(self):
        """Test notification collection when no PM exists."""
        # Mock no PM in session
        self.tmux.list_windows.return_value = [{"index": "1", "name": "developer"}]

        event = NotificationEvent(
            type=NotificationType.AGENT_CRASH,
            target="test:2",
            message="Test message",
            timestamp=datetime.now(),
            session="test",
            metadata={},
        )

        self.notification_manager._collect_notification_for_pm(event)

        # Should not collect anything
        assert len(self.notification_manager._pm_notifications) == 0

    def test_send_queued_notifications_empty(self):
        """Test sending queued notifications when queue is empty."""
        sent_count = self.notification_manager.send_queued_notifications()

        assert sent_count == 0

    def test_send_queued_notifications_with_pm(self):
        """Test sending queued notifications to PM."""
        # Mock PM discovery
        self.tmux.list_windows.return_value = [{"index": "1", "name": "pm"}]

        # Queue some notifications
        self.notification_manager.notify_agent_crash("test:2", "rate_limit", "test")
        self.notification_manager.notify_agent_idle("test:3", IdleType.NEWLY_IDLE, "test")

        sent_count = self.notification_manager.send_queued_notifications()

        assert sent_count == 1  # One report sent to PM
        assert len(self.notification_manager._queued_notifications) == 0  # Queue cleared

        # Verify tmux.send_keys was called
        self.tmux.send_keys.assert_called_once()


class TestNotificationReportGeneration:
    """Test consolidated notification report generation."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.notification_manager = NotificationManager(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_send_collected_notifications_grouping(self):
        """Test that notifications are properly grouped in reports."""
        # Add different types of messages to PM collection
        pm_target = "test:1"
        self.notification_manager._pm_notifications[pm_target] = [
            "🚨 AGENT CRASH: test:2 - rate_limit",
            "🌱 FRESH AGENT ALERT: test:3 - Ready for briefing",
            "💤 AGENT IDLE: test:4 - newly_idle",
            "🔧 RECOVERY NEEDED: test:5 - Not responding",
            "❌ MISSING: test:6 - Agent disappeared",
        ]

        sent_count = self.notification_manager._send_collected_notifications()

        assert sent_count == 1

        # Verify send_keys was called with grouped report
        self.tmux.send_keys.assert_called_once()
        call_args = self.tmux.send_keys.call_args[0]
        report_content = call_args[1]

        # Verify report contains sections
        assert "🔔 MONITORING REPORT" in report_content
        assert "🚨 CRITICAL - Agent Crashes:" in report_content
        assert "🔧 RECOVERY NEEDED:" in report_content
        assert "🌱 Fresh Agents" in report_content
        assert "💤 Idle Agents:" in report_content

    def test_send_collected_notifications_error_handling(self):
        """Test error handling during notification sending."""
        pm_target = "test:1"
        self.notification_manager._pm_notifications[pm_target] = ["Test message"]

        # Mock send_keys to fail
        self.tmux.send_keys.side_effect = Exception("Send failed")

        sent_count = self.notification_manager._send_collected_notifications()

        assert sent_count == 0
        self.logger.error.assert_called()

    def test_send_collected_notifications_empty_messages(self):
        """Test handling of empty message collections."""
        pm_target = "test:1"
        self.notification_manager._pm_notifications[pm_target] = []

        sent_count = self.notification_manager._send_collected_notifications()

        assert sent_count == 0
        self.tmux.send_keys.assert_not_called()


class TestNotificationStatistics:
    """Test notification statistics functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.notification_manager = NotificationManager(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_get_notification_stats_empty(self):
        """Test notification statistics when empty."""
        stats = self.notification_manager.get_notification_stats()

        assert stats["queued_notifications"] == 0
        assert stats["pm_collections"] == 0
        assert stats["total_pm_messages"] == 0

    def test_get_notification_stats_with_data(self):
        """Test notification statistics with data."""
        # Add queued notifications
        self.notification_manager.notify_agent_crash("test:1", "error", "test")
        self.notification_manager.notify_agent_idle("test:2", IdleType.NEWLY_IDLE, "test")

        # Add PM collections
        self.notification_manager._pm_notifications["pm:1"] = ["msg1", "msg2"]
        self.notification_manager._pm_notifications["pm:2"] = ["msg3"]

        stats = self.notification_manager.get_notification_stats()

        assert stats["queued_notifications"] == 2
        assert stats["pm_collections"] == 2
        assert stats["total_pm_messages"] == 3


class TestNotificationThrottling:
    """Test notification throttling to prevent spam."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.notification_manager = NotificationManager(self.tmux, self.config, self.logger)
        # Set short cooldown for testing
        self.notification_manager._notification_cooldown = 1  # 1 second

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_throttling_same_notification(self):
        """Test throttling of identical notifications."""
        # Send first notification
        self.notification_manager.notify_agent_crash("test:1", "error", "test")
        assert len(self.notification_manager._queued_notifications) == 1

        # Send identical notification immediately - should be throttled
        self.notification_manager.notify_agent_crash("test:1", "error", "test")
        assert len(self.notification_manager._queued_notifications) == 1  # Still only 1

    @patch("time.sleep")
    def test_throttling_timeout(self, mock_sleep):
        """Test that throttling expires after cooldown period."""
        # Send first notification
        self.notification_manager.notify_agent_crash("test:1", "error", "test")
        assert len(self.notification_manager._queued_notifications) == 1

        # Simulate time passing by modifying the last notification time
        notification_key = "agent_crash:test:1"
        first_time = self.notification_manager._last_notification_times[notification_key]
        self.notification_manager._last_notification_times[notification_key] = first_time - timedelta(
            seconds=2
        )  # 2 seconds ago

        # Send same notification type - should not be throttled now
        self.notification_manager.notify_agent_crash("test:1", "error", "test")
        assert len(self.notification_manager._queued_notifications) == 2  # Now 2

    def test_throttling_different_targets(self):
        """Test that different targets are not throttled."""
        # Send notifications for different targets
        self.notification_manager.notify_agent_crash("test:1", "error", "test")
        self.notification_manager.notify_agent_crash("test:2", "error", "test")

        # Both should be queued
        assert len(self.notification_manager._queued_notifications) == 2
