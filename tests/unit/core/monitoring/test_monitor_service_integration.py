"""
Integration tests for MonitorService facade.

Tests the coordination between all monitoring components through
the unified MonitorService interface.
"""

import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.monitor_service import MonitorService
from tmux_orchestrator.core.monitoring.types import AgentInfo, MonitorStatus
from tmux_orchestrator.utils.tmux import TMUXManager


class TestMonitorServiceInitialization:
    """Test MonitorService initialization and lifecycle."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.config.check_interval = 30
        self.logger = Mock(spec=logging.Logger)

        # Mock the component imports that don't exist yet
        with (
            patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager"),
            patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager"),
        ):
            self.service = MonitorService(self.tmux, self.config, self.logger)

    def test_initialization(self):
        """Test proper initialization of MonitorService."""
        assert self.service.tmux == self.tmux
        assert self.service.config == self.config
        assert self.service.logger == self.logger
        assert not self.service.is_running
        assert self.service.cycle_count == 0
        assert self.service.check_interval == 30

    @patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager")
    @patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager")
    def test_component_initialization(self, mock_pm_recovery, mock_daemon):
        """Test all components are initialized."""
        service = MonitorService(self.tmux, self.config, self.logger)

        # Verify all components exist
        assert hasattr(service, "daemon_manager")
        assert hasattr(service, "health_checker")
        assert hasattr(service, "agent_monitor")
        assert hasattr(service, "notification_manager")
        assert hasattr(service, "state_tracker")
        assert hasattr(service, "pm_recovery_manager")

    def test_set_idle_monitor(self):
        """Test setting idle monitor propagates to components."""
        idle_monitor = Mock()

        with patch.object(self.service.health_checker, "set_idle_monitor") as mock_set:
            self.service.set_idle_monitor(idle_monitor)

            assert self.service.idle_monitor == idle_monitor
            mock_set.assert_called_once_with(idle_monitor)


class TestMonitorServiceLifecycle:
    """Test start/stop lifecycle management."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)

        with (
            patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager"),
            patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager"),
        ):
            self.service = MonitorService(self.tmux, self.config, self.logger)

    def test_initialize_success(self):
        """Test successful initialization of all components."""
        # Mock all component initializations to succeed
        components = [
            self.service.daemon_manager,
            self.service.health_checker,
            self.service.agent_monitor,
            self.service.notification_manager,
            self.service.state_tracker,
            self.service.pm_recovery_manager,
        ]

        for component in components:
            component.initialize = Mock(return_value=True)

        result = self.service.initialize()

        assert result is True
        for component in components:
            component.initialize.assert_called_once()

    def test_initialize_failure(self):
        """Test initialization failure handling."""
        # Make health_checker fail
        self.service.health_checker.initialize = Mock(return_value=False)

        result = self.service.initialize()

        assert result is False
        self.logger.error.assert_called()

    def test_start_success(self):
        """Test successful service start."""
        with (
            patch.object(self.service, "initialize", return_value=True),
            patch.object(self.service.daemon_manager, "is_running", return_value=False),
            patch.object(self.service.daemon_manager, "start", return_value=True),
        ):
            result = self.service.start()

            assert result is True
            assert self.service.is_running
            assert self.service.start_time is not None

    def test_start_already_running(self):
        """Test starting when already running."""
        self.service.is_running = True

        result = self.service.start()

        assert result is True
        self.logger.warning.assert_called_with("MonitorService is already running")

    def test_stop_success(self):
        """Test successful service stop."""
        self.service.is_running = True

        with (
            patch.object(self.service.daemon_manager, "is_running", return_value=True),
            patch.object(self.service.daemon_manager, "stop"),
            patch.object(self.service, "cleanup"),
        ):
            result = self.service.stop()

            assert result is True
            assert not self.service.is_running
            self.service.daemon_manager.stop.assert_called_once()
            self.service.cleanup.assert_called_once()

    def test_cleanup(self):
        """Test cleanup of all components."""
        components = [
            self.service.pm_recovery_manager,
            self.service.state_tracker,
            self.service.notification_manager,
            self.service.agent_monitor,
            self.service.health_checker,
            self.service.daemon_manager,
        ]

        for component in components:
            component.cleanup = Mock()

        self.service.cleanup()

        for component in components:
            component.cleanup.assert_called_once()


