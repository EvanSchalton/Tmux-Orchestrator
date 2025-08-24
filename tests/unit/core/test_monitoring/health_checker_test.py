"""Tests for the HealthChecker component."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.health_checker import HealthChecker
from tmux_orchestrator.utils.tmux import TMUXManager


class TestHealthChecker:
    """Test suite for HealthChecker component."""

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
        config.max_failures = 3
        config.recovery_cooldown = 300
        config.response_timeout = 60
        return config

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()

    @pytest.fixture
    def health_checker(self, mock_tmux, mock_config, mock_logger):
        """Create a HealthChecker instance with mocks."""
        return HealthChecker(mock_tmux, mock_config, mock_logger)

    def test_initialization(self, health_checker):
        """Test HealthChecker initialization."""
        assert health_checker.initialize() is True
        assert health_checker.agent_status == {}
        assert health_checker.recent_recoveries == {}
        assert health_checker.max_failures == 3
        assert health_checker.recovery_cooldown == 300
        assert health_checker.response_timeout == 60

    def test_cleanup(self, health_checker):
        """Test cleanup clears all state."""
        # Add some state
        health_checker.agent_status["test:1"] = Mock()
        health_checker.recent_recoveries["test:1"] = datetime.now()

        # Clean up
        health_checker.cleanup()

        # Verify state is cleared
        assert health_checker.agent_status == {}
        assert health_checker.recent_recoveries == {}

    def test_register_agent(self, health_checker):
        """Test agent registration."""
        target = "session:1"
        health_checker.register_agent(target)

        assert target in health_checker.agent_status
        status = health_checker.agent_status[target]
        assert status.target == target
        assert status.is_responsive is True
        assert status.status == "healthy"
        assert status.consecutive_failures == 0

    def test_unregister_agent(self, health_checker):
        """Test agent unregistration."""
        target = "session:1"
        health_checker.register_agent(target)
        assert target in health_checker.agent_status

        health_checker.unregister_agent(target)
        assert target not in health_checker.agent_status

    def test_check_agent_health_new_agent(self, health_checker, mock_tmux):
        """Test health check for new agent."""
        target = "session:1"
        mock_tmux.capture_pane.return_value = "Agent content"

        status = health_checker.check_agent_health(target)

        assert status.target == target
        assert status.is_responsive is True
        assert status.status == "healthy"
        assert status.consecutive_failures == 0
        mock_tmux.capture_pane.assert_called_once_with(target, lines=50)

    def test_check_agent_health_with_idle_monitor(self, health_checker, mock_tmux):
        """Test health check with idle monitor set."""
        target = "session:1"
        mock_idle_monitor = Mock()
        mock_idle_monitor.is_agent_idle.return_value = True
        health_checker.set_idle_monitor(mock_idle_monitor)

        status = health_checker.check_agent_health(target)

        assert status.is_idle is True
        mock_idle_monitor.is_agent_idle.assert_called_once_with(target)

    def test_check_agent_health_activity_tracking(self, health_checker, mock_tmux):
        """Test activity tracking through content hash changes."""
        target = "session:1"

        # First check
        mock_tmux.capture_pane.return_value = "Content 1"
        status1 = health_checker.check_agent_health(target)
        assert status1.activity_changes == 0

        # Second check with same content
        status2 = health_checker.check_agent_health(target)
        assert status2.activity_changes == 0

        # Third check with different content
        mock_tmux.capture_pane.return_value = "Content 2"
        status3 = health_checker.check_agent_health(target)
        assert status3.activity_changes == 1

    @patch("tmux_orchestrator.core.monitoring.health_checker.is_claude_interface_present")
    def test_check_agent_responsiveness_active(self, mock_interface_check, health_checker):
        """Test responsiveness check for active agent."""
        # Active agent (not idle) should be responsive
        assert health_checker._check_agent_responsiveness("session:1", "content", False) is True
        mock_interface_check.assert_not_called()

    @patch("tmux_orchestrator.core.monitoring.health_checker.is_claude_interface_present")
    def test_check_agent_responsiveness_idle_with_interface(self, mock_interface_check, health_checker):
        """Test responsiveness check for idle agent with Claude interface."""
        mock_interface_check.return_value = True
        assert health_checker._check_agent_responsiveness("session:1", "content", True) is True
        mock_interface_check.assert_called_once_with("content")

    @patch("tmux_orchestrator.core.monitoring.health_checker._has_crash_indicators")
    @patch("tmux_orchestrator.core.monitoring.health_checker._has_error_indicators")
    @patch("tmux_orchestrator.core.monitoring.health_checker.is_claude_interface_present")
    def test_check_agent_responsiveness_with_errors(self, mock_interface, mock_error, mock_crash, health_checker):
        """Test responsiveness check with error indicators."""
        mock_interface.return_value = False
        mock_crash.return_value = True
        mock_error.return_value = False

        assert health_checker._check_agent_responsiveness("session:1", "content", True) is False

    def test_consecutive_failures_tracking(self, health_checker, mock_tmux):
        """Test tracking of consecutive failures."""
        target = "session:1"
        health_checker.register_agent(target)

        # Mock idle monitor to make agent unresponsive
        mock_idle_monitor = Mock()
        mock_idle_monitor.is_agent_idle.return_value = True
        health_checker.set_idle_monitor(mock_idle_monitor)

        # Mock interface check to return False (unresponsive)
        with patch("tmux_orchestrator.core.monitoring.health_checker.is_claude_interface_present", return_value=False):
            with patch("tmux_orchestrator.core.monitoring.health_checker._has_crash_indicators", return_value=True):
                # First failure
                status1 = health_checker.check_agent_health(target)
                assert status1.consecutive_failures == 1
                assert status1.status == "unresponsive"

                # Second failure
                status2 = health_checker.check_agent_health(target)
                assert status2.consecutive_failures == 2
                assert status2.status == "warning"

                # Third failure
                status3 = health_checker.check_agent_health(target)
                assert status3.consecutive_failures == 3
                assert status3.status == "critical"

    def test_should_attempt_recovery_no_agent(self, health_checker):
        """Test recovery check for non-existent agent."""
        assert health_checker.should_attempt_recovery("unknown:1") is False

    def test_should_attempt_recovery_recent_recovery(self, health_checker):
        """Test recovery check with recent recovery."""
        target = "session:1"
        health_checker.register_agent(target)
        health_checker.recent_recoveries[target] = datetime.now()

        status = health_checker.agent_status[target]
        status.status = "critical"
        status.consecutive_failures = 5

        assert health_checker.should_attempt_recovery(target) is False

    def test_should_attempt_recovery_critical_status(self, health_checker):
        """Test recovery check for critical status."""
        target = "session:1"
        health_checker.register_agent(target)

        status = health_checker.agent_status[target]
        status.status = "critical"
        status.consecutive_failures = 3

        assert health_checker.should_attempt_recovery(target) is True

    def test_should_attempt_recovery_long_unresponsive(self, health_checker):
        """Test recovery check for long unresponsive agent."""
        target = "session:1"
        health_checker.register_agent(target)

        status = health_checker.agent_status[target]
        status.last_response = datetime.now() - timedelta(seconds=200)  # Over 3x timeout

        assert health_checker.should_attempt_recovery(target) is True

    def test_mark_recovery_attempted(self, health_checker):
        """Test marking recovery attempt."""
        target = "session:1"
        assert target not in health_checker.recent_recoveries

        health_checker.mark_recovery_attempted(target)

        assert target in health_checker.recent_recoveries
        assert isinstance(health_checker.recent_recoveries[target], datetime)

    def test_get_all_agent_statuses(self, health_checker):
        """Test getting all agent statuses."""
        # Register multiple agents
        health_checker.register_agent("session1:1")
        health_checker.register_agent("session2:1")

        statuses = health_checker.get_all_agent_statuses()

        assert len(statuses) == 2
        assert "session1:1" in statuses
        assert "session2:1" in statuses
        # Verify it's a copy
        statuses["new:1"] = Mock()
        assert "new:1" not in health_checker.agent_status

    def test_is_agent_healthy(self, health_checker):
        """Test quick health check."""
        target = "session:1"

        # Non-existent agent
        assert health_checker.is_agent_healthy(target) is False

        # Healthy agent
        health_checker.register_agent(target)
        assert health_checker.is_agent_healthy(target) is True

        # Unhealthy agent
        health_checker.agent_status[target].status = "critical"
        assert health_checker.is_agent_healthy(target) is False

    def test_error_handling_in_health_check(self, health_checker, mock_tmux):
        """Test error handling during health check."""
        target = "session:1"
        health_checker.register_agent(target)

        # Mock tmux to raise exception
        mock_tmux.capture_pane.side_effect = Exception("TMUX error")

        status = health_checker.check_agent_health(target)

        assert status.consecutive_failures == 1
        assert status.is_responsive is False
        assert status.status == "critical"
