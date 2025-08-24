"""
Comprehensive tests for ComponentManager.

Tests the coordination between AgentMonitor, NotificationManager, and StateTracker
to ensure complete monitoring workflow functionality.
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.component_manager import ComponentManager, MonitorCycleResult
from tmux_orchestrator.core.monitoring.types import IdleType
from tmux_orchestrator.utils.tmux import TMUXManager


class TestComponentManagerInitialization:
    """Test ComponentManager initialization and basic functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()

        self.component_manager = ComponentManager(self.tmux, self.config)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_initialization_success(self):
        """Test successful ComponentManager initialization."""
        # Mock successful component initialization
        with (
            patch.object(self.component_manager.agent_monitor, "initialize", return_value=True),
            patch.object(self.component_manager.notification_manager, "initialize", return_value=True),
            patch.object(self.component_manager.state_tracker, "initialize", return_value=True),
        ):
            result = self.component_manager.initialize()

            assert result is True
            assert self.component_manager._start_time is not None

    def test_initialization_failure(self):
        """Test ComponentManager initialization failure."""
        # Mock component initialization failure
        with patch.object(self.component_manager.agent_monitor, "initialize", return_value=False):
            result = self.component_manager.initialize()

            assert result is False

    def test_cleanup(self):
        """Test ComponentManager cleanup."""
        self.component_manager._is_running = True

        with (
            patch.object(self.component_manager.agent_monitor, "cleanup"),
            patch.object(self.component_manager.notification_manager, "cleanup"),
            patch.object(self.component_manager.state_tracker, "cleanup"),
        ):
            self.component_manager.cleanup()

            assert self.component_manager._is_running is False
            assert self.component_manager._start_time is None

    def test_start_monitoring_success(self):
        """Test successful monitoring start."""
        with patch.object(self.component_manager, "initialize", return_value=True):
            result = self.component_manager.start_monitoring()

            assert result is True
            assert self.component_manager._is_running is True

    def test_start_monitoring_already_running(self):
        """Test starting monitoring when already running."""
        self.component_manager._is_running = True

        result = self.component_manager.start_monitoring()

        assert result is True

    def test_stop_monitoring_success(self):
        """Test successful monitoring stop."""
        self.component_manager._is_running = True

        with patch.object(self.component_manager, "cleanup"):
            result = self.component_manager.stop_monitoring()

            assert result is True
            assert self.component_manager._is_running is False

    def test_stop_monitoring_not_running(self):
        """Test stopping monitoring when not running."""
        self.component_manager._is_running = False

        result = self.component_manager.stop_monitoring()

        assert result is True