class TestMonitoringCycle:
    """Test monitoring cycle execution."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)

        with (
            patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager"),
            patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager"),
        ):
            self.service = MonitorService(self.tmux, self.config, self.logger)
            self.service.is_running = True

    def test_run_monitoring_cycle_success(self):
        """Test successful monitoring cycle."""
        # Mock agents
        agents = [
            AgentInfo("test:1", "test", "1", "PM", "pm", "active"),
            AgentInfo("test:2", "test", "2", "Dev", "developer", "active"),
        ]

        # Mock healthy status
        healthy_status = Mock(status="healthy", is_responsive=True, is_idle=False)

        with (
            patch.object(self.service, "discover_agents", return_value=agents),
            patch.object(self.tmux, "capture_pane", return_value="content"),
            patch.object(self.service.state_tracker, "update_agent_state"),
            patch.object(self.service.health_checker, "check_agent_health", return_value=healthy_status),
            patch.object(self.service.notification_manager, "send_queued_notifications"),
        ):
            self.service.run_monitoring_cycle()

            assert self.service.cycle_count == 1
            assert self.service.last_cycle_time > 0
            assert self.service.errors_detected == 0

    def test_run_monitoring_cycle_with_critical_agent(self):
        """Test monitoring cycle with critical agent."""
        # Mock agents
        agents = [
            AgentInfo("test:1", "test", "1", "PM", "pm", "active"),
            AgentInfo("test:2", "test", "2", "Dev", "developer", "active"),
        ]

        # Mock statuses
        healthy_status = Mock(status="healthy", is_responsive=True)
        critical_status = Mock(status="critical", is_responsive=False)

        def mock_health_check(target):
            return healthy_status if target == "test:1" else critical_status

        with (
            patch.object(self.service, "discover_agents", return_value=agents),
            patch.object(self.tmux, "capture_pane", return_value="content"),
            patch.object(self.service.state_tracker, "update_agent_state"),
            patch.object(self.service.health_checker, "check_agent_health", side_effect=mock_health_check),
            patch.object(self.service.notification_manager, "notify_agent_crash") as mock_notify,
            patch.object(self.service.notification_manager, "send_queued_notifications"),
        ):
            self.service.run_monitoring_cycle()

            assert self.service.errors_detected == 1
            mock_notify.assert_called_once()

    def test_run_monitoring_cycle_pm_recovery(self):
        """Test monitoring cycle triggers PM recovery."""
        # Mock PM agent
        pm_agent = AgentInfo("test:1", "test", "1", "PM", "pm", "active")
        critical_status = Mock(status="critical", is_responsive=False)

        with (
            patch.object(self.service, "discover_agents", return_value=[pm_agent]),
            patch.object(self.tmux, "capture_pane", return_value="content"),
            patch.object(self.service.state_tracker, "update_agent_state"),
            patch.object(self.service.health_checker, "check_agent_health", return_value=critical_status),
            patch.object(self.service.pm_recovery_manager, "check_and_recover_if_needed") as mock_recover,
            patch.object(self.service.notification_manager, "send_queued_notifications"),
        ):
            self.service.run_monitoring_cycle()

            mock_recover.assert_called_once_with("test")

    def test_run_monitoring_cycle_not_running(self):
        """Test monitoring cycle when service not running."""
        self.service.is_running = False

        self.service.run_monitoring_cycle()

        # Should return early without doing anything
        assert self.service.cycle_count == 0


class TestHealthChecking:
    """Test health checking functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)

        with (
            patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager"),
            patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager"),
        ):
            self.service = MonitorService(self.tmux, self.config, self.logger)

    def test_check_health_single_window(self):
        """Test health check for single window."""
        status = Mock(
            status="healthy", is_responsive=True, is_idle=False, consecutive_failures=0, last_response=datetime.now()
        )

        with patch.object(self.service.health_checker, "check_agent_health", return_value=status):
            result = self.service.check_health("test", "1")

            assert result["target"] == "test:1"
            assert result["status"] == "healthy"
            assert result["is_responsive"] is True
            assert result["is_idle"] is False

    def test_check_health_entire_session(self):
        """Test health check for entire session."""
        agents = [
            Mock(target="test:1", session="test", display_name="PM"),
            Mock(target="test:2", session="test", display_name="Dev"),
        ]

        status = Mock(status="healthy", is_responsive=True, is_idle=False)

        with (
            patch.object(self.service.agent_monitor, "discover_agents", return_value=agents),
            patch.object(self.service.health_checker, "check_agent_health", return_value=status),
        ):
            result = self.service.check_health("test")

            assert "test:1" in result
            assert "test:2" in result
            assert result["test:1"]["status"] == "healthy"


