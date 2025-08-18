"""
Comprehensive tests for HealthChecker component.

Tests the health monitoring functionality to ensure accurate
health status tracking and recovery decisions.
"""

import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.health_checker import AgentHealthStatus, HealthChecker
from tmux_orchestrator.utils.tmux import TMUXManager


class TestHealthCheckerInitialization:
    """Test HealthChecker initialization and configuration."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.config.max_failures = 3
        self.config.recovery_cooldown = 300
        self.config.response_timeout = 60
        self.logger = Mock(spec=logging.Logger)

        self.health_checker = HealthChecker(self.tmux, self.config, self.logger)

    def test_initialization(self):
        """Test proper initialization of HealthChecker."""
        assert self.health_checker.tmux == self.tmux
        assert self.health_checker.config == self.config
        assert self.health_checker.logger == self.logger
        assert self.health_checker.max_failures == 3
        assert self.health_checker.recovery_cooldown == 300
        assert self.health_checker.response_timeout == 60
        assert isinstance(self.health_checker.agent_status, dict)
        assert isinstance(self.health_checker.recent_recoveries, dict)

    def test_initialize_method(self):
        """Test initialize method."""
        result = self.health_checker.initialize()
        assert result is True
        self.logger.info.assert_called_with("HealthChecker initialized")

    def test_cleanup(self):
        """Test cleanup method."""
        # Add some data
        self.health_checker.agent_status["test:1"] = Mock()
        self.health_checker.recent_recoveries["test:1"] = datetime.now()

        self.health_checker.cleanup()

        assert len(self.health_checker.agent_status) == 0
        assert len(self.health_checker.recent_recoveries) == 0

    def test_set_idle_monitor(self):
        """Test setting idle monitor."""
        idle_monitor = Mock()
        self.health_checker.set_idle_monitor(idle_monitor)
        assert self.health_checker.idle_monitor == idle_monitor


class TestAgentRegistration:
    """Test agent registration and unregistration."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.health_checker = HealthChecker(self.tmux, self.config, self.logger)

    def test_register_agent(self):
        """Test registering a new agent."""
        target = "test:1"
        self.health_checker.register_agent(target)

        assert target in self.health_checker.agent_status
        status = self.health_checker.agent_status[target]
        assert status.target == target
        assert status.consecutive_failures == 0
        assert status.is_responsive is True
        assert status.status == "healthy"
        assert status.is_idle is False
        assert status.activity_changes == 0

    def test_register_agent_duplicate(self):
        """Test registering an already registered agent."""
        target = "test:1"
        self.health_checker.register_agent(target)
        original_status = self.health_checker.agent_status[target]

        # Register again
        self.health_checker.register_agent(target)

        # Should not replace existing status
        assert self.health_checker.agent_status[target] == original_status

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        target = "test:1"
        self.health_checker.register_agent(target)

        self.health_checker.unregister_agent(target)

        assert target not in self.health_checker.agent_status
        self.logger.info.assert_called_with(f"Unregistered agent from health monitoring: {target}")

    def test_unregister_nonexistent_agent(self):
        """Test unregistering a non-existent agent."""
        # Should not raise error
        self.health_checker.unregister_agent("nonexistent:1")