class TestMonitoringCycle:
    """Test complete monitoring cycle execution."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()

        self.component_manager = ComponentManager(self.tmux, self.config)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_execute_monitoring_cycle_success(self):
        """Test successful monitoring cycle execution."""
        # Mock agent discovery
        mock_agents = [
            Mock(target="test:1", session="test", name="agent1", type="Developer"),
            Mock(target="test:2", session="test", name="agent2", type="QA"),
        ]

        # Mock analysis results
        mock_analysis = Mock(is_idle=False, idle_type=IdleType.UNKNOWN, error_detected=False, content_hash="abc123")

        with (
            patch.object(self.component_manager.agent_monitor, "discover_agents", return_value=mock_agents),
            patch.object(self.component_manager.agent_monitor, "analyze_agent_content", return_value=mock_analysis),
            patch.object(self.component_manager.state_tracker, "track_session_agent"),
            patch.object(self.component_manager.state_tracker, "update_agent_state"),
            patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=0),
        ):
            result = self.component_manager.execute_monitoring_cycle()

            assert isinstance(result, MonitorCycleResult)
            assert result.success is True
            assert result.agents_discovered == 2
            assert result.agents_analyzed == 2
            assert result.cycle_duration > 0

    def test_execute_monitoring_cycle_with_idle_agents(self):
        """Test monitoring cycle with idle agents."""
        # Mock agent discovery
        mock_agents = [
            Mock(target="test:1", session="test", name="agent1", type="Developer"),
        ]

        # Mock analysis - agent is idle
        mock_analysis = Mock(
            is_idle=True, idle_type=IdleType.NEWLY_IDLE, error_detected=False, content_hash="abc123", confidence=0.9
        )

        with (
            patch.object(self.component_manager.agent_monitor, "discover_agents", return_value=mock_agents),
            patch.object(self.component_manager.agent_monitor, "analyze_agent_content", return_value=mock_analysis),
            patch.object(self.component_manager.state_tracker, "track_session_agent"),
            patch.object(self.component_manager.state_tracker, "update_agent_state"),
            patch.object(self.component_manager.notification_manager, "notify_agent_idle") as mock_notify,
            patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=1),
            patch.object(self.component_manager, "_check_team_idle_status"),
        ):
            result = self.component_manager.execute_monitoring_cycle()

            assert result.success is True
            assert result.idle_agents == 1
            assert result.notifications_sent == 1
            mock_notify.assert_called_once()

    def test_execute_monitoring_cycle_with_errors(self):
        """Test monitoring cycle with agent errors."""
        # Mock agent discovery
        mock_agents = [
            Mock(target="test:1", session="test", name="agent1", type="Developer"),
        ]

        # Mock analysis - agent has error
        mock_analysis = Mock(
            is_idle=True,
            idle_type=IdleType.ERROR_STATE,
            error_detected=True,
            error_type="rate_limit",
            content_hash="abc123",
            confidence=0.8,
        )

        with (
            patch.object(self.component_manager.agent_monitor, "discover_agents", return_value=mock_agents),
            patch.object(self.component_manager.agent_monitor, "analyze_agent_content", return_value=mock_analysis),
            patch.object(self.component_manager.state_tracker, "track_session_agent"),
            patch.object(self.component_manager.state_tracker, "update_agent_state"),
            patch.object(self.component_manager.notification_manager, "notify_agent_crash") as mock_crash,
            patch.object(self.component_manager.notification_manager, "notify_recovery_needed") as mock_recovery,
            patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=2),
        ):
            result = self.component_manager.execute_monitoring_cycle()

            assert result.success is True
            mock_crash.assert_called_once()
            mock_recovery.assert_called_once()

    def test_execute_monitoring_cycle_with_fresh_agents(self):
        """Test monitoring cycle with fresh agents."""
        # Mock agent discovery
        mock_agents = [
            Mock(target="test:1", session="test", name="agent1", type="Developer"),
        ]

        # Mock analysis - fresh agent
        mock_analysis = Mock(is_idle=True, idle_type=IdleType.FRESH_AGENT, error_detected=False, content_hash="abc123")

        with (
            patch.object(self.component_manager.agent_monitor, "discover_agents", return_value=mock_agents),
            patch.object(self.component_manager.agent_monitor, "analyze_agent_content", return_value=mock_analysis),
            patch.object(self.component_manager.state_tracker, "track_session_agent"),
            patch.object(self.component_manager.state_tracker, "update_agent_state"),
            patch.object(self.component_manager.notification_manager, "notify_fresh_agent") as mock_fresh,
            patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=1),
        ):
            result = self.component_manager.execute_monitoring_cycle()

            assert result.success is True
            mock_fresh.assert_called_once()

    def test_execute_monitoring_cycle_failure(self):
        """Test monitoring cycle with failure."""
        # Mock discovery failure
        with patch.object(
            self.component_manager.agent_monitor, "discover_agents", side_effect=Exception("Discovery failed")
        ):
            result = self.component_manager.execute_monitoring_cycle()

            assert result.success is False
            assert len(result.errors) > 0
            assert "Discovery failed" in result.errors[0]


class TestTeamIdleDetection:
    """Test team-wide idle detection functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()

        self.component_manager = ComponentManager(self.tmux, self.config)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_check_team_idle_status_all_idle(self):
        """Test team idle detection when all agents are idle."""
        # Mock session agents
        mock_agents = [Mock(target="test:1"), Mock(target="test:2")]

        with (
            patch.object(self.component_manager.state_tracker, "get_session_agents", return_value=mock_agents),
            patch.object(self.component_manager.state_tracker, "is_agent_idle", return_value=True),
            patch.object(self.component_manager.state_tracker, "is_team_idle", return_value=False),
            patch.object(self.component_manager.state_tracker, "set_team_idle") as mock_set_idle,
            patch.object(self.component_manager.notification_manager, "notify_team_idle") as mock_notify,
        ):
            self.component_manager._check_team_idle_status("test")

            mock_set_idle.assert_called_once_with("test")
            mock_notify.assert_called_once()

    def test_check_team_idle_status_mixed(self):
        """Test team idle detection with mixed agent states."""
        # Mock session agents
        mock_agents = [Mock(target="test:1"), Mock(target="test:2")]

        # One idle, one active
        def mock_is_idle(target):
            return target == "test:1"

        with (
            patch.object(self.component_manager.state_tracker, "get_session_agents", return_value=mock_agents),
            patch.object(self.component_manager.state_tracker, "is_agent_idle", side_effect=mock_is_idle),
            patch.object(self.component_manager.state_tracker, "is_team_idle", return_value=True),
            patch.object(self.component_manager.state_tracker, "clear_team_idle") as mock_clear,
        ):
            self.component_manager._check_team_idle_status("test")

            mock_clear.assert_called_once_with("test")

    def test_check_team_idle_status_no_agents(self):
        """Test team idle detection with no agents."""
        with patch.object(self.component_manager.state_tracker, "get_session_agents", return_value=[]):
            # Should not raise exception
            self.component_manager._check_team_idle_status("test")