class TestRecoveryHandling:
    """Test recovery handling functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)

        with (
            patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager"),
            patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager"),
        ):
            self.service = MonitorService(self.tmux, self.config, self.logger)

    def test_handle_recovery_pm(self):
        """Test recovery handling for PM."""
        with patch.object(self.service.pm_recovery_manager, "handle_recovery", return_value=True):
            result = self.service.handle_recovery("test", "1")

            assert result is True
            self.service.pm_recovery_manager.handle_recovery.assert_called_once_with("test")

    def test_handle_recovery_regular_agent(self):
        """Test recovery handling for regular agent."""
        status = Mock(status="critical", is_responsive=False)

        with (
            patch.object(self.service.health_checker, "check_agent_health", return_value=status),
            patch.object(self.service.health_checker, "should_attempt_recovery", return_value=True),
            patch.object(self.service.notification_manager, "notify_agent_crash"),
            patch.object(self.service.health_checker, "mark_recovery_attempted"),
        ):
            result = self.service.handle_recovery("test", "2")

            assert result is True
            self.service.notification_manager.notify_agent_crash.assert_called_once()
            self.service.health_checker.mark_recovery_attempted.assert_called_once()


class TestStatusReporting:
    """Test status reporting functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)

        with (
            patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager"),
            patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager"),
        ):
            self.service = MonitorService(self.tmux, self.config, self.logger)

    def test_status_when_running(self):
        """Test status reporting when service is running."""
        self.service.is_running = True
        self.service.start_time = datetime.now() - timedelta(minutes=10)
        self.service.cycle_count = 20
        self.service.last_cycle_time = 0.05
        self.service.errors_detected = 2

        # Mock agent statuses
        agent_statuses = {"test:1": Mock(is_idle=False), "test:2": Mock(is_idle=True), "test:3": Mock(is_idle=False)}

        with patch.object(self.service.health_checker, "get_all_agent_statuses", return_value=agent_statuses):
            status = self.service.status()

            assert isinstance(status, MonitorStatus)
            assert status.is_running is True
            assert status.active_agents == 2
            assert status.idle_agents == 1
            assert status.cycle_count == 20
            assert status.last_cycle_time == 0.05
            assert status.errors_detected == 2
            assert status.uptime.total_seconds() >= 600  # At least 10 minutes

    def test_status_when_not_running(self):
        """Test status reporting when service is not running."""
        self.service.is_running = False

        with patch.object(self.service.health_checker, "get_all_agent_statuses", return_value={}):
            status = self.service.status()

            assert status.is_running is False
            assert status.uptime == timedelta(0)


class TestAsyncExecution:
    """Test asynchronous execution."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)

        with (
            patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager"),
            patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager"),
        ):
            self.service = MonitorService(self.tmux, self.config, self.logger)
            self.service.check_interval = 0.1  # Fast for testing

    @pytest.mark.asyncio
    async def test_run_async(self):
        """Test async monitoring execution."""
        cycle_count = 0

        def mock_cycle():
            nonlocal cycle_count
            cycle_count += 1
            if cycle_count >= 3:
                self.service.is_running = False

        with (
            patch.object(self.service, "start", return_value=True),
            patch.object(self.service, "run_monitoring_cycle", side_effect=mock_cycle),
            patch.object(self.service, "stop"),
        ):
            await self.service.run_async()

            assert cycle_count >= 3
            self.service.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_async_start_failure(self):
        """Test async execution with start failure."""
        with patch.object(self.service, "start", return_value=False):
            with pytest.raises(RuntimeError, match="Failed to start MonitorService"):
                await self.service.run_async()


class TestSyncExecution:
    """Test synchronous execution."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)

        with (
            patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager"),
            patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager"),
        ):
            self.service = MonitorService(self.tmux, self.config, self.logger)
            self.service.check_interval = 0.01  # Very fast for testing

    def test_run_sync(self):
        """Test synchronous monitoring execution."""
        cycle_count = 0

        def mock_cycle():
            nonlocal cycle_count
            cycle_count += 1
            if cycle_count >= 3:
                self.service.is_running = False

        with (
            patch.object(self.service, "start", return_value=True),
            patch.object(self.service, "run_monitoring_cycle", side_effect=mock_cycle),
            patch.object(self.service, "stop"),
        ):
            self.service.run()

            assert cycle_count >= 3
            self.service.stop.assert_called_once()

    def test_run_sync_keyboard_interrupt(self):
        """Test handling keyboard interrupt."""

        def mock_cycle():
            raise KeyboardInterrupt()

        with (
            patch.object(self.service, "start", return_value=True),
            patch.object(self.service, "run_monitoring_cycle", side_effect=mock_cycle),
            patch.object(self.service, "stop"),
        ):
            self.service.run()

            self.logger.info.assert_called_with("Monitoring interrupted by user")
            self.service.stop.assert_called_once()