class TestHealthChecking:
    """Test health checking functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.config.max_failures = 3
        self.logger = Mock(spec=logging.Logger)
        self.health_checker = HealthChecker(self.tmux, self.config, self.logger)

    @patch("tmux_orchestrator.core.monitoring.health_checker.is_claude_interface_present")
    def test_check_agent_health_new_agent(self, mock_claude_check):
        """Test health check for new agent."""
        target = "test:1"
        content = "Human: Hello\nAssistant: Hi!"
        self.tmux.capture_pane.return_value = content
        mock_claude_check.return_value = True

        status = self.health_checker.check_agent_health(target)

        assert status.target == target
        assert status.is_responsive is True
        assert status.status == "healthy"
        assert status.consecutive_failures == 0

    @patch("tmux_orchestrator.core.monitoring.health_checker.is_claude_interface_present")
    def test_check_agent_health_with_idle_monitor(self, mock_claude_check):
        """Test health check with idle monitor set."""
        target = "test:1"
        content = "Human: Hello\nAssistant: Hi!"
        self.tmux.capture_pane.return_value = content
        mock_claude_check.return_value = True

        # Set up idle monitor
        idle_monitor = Mock()
        idle_monitor.is_agent_idle.return_value = True
        self.health_checker.set_idle_monitor(idle_monitor)

        status = self.health_checker.check_agent_health(target)

        assert status.is_idle is True
        idle_monitor.is_agent_idle.assert_called_with(target)

    @patch("tmux_orchestrator.core.monitoring.health_checker.is_claude_interface_present")
    def test_check_agent_health_content_change(self, mock_claude_check):
        """Test health check detects content changes."""
        target = "test:1"
        self.health_checker.register_agent(target)
        original_changes = self.health_checker.agent_status[target].activity_changes

        # First check
        self.tmux.capture_pane.return_value = "Content 1"
        mock_claude_check.return_value = True
        self.health_checker.check_agent_health(target)

        # Second check with different content
        self.tmux.capture_pane.return_value = "Content 2"
        status = self.health_checker.check_agent_health(target)

        assert status.activity_changes > original_changes

    @patch("tmux_orchestrator.core.monitoring.health_checker._has_crash_indicators")
    @patch("tmux_orchestrator.core.monitoring.health_checker.is_claude_interface_present")
    def test_check_agent_health_unresponsive(self, mock_claude_check, mock_crash_check):
        """Test health check for unresponsive agent."""
        target = "test:1"
        content = "bash$ "
        self.tmux.capture_pane.return_value = content
        mock_claude_check.return_value = False
        mock_crash_check.return_value = True

        # Set idle monitor to return idle
        idle_monitor = Mock()
        idle_monitor.is_agent_idle.return_value = True
        self.health_checker.set_idle_monitor(idle_monitor)

        status = self.health_checker.check_agent_health(target)

        assert status.is_responsive is False
        assert status.consecutive_failures == 1
        assert status.status == "unresponsive"

    def test_check_agent_health_critical_after_failures(self):
        """Test agent becomes critical after max failures."""
        target = "test:1"
        self.health_checker.register_agent(target)

        # Mock idle monitor
        idle_monitor = Mock()
        idle_monitor.is_agent_idle.return_value = True
        self.health_checker.set_idle_monitor(idle_monitor)

        # Simulate multiple failures
        with patch.object(self.health_checker, "_check_agent_responsiveness", return_value=False):
            for i in range(4):  # More than max_failures
                status = self.health_checker.check_agent_health(target)

        assert status.status == "critical"
        assert status.consecutive_failures >= self.config.max_failures

    def test_check_agent_health_exception_handling(self):
        """Test health check handles exceptions gracefully."""
        target = "test:1"
        self.tmux.capture_pane.side_effect = Exception("TMUX error")

        status = self.health_checker.check_agent_health(target)

        assert status.is_responsive is False
        assert status.status == "critical"
        assert status.consecutive_failures == 1
        self.logger.error.assert_called()


class TestResponsivenessChecking:
    """Test agent responsiveness checking."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.health_checker = HealthChecker(self.tmux, self.config, self.logger)

    @patch("tmux_orchestrator.core.monitoring.health_checker.is_claude_interface_present")
    def test_responsive_when_not_idle(self, mock_claude_check):
        """Test agent is responsive when not idle."""
        result = self.health_checker._check_agent_responsiveness("test:1", "content", is_idle=False)
        assert result is True
        # Should not even check Claude interface when not idle
        mock_claude_check.assert_not_called()

    @patch("tmux_orchestrator.core.monitoring.health_checker.is_claude_interface_present")
    def test_responsive_with_claude_interface(self, mock_claude_check):
        """Test agent is responsive with Claude interface present."""
        mock_claude_check.return_value = True

        result = self.health_checker._check_agent_responsiveness(
            "test:1", "Human: test\nAssistant: response", is_idle=True
        )
        assert result is True

    @patch("tmux_orchestrator.core.monitoring.health_checker._has_crash_indicators")
    @patch("tmux_orchestrator.core.monitoring.health_checker._has_error_indicators")
    @patch("tmux_orchestrator.core.monitoring.health_checker.is_claude_interface_present")
    def test_unresponsive_with_errors(self, mock_claude_check, mock_error_check, mock_crash_check):
        """Test agent is unresponsive with critical errors."""
        mock_claude_check.return_value = False
        mock_error_check.return_value = True
        mock_crash_check.return_value = True

        result = self.health_checker._check_agent_responsiveness("test:1", "Error: crashed", is_idle=True)
        assert result is False


