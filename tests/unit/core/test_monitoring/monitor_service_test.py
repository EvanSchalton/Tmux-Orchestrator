"""Tests for the MonitorService facade."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.monitor_service import MonitorService
from tmux_orchestrator.core.monitoring.types import AgentInfo, MonitorStatus
from tmux_orchestrator.utils.tmux import TMUXManager


class TestMonitorService:
    """Test suite for MonitorService facade."""

    @pytest.fixture
    def mock_tmux(self):
        """Create a mock TMUXManager."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane = Mock(return_value="Normal pane content")
        return tmux

    @pytest.fixture
    def mock_config(self):
        """Create a mock Config."""
        config = Mock(spec=Config)
        config.check_interval = 30
        return config

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()

    @pytest.fixture
    def monitor_service(self, mock_tmux, mock_config, mock_logger):
        """Create a MonitorService instance with mocks."""
        with patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager"):
            with patch("tmux_orchestrator.core.monitoring.monitor_service.HealthChecker"):
                with patch("tmux_orchestrator.core.monitoring.monitor_service.AgentMonitor"):
                    with patch("tmux_orchestrator.core.monitoring.monitor_service.NotificationManager"):
                        with patch("tmux_orchestrator.core.monitoring.monitor_service.StateTracker"):
                            with patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager"):
                                service = MonitorService(mock_tmux, mock_config, mock_logger)
                                return service

    def test_initialization(self, monitor_service):
        """Test MonitorService initialization."""
        assert monitor_service.is_running is False
        assert monitor_service.start_time is None
        assert monitor_service.cycle_count == 0
        assert monitor_service.errors_detected == 0
        assert monitor_service.check_interval == 30

    def test_initialize_components(self, monitor_service):
        """Test component initialization."""
        # Mock all component initialize methods
        monitor_service.daemon_manager.initialize.return_value = True
        monitor_service.health_checker.initialize.return_value = True
        monitor_service.agent_monitor.initialize.return_value = True
        monitor_service.notification_manager.initialize.return_value = True
        monitor_service.state_tracker.initialize.return_value = True
        monitor_service.pm_recovery_manager.initialize.return_value = True

        assert monitor_service.initialize() is True

        # Verify all components were initialized
        monitor_service.daemon_manager.initialize.assert_called_once()
        monitor_service.health_checker.initialize.assert_called_once()
        monitor_service.agent_monitor.initialize.assert_called_once()
        monitor_service.notification_manager.initialize.assert_called_once()
        monitor_service.state_tracker.initialize.assert_called_once()
        monitor_service.pm_recovery_manager.initialize.assert_called_once()

    def test_initialize_component_failure(self, monitor_service):
        """Test initialization failure when a component fails."""
        monitor_service.daemon_manager.initialize.return_value = False

        assert monitor_service.initialize() is False

    def test_cleanup(self, monitor_service):
        """Test cleanup of all components."""
        monitor_service.cleanup()

        # Verify all components were cleaned up in reverse order
        monitor_service.pm_recovery_manager.cleanup.assert_called_once()
        monitor_service.state_tracker.cleanup.assert_called_once()
        monitor_service.notification_manager.cleanup.assert_called_once()
        monitor_service.agent_monitor.cleanup.assert_called_once()
        monitor_service.health_checker.cleanup.assert_called_once()
        monitor_service.daemon_manager.cleanup.assert_called_once()

    def test_cleanup_with_errors(self, monitor_service):
        """Test cleanup continues even if components raise errors."""
        monitor_service.health_checker.cleanup.side_effect = Exception("Cleanup error")

        # Should not raise
        monitor_service.cleanup()

        # Other components should still be cleaned up
        monitor_service.pm_recovery_manager.cleanup.assert_called_once()
        monitor_service.daemon_manager.cleanup.assert_called_once()

    def test_set_idle_monitor(self, monitor_service):
        """Test setting idle monitor."""
        mock_idle_monitor = Mock()

        monitor_service.set_idle_monitor(mock_idle_monitor)

        assert monitor_service.idle_monitor == mock_idle_monitor
        monitor_service.health_checker.set_idle_monitor.assert_called_once_with(mock_idle_monitor)

    def test_start_success(self, monitor_service):
        """Test successful start."""
        monitor_service.initialize = Mock(return_value=True)
        monitor_service.daemon_manager.is_running.return_value = False
        monitor_service.daemon_manager.start.return_value = True

        assert monitor_service.start() is True
        assert monitor_service.is_running is True
        assert monitor_service.start_time is not None

        monitor_service.initialize.assert_called_once()
        monitor_service.daemon_manager.start.assert_called_once()

    def test_start_already_running(self, monitor_service):
        """Test start when already running."""
        monitor_service.is_running = True

        assert monitor_service.start() is True

        # Should not try to initialize or start daemon
        monitor_service.daemon_manager.start.assert_not_called()

    def test_start_initialization_failure(self, monitor_service):
        """Test start failure due to initialization."""
        monitor_service.initialize = Mock(return_value=False)

        assert monitor_service.start() is False
        assert monitor_service.is_running is False

    def test_start_daemon_failure(self, monitor_service):
        """Test start failure due to daemon start."""
        monitor_service.initialize = Mock(return_value=True)
        monitor_service.daemon_manager.is_running.return_value = False
        monitor_service.daemon_manager.start.return_value = False

        assert monitor_service.start() is False
        assert monitor_service.is_running is False

    def test_stop_success(self, monitor_service):
        """Test successful stop."""
        monitor_service.is_running = True
        monitor_service.daemon_manager.is_running.return_value = True
        monitor_service.cleanup = Mock()

        assert monitor_service.stop() is True
        assert monitor_service.is_running is False

        monitor_service.daemon_manager.stop.assert_called_once()
        monitor_service.cleanup.assert_called_once()

    def test_stop_not_running(self, monitor_service):
        """Test stop when not running."""
        monitor_service.is_running = False

        assert monitor_service.stop() is True

        monitor_service.daemon_manager.stop.assert_not_called()

    def test_status(self, monitor_service):
        """Test getting monitor status."""
        monitor_service.is_running = True
        monitor_service.start_time = datetime.now() - timedelta(minutes=5)
        monitor_service.cycle_count = 10
        monitor_service.last_cycle_time = 0.05
        monitor_service.errors_detected = 2

        # Mock health checker statuses
        monitor_service.health_checker.get_all_agent_statuses.return_value = {
            "session1:1": Mock(is_idle=True),
            "session1:2": Mock(is_idle=False),
            "session2:1": Mock(is_idle=False),
        }

        status = monitor_service.status()

        assert isinstance(status, MonitorStatus)
        assert status.is_running is True
        assert status.active_agents == 2
        assert status.idle_agents == 1
        assert status.last_cycle_time == 0.05
        assert status.cycle_count == 10
        assert status.errors_detected == 2
        assert status.uptime.total_seconds() >= 300  # At least 5 minutes

    def test_check_health_specific_window(self, monitor_service):
        """Test health check for specific window."""
        mock_status = Mock(
            status="healthy", is_responsive=True, is_idle=False, consecutive_failures=0, last_response=datetime.now()
        )
        monitor_service.health_checker.check_agent_health.return_value = mock_status

        result = monitor_service.check_health("session1", "2")

        assert result["target"] == "session1:2"
        assert result["status"] == "healthy"
        assert result["is_responsive"] is True
        assert result["is_idle"] is False
        assert result["consecutive_failures"] == 0

        monitor_service.health_checker.check_agent_health.assert_called_once_with("session1:2")

    def test_check_health_session(self, monitor_service):
        """Test health check for entire session."""
        # Mock discovered agents
        agents = [
            AgentInfo(target="session1:1", session="session1", window="1", name="PM", type="pm", status="active"),
            AgentInfo(target="session1:2", session="session1", window="2", name="Dev", type="dev", status="active"),
        ]
        monitor_service.agent_monitor.discover_agents.return_value = agents

        # Mock health statuses
        def mock_health_check(target):
            status = Mock()
            if target == "session1:1":
                status.status = "healthy"
                status.is_responsive = True
                status.is_idle = False
            else:
                status.status = "warning"
                status.is_responsive = True
                status.is_idle = True
            return status

        monitor_service.health_checker.check_agent_health.side_effect = mock_health_check

        result = monitor_service.check_health("session1")

        assert len(result) == 2
        assert result["session1:1"]["status"] == "healthy"
        assert result["session1:2"]["status"] == "warning"

    def test_handle_recovery_pm(self, monitor_service):
        """Test recovery handling for PM."""
        monitor_service.pm_recovery_manager.handle_recovery.return_value = True

        result = monitor_service.handle_recovery("session1", "1")

        assert result is True
        monitor_service.pm_recovery_manager.handle_recovery.assert_called_once_with("session1")

    def test_handle_recovery_non_pm_needs_recovery(self, monitor_service):
        """Test recovery handling for non-PM agent that needs recovery."""
        mock_status = Mock(status="critical")
        monitor_service.health_checker.check_agent_health.return_value = mock_status
        monitor_service.health_checker.should_attempt_recovery.return_value = True

        result = monitor_service.handle_recovery("session1", "2")

        assert result is True
        monitor_service.notification_manager.notify_agent_crash.assert_called_once()
        monitor_service.health_checker.mark_recovery_attempted.assert_called_once_with("session1:2")

    def test_handle_recovery_non_pm_no_recovery_needed(self, monitor_service):
        """Test recovery handling for non-PM agent that doesn't need recovery."""
        mock_status = Mock(status="healthy")
        monitor_service.health_checker.check_agent_health.return_value = mock_status
        monitor_service.health_checker.should_attempt_recovery.return_value = False

        result = monitor_service.handle_recovery("session1", "2")

        assert result is False
        monitor_service.notification_manager.notify_agent_crash.assert_not_called()

    def test_discover_agents(self, monitor_service):
        """Test agent discovery delegation."""
        mock_agents = [Mock(), Mock()]
        monitor_service.agent_monitor.discover_agents.return_value = mock_agents

        result = monitor_service.discover_agents()

        assert result == mock_agents
        monitor_service.agent_monitor.discover_agents.assert_called_once()

    def test_run_monitoring_cycle(self, monitor_service, mock_tmux):
        """Test running a monitoring cycle."""
        monitor_service.is_running = True

        # Mock discovered agents
        agents = [
            AgentInfo(target="session1:1", session="session1", window="1", name="PM", type="pm", status="active"),
            AgentInfo(target="session1:2", session="session1", window="2", name="Dev", type="dev", status="active"),
        ]
        monitor_service.discover_agents = Mock(return_value=agents)

        # Mock health check results
        def mock_health_check(target):
            if target == "session1:2":
                return Mock(status="critical", is_responsive=False)
            return Mock(status="healthy", is_responsive=True)

        monitor_service.health_checker.check_agent_health.side_effect = mock_health_check

        # Run the cycle
        monitor_service.run_monitoring_cycle()

        # Verify agents were discovered and checked
        monitor_service.discover_agents.assert_called_once()
        assert monitor_service.health_checker.check_agent_health.call_count == 2

        # Verify state was updated
        assert monitor_service.state_tracker.update_agent_state.call_count == 2

        # Verify PM recovery was checked for critical agent
        monitor_service.pm_recovery_manager.check_and_recover_if_needed.assert_not_called()

        # Verify notification was sent for critical non-PM agent
        monitor_service.notification_manager.notify_agent_crash.assert_called_once()

        # Verify notifications were sent
        monitor_service.notification_manager.send_queued_notifications.assert_called_once()

        # Verify metrics were updated
        assert monitor_service.cycle_count == 1
        assert monitor_service.errors_detected == 1

    def test_run_monitoring_cycle_not_running(self, monitor_service):
        """Test monitoring cycle when service is not running."""
        monitor_service.is_running = False

        monitor_service.run_monitoring_cycle()

        # Should not do anything
        monitor_service.discover_agents.assert_not_called()

    def test_run_monitoring_cycle_error_handling(self, monitor_service):
        """Test error handling in monitoring cycle."""
        monitor_service.is_running = True
        monitor_service.discover_agents = Mock(side_effect=Exception("Discovery error"))

        # Should not raise
        monitor_service.run_monitoring_cycle()

        assert monitor_service.errors_detected == 1

    @pytest.mark.asyncio
    async def test_run_async(self, monitor_service):
        """Test async run method."""
        monitor_service.start = Mock(return_value=True)
        monitor_service.stop = Mock()
        monitor_service.run_monitoring_cycle = Mock()
        monitor_service.check_interval = 0.01  # Short interval for testing

        # Run for a short time then stop
        async def stop_after_delay():
            await asyncio.sleep(0.03)
            monitor_service.is_running = False

        stop_task = asyncio.create_task(stop_after_delay())

        await monitor_service.run_async()
        await stop_task

        monitor_service.start.assert_called_once()
        monitor_service.stop.assert_called_once()
        assert monitor_service.run_monitoring_cycle.call_count >= 2

    @pytest.mark.asyncio
    async def test_run_async_start_failure(self, monitor_service):
        """Test async run with start failure."""
        monitor_service.start = Mock(return_value=False)

        with pytest.raises(RuntimeError, match="Failed to start MonitorService"):
            await monitor_service.run_async()

    def test_run_sync(self, monitor_service):
        """Test synchronous run method."""
        monitor_service.start = Mock(return_value=True)
        monitor_service.stop = Mock()
        monitor_service.run_monitoring_cycle = Mock()
        monitor_service.check_interval = 0.01

        # Mock keyboard interrupt after a few cycles
        call_count = 0

        def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise KeyboardInterrupt()

        monitor_service.run_monitoring_cycle.side_effect = side_effect

        monitor_service.run()

        monitor_service.start.assert_called_once()
        monitor_service.stop.assert_called_once()
        assert monitor_service.run_monitoring_cycle.call_count == 3