class TestErrorHandling:
    """Test error handling throughout the service."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)

        with (
            patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager"),
            patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager"),
        ):
            self.service = MonitorService(self.tmux, self.config, self.logger)

    def test_initialize_exception_handling(self):
        """Test exception handling during initialization."""
        self.service.health_checker.initialize = Mock(side_effect=Exception("Init error"))

        result = self.service.initialize()

        assert result is False
        self.logger.error.assert_called()

    def test_cleanup_exception_handling(self):
        """Test exception handling during cleanup."""
        self.service.health_checker.cleanup = Mock(side_effect=Exception("Cleanup error"))

        # Should not raise
        self.service.cleanup()

        self.logger.error.assert_called()

    def test_monitoring_cycle_agent_error(self):
        """Test handling errors for individual agents."""
        agents = [
            AgentInfo("test:1", "test", "1", "PM", "pm", "active"),
            AgentInfo("test:2", "test", "2", "Dev", "developer", "active"),
        ]

        # Make capture_pane fail for second agent
        def mock_capture(target):
            if target == "test:2":
                raise Exception("Capture failed")
            return "content"

        self.service.is_running = True

        with (
            patch.object(self.service, "discover_agents", return_value=agents),
            patch.object(self.tmux, "capture_pane", side_effect=mock_capture),
            patch.object(self.service.state_tracker, "update_agent_state"),
            patch.object(self.service.health_checker, "check_agent_health"),
            patch.object(self.service.notification_manager, "send_queued_notifications"),
        ):
            self.service.run_monitoring_cycle()

            # Should continue despite error
            assert self.service.cycle_count == 1
            self.logger.error.assert_called()


class TestIntegrationWithComponents:
    """Test integration between all components."""

    def setup_method(self):
        """Set up test environment with minimal mocking."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.config.idle_threshold_seconds = 30
        self.config.fresh_agent_threshold_seconds = 10
        self.config.submission_threshold_seconds = 60
        self.config.check_interval = 30
        self.logger = Mock(spec=logging.Logger)

    @patch("tmux_orchestrator.core.monitoring.monitor_service.DaemonManager")
    @patch("tmux_orchestrator.core.monitoring.monitor_service.PMRecoveryManager")
    def test_full_monitoring_flow(self, mock_pm_recovery_class, mock_daemon_class):
        """Test complete monitoring flow with real components."""
        # Create service with real components (except mocked daemon/PM recovery)
        service = MonitorService(self.tmux, self.config, self.logger)

        # Mock TMUX responses
        self.tmux.list_sessions.return_value = [{"name": "test-session"}]
        self.tmux.list_windows.return_value = [{"index": "1", "name": "pm"}, {"index": "2", "name": "developer"}]
        self.tmux.capture_pane.return_value = "Human: Status?\nAssistant: Working on task..."

        # Initialize and start
        service.initialize()
        service.is_running = True

        # Run a monitoring cycle
        service.run_monitoring_cycle()

        # Verify the flow
        assert service.cycle_count == 1
        assert service.last_cycle_time > 0

        # Check that components were used
        self.tmux.list_sessions.assert_called()
        self.tmux.list_windows.assert_called()
        self.tmux.capture_pane.assert_called()