class TestPerformanceTracking:
    """Test performance tracking functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()

        self.component_manager = ComponentManager(self.tmux, self.config)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_update_performance_stats(self):
        """Test performance statistics tracking."""
        # Simulate multiple cycles
        self.component_manager._update_performance_stats(0.005)
        self.component_manager._update_performance_stats(0.010)
        self.component_manager._update_performance_stats(0.008)

        stats = self.component_manager.get_performance_stats()

        assert stats["total_cycles"] == 3
        assert stats["avg_cycle_time"] == pytest.approx(0.0077, rel=0.01)
        assert stats["min_cycle_time"] == 0.005
        assert stats["max_cycle_time"] == 0.010

    def test_performance_history_limit(self):
        """Test that performance history is limited."""
        # Add more than max history size
        for i in range(150):  # More than _max_history_size (100)
            self.component_manager._update_performance_stats(0.001 * i)

        assert len(self.component_manager._performance_history) == 100

    def test_get_performance_stats_empty(self):
        """Test performance stats when no data."""
        stats = self.component_manager.get_performance_stats()

        assert stats["avg_cycle_time"] == 0.0
        assert stats["min_cycle_time"] == 0.0
        assert stats["max_cycle_time"] == 0.0
        assert stats["total_cycles"] == 0


class TestStatusAndUtilities:
    """Test status reporting and utility methods."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()

        self.component_manager = ComponentManager(self.tmux, self.config)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_get_status_not_started(self):
        """Test status when not started."""
        with (
            patch.object(self.component_manager.agent_monitor, "get_all_cached_agents", return_value=[]),
            patch.object(self.component_manager.state_tracker, "get_all_idle_agents", return_value={}),
        ):
            status = self.component_manager.get_status()

            assert status.is_running is False
            assert status.active_agents == 0
            assert status.idle_agents == 0
            assert status.cycle_count == 0

    def test_get_status_running(self):
        """Test status when running."""
        self.component_manager._is_running = True
        self.component_manager._cycle_count = 10
        self.component_manager._last_cycle_time = 0.008

        mock_agents = [Mock(), Mock(), Mock()]
        mock_idle = {"agent1": Mock(), "agent2": Mock()}

        with (
            patch.object(self.component_manager.agent_monitor, "get_all_cached_agents", return_value=mock_agents),
            patch.object(self.component_manager.state_tracker, "get_all_idle_agents", return_value=mock_idle),
        ):
            status = self.component_manager.get_status()

            assert status.is_running is True
            assert status.active_agents == 3
            assert status.idle_agents == 2
            assert status.cycle_count == 10
            assert status.last_cycle_time == 0.008

    def test_is_agent_idle(self):
        """Test agent idle check delegation."""
        with patch.object(self.component_manager.state_tracker, "is_agent_idle", return_value=True):
            result = self.component_manager.is_agent_idle("test:1")

            assert result is True

    def test_get_agent_info(self):
        """Test agent info retrieval."""
        mock_info = Mock()

        with patch.object(self.component_manager.agent_monitor, "get_cached_agent_info", return_value=mock_info):
            result = self.component_manager.get_agent_info("test:1")

            assert result == mock_info

    def test_reset_agent_tracking(self):
        """Test agent tracking reset."""
        with patch.object(self.component_manager.state_tracker, "reset_agent_state") as mock_reset:
            self.component_manager.reset_agent_tracking("test:1")

            mock_reset.assert_called_once_with("test:1")

    def test_force_notification_send(self):
        """Test forced notification sending."""
        with patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=5):
            result = self.component_manager.force_notification_send()

            assert result == 5


class TestMonitorCycleResult:
    """Test MonitorCycleResult functionality."""

    def test_monitor_cycle_result_initialization(self):
        """Test MonitorCycleResult initialization."""
        result = MonitorCycleResult()

        assert result.agents_discovered == 0
        assert result.agents_analyzed == 0
        assert result.idle_agents == 0
        assert result.notifications_sent == 0
        assert result.cycle_duration == 0.0
        assert result.errors == []
        assert result.success is True

    def test_monitor_cycle_result_with_errors(self):
        """Test MonitorCycleResult with errors."""
        result = MonitorCycleResult()
        result.add_error("Test error")
        result.add_error("Another error")

        assert len(result.errors) == 2
        assert result.success is False
        assert "Test error" in result.errors
        assert "Another error" in result.errors