class TestRecoveryDecisions:
    """Test recovery decision logic."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.config.max_failures = 3
        self.config.recovery_cooldown = 300
        self.config.response_timeout = 60
        self.logger = Mock(spec=logging.Logger)
        self.health_checker = HealthChecker(self.tmux, self.config, self.logger)

    def test_should_not_recover_healthy_agent(self):
        """Test no recovery for healthy agent."""
        target = "test:1"
        self.health_checker.register_agent(target)

        result = self.health_checker.should_attempt_recovery(target)
        assert result is False

    def test_should_recover_critical_agent(self):
        """Test recovery for critical agent."""
        target = "test:1"
        status = AgentHealthStatus(
            target=target,
            last_heartbeat=datetime.now(),
            last_response=datetime.now(),
            consecutive_failures=5,
            is_responsive=False,
            last_content_hash="",
            status="critical",
            is_idle=True,
            activity_changes=0,
        )
        self.health_checker.agent_status[target] = status

        result = self.health_checker.should_attempt_recovery(target)
        assert result is True

    def test_should_not_recover_recently_recovered(self):
        """Test no recovery for recently recovered agent."""
        target = "test:1"
        # Mark as recently recovered
        self.health_checker.recent_recoveries[target] = datetime.now()

        # Create critical status
        status = AgentHealthStatus(
            target=target,
            last_heartbeat=datetime.now(),
            last_response=datetime.now(),
            consecutive_failures=5,
            is_responsive=False,
            last_content_hash="",
            status="critical",
            is_idle=True,
            activity_changes=0,
        )
        self.health_checker.agent_status[target] = status

        result = self.health_checker.should_attempt_recovery(target)
        assert result is False

    def test_should_recover_long_unresponsive(self):
        """Test recovery for long unresponsive agent."""
        target = "test:1"
        old_time = datetime.now() - timedelta(seconds=200)  # Much longer than response_timeout

        status = AgentHealthStatus(
            target=target,
            last_heartbeat=datetime.now(),
            last_response=old_time,
            consecutive_failures=1,
            is_responsive=False,
            last_content_hash="",
            status="warning",
            is_idle=True,
            activity_changes=0,
        )
        self.health_checker.agent_status[target] = status

        result = self.health_checker.should_attempt_recovery(target)
        assert result is True

    def test_mark_recovery_attempted(self):
        """Test marking recovery attempt."""
        target = "test:1"
        before_time = datetime.now()

        self.health_checker.mark_recovery_attempted(target)

        assert target in self.health_checker.recent_recoveries
        assert self.health_checker.recent_recoveries[target] >= before_time
        self.logger.info.assert_called_with(f"Marked recovery attempt for {target}")


class TestUtilityMethods:
    """Test utility methods."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.health_checker = HealthChecker(self.tmux, self.config, self.logger)

    def test_get_all_agent_statuses(self):
        """Test getting all agent statuses."""
        # Register some agents
        self.health_checker.register_agent("test:1")
        self.health_checker.register_agent("test:2")

        statuses = self.health_checker.get_all_agent_statuses()

        assert len(statuses) == 2
        assert "test:1" in statuses
        assert "test:2" in statuses
        # Should be a copy, not the original
        assert statuses is not self.health_checker.agent_status

    def test_is_agent_healthy_true(self):
        """Test checking if agent is healthy."""
        target = "test:1"
        self.health_checker.register_agent(target)

        result = self.health_checker.is_agent_healthy(target)
        assert result is True

    def test_is_agent_healthy_false(self):
        """Test checking if unhealthy agent is healthy."""
        target = "test:1"
        status = AgentHealthStatus(
            target=target,
            last_heartbeat=datetime.now(),
            last_response=datetime.now(),
            consecutive_failures=3,
            is_responsive=False,
            last_content_hash="",
            status="critical",
            is_idle=True,
            activity_changes=0,
        )
        self.health_checker.agent_status[target] = status

        result = self.health_checker.is_agent_healthy(target)
        assert result is False

    def test_is_agent_healthy_nonexistent(self):
        """Test checking health of non-existent agent."""
        result = self.health_checker.is_agent_healthy("nonexistent:1")
        assert result is False


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        # Test missing config attributes
        self.logger = Mock(spec=logging.Logger)
        self.health_checker = HealthChecker(self.tmux, self.config, self.logger)

    def test_default_config_values(self):
        """Test default values when config attributes missing."""
        # Should use defaults when config doesn't have attributes
        assert self.health_checker.max_failures == 3
        assert self.health_checker.recovery_cooldown == 300
        assert self.health_checker.response_timeout == 60

    def test_concurrent_health_checks(self):
        """Test handling multiple agents concurrently."""
        targets = [f"test:{i}" for i in range(10)]

        for target in targets:
            self.health_checker.register_agent(target)

        # Check all agents
        statuses = []
        for target in targets:
            with patch.object(self.health_checker, "_check_agent_responsiveness", return_value=True):
                status = self.health_checker.check_agent_health(target)
                statuses.append(status)

        assert len(statuses) == 10
        assert all(s.status == "healthy" for s in statuses)
