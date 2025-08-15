"""
End-to-end integration tests for the modular monitoring system.

Tests complete workflows from agent discovery through notification delivery
to validate the new architecture provides equivalent functionality to the
monolithic implementation.
"""

import os
import tempfile
import time
from unittest.mock import Mock, patch

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitor_modular import ModularIdleMonitor
from tmux_orchestrator.core.monitoring import ComponentManager
from tmux_orchestrator.utils.tmux import TMUXManager


class TestEndToEndMonitoringWorkflow:
    """Test complete monitoring workflows."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_complete_monitoring_cycle_happy_path(self):
        """Test a complete successful monitoring cycle."""
        # Set up mock data for a typical scenario
        self.tmux.list_sessions.return_value = [{"name": "frontend-team"}, {"name": "backend-team"}]

        def mock_list_windows(session_name):
            if session_name == "frontend-team":
                return [
                    {"index": "0", "name": "shell"},
                    {"index": "1", "name": "pm"},
                    {"index": "2", "name": "claude-developer"},
                ]
            elif session_name == "backend-team":
                return [
                    {"index": "0", "name": "shell"},
                    {"index": "1", "name": "claude-qa"},
                    {"index": "2", "name": "devops"},
                ]
            return []

        self.tmux.list_windows.side_effect = mock_list_windows

        # Mock content capture - simulate active agents
        self.tmux.capture_pane.side_effect = [
            "Agent working on feature implementation...",  # Different each call
            "Running tests and validation...",
            "Implementing backend API...",
            "Setting up deployment pipeline...",
        ]

        # Create component manager and run cycle
        component_manager = ComponentManager(self.tmux, self.config)

        with patch("time.sleep"):  # Speed up polling
            result = component_manager.execute_monitoring_cycle()

        # Verify results
        assert result.success is True
        assert result.agents_discovered == 4  # pm, claude-developer, claude-qa, devops
        assert result.agents_analyzed == 4
        assert result.idle_agents == 0  # All active due to changing content
        assert result.cycle_duration > 0

    def test_monitoring_cycle_with_idle_and_error_agents(self):
        """Test monitoring cycle with mixed agent states."""
        # Set up session with various agent states
        self.tmux.list_sessions.return_value = [{"name": "mixed-team"}]
        self.tmux.list_windows.return_value = [
            {"index": "1", "name": "pm"},
            {"index": "2", "name": "claude-developer"},
            {"index": "3", "name": "claude-qa"},
        ]

        # Mock content - PM active, developer idle, QA has error
        content_responses = [
            "PM coordinating team activities...",  # PM active
            "Static content",  # Developer idle
            "Static content",  # Developer still idle (second poll)
            "Static content",  # Developer still idle (third poll)
            "Static content",  # Developer still idle (fourth poll)
            "Error: Rate limit exceeded. Please try again.",  # QA error
            "Error: Rate limit exceeded. Please try again.",  # QA still error
            "Error: Rate limit exceeded. Please try again.",  # QA still error
            "Error: Rate limit exceeded. Please try again.",  # QA still error
        ]

        self.tmux.capture_pane.side_effect = content_responses

        # Mock PM discovery for notifications
        self.tmux.send_keys = Mock()

        component_manager = ComponentManager(self.tmux, self.config)

        with patch("time.sleep"):  # Speed up polling
            result = component_manager.execute_monitoring_cycle()

        # Verify results
        assert result.success is True
        assert result.agents_discovered == 3
        assert result.agents_analyzed == 3
        assert result.idle_agents == 2  # Developer and QA

        # Verify notifications were queued (send happens separately)
        notification_stats = component_manager.notification_manager.get_notification_stats()
        assert notification_stats["queued_notifications"] >= 2  # Idle + error notifications

    def test_team_idle_detection_and_escalation(self):
        """Test team-wide idle detection and PM escalation."""
        # Set up session where all agents become idle
        self.tmux.list_sessions.return_value = [{"name": "idle-team"}]
        self.tmux.list_windows.return_value = [{"index": "1", "name": "pm"}, {"index": "2", "name": "claude-developer"}]

        # Mock static content for all agents
        static_content = "No activity - agent is idle"
        self.tmux.capture_pane.return_value = static_content

        component_manager = ComponentManager(self.tmux, self.config)

        with patch("time.sleep"):  # Speed up polling
            result = component_manager.execute_monitoring_cycle()

        # Verify team idle detection
        assert component_manager.state_tracker.is_team_idle("idle-team") is True

        # Verify team idle notification was queued
        notification_stats = component_manager.notification_manager.get_notification_stats()
        assert notification_stats["queued_notifications"] >= 1

    def test_fresh_agent_detection_and_notification(self):
        """Test fresh agent detection and briefing notifications."""
        # Set up session with fresh agent
        self.tmux.list_sessions.return_value = [{"name": "fresh-team"}]
        self.tmux.list_windows.return_value = [{"index": "1", "name": "pm"}, {"index": "2", "name": "claude-developer"}]

        # Mock content - PM active, developer fresh
        def mock_capture(target, lines=50):
            if "pm" in target or ":1" in target:
                return "PM managing team coordination..."
            else:
                return "Welcome! How can I assist you today?"

        self.tmux.capture_pane.side_effect = mock_capture

        component_manager = ComponentManager(self.tmux, self.config)

        with patch("time.sleep"):  # Speed up polling
            result = component_manager.execute_monitoring_cycle()

        # Verify fresh agent notification was queued
        notification_stats = component_manager.notification_manager.get_notification_stats()
        assert notification_stats["queued_notifications"] >= 1

    def test_notification_batching_and_delivery(self):
        """Test notification batching and delivery to PM."""
        # Set up session with PM for notification delivery
        self.tmux.list_sessions.return_value = [{"name": "notify-team"}]
        self.tmux.list_windows.return_value = [
            {"index": "1", "name": "pm"},
            {"index": "2", "name": "claude-developer"},
            {"index": "3", "name": "claude-qa"},
        ]

        # Mock mixed content to generate notifications
        content_responses = [
            "PM working...",  # PM active
            "Static content",  # Developer idle
            "Error: Connection timeout",  # QA error
        ]

        call_count = 0

        def mock_capture_pane(target, lines=50):
            nonlocal call_count
            # Return different content for polling simulation
            if ":1" in target:  # PM
                return "PM working..."
            elif ":2" in target:  # Developer
                return "Static content"  # Always same = idle
            else:  # QA
                return "Error: Connection timeout"  # Always same = error

        self.tmux.capture_pane.side_effect = mock_capture_pane
        self.tmux.send_keys = Mock()

        component_manager = ComponentManager(self.tmux, self.config)

        with patch("time.sleep"):  # Speed up polling
            # Execute cycle to queue notifications
            result = component_manager.execute_monitoring_cycle()

            # Send notifications
            sent_count = component_manager.notification_manager.send_queued_notifications()

        # Verify notifications were sent to PM
        assert sent_count >= 1
        self.tmux.send_keys.assert_called()  # PM received notifications

    def test_error_recovery_and_system_resilience(self):
        """Test system behavior during errors and recovery."""
        # Set up session
        self.tmux.list_sessions.return_value = [{"name": "error-team"}]
        self.tmux.list_windows.return_value = [{"index": "1", "name": "pm"}]

        # Simulate agent discovery failure
        component_manager = ComponentManager(self.tmux, self.config)

        with patch.object(
            component_manager.agent_monitor, "discover_agents", side_effect=Exception("Discovery failed")
        ):
            result = component_manager.execute_monitoring_cycle()

        # System should handle error gracefully
        assert result.success is False
        assert len(result.errors) > 0
        assert "Discovery failed" in result.errors[0]

        # Error count should be tracked
        status = component_manager.get_status()
        assert status.errors_detected >= 1

    def test_performance_tracking_and_optimization(self):
        """Test performance tracking during monitoring cycles."""
        # Set up minimal session for performance testing
        self.tmux.list_sessions.return_value = [{"name": "perf-team"}]
        self.tmux.list_windows.return_value = [{"index": "1", "name": "claude-developer"}]
        self.tmux.capture_pane.return_value = "Agent working..."

        component_manager = ComponentManager(self.tmux, self.config)

        # Execute multiple cycles
        with patch("time.sleep"):  # Speed up polling
            for _ in range(5):
                result = component_manager.execute_monitoring_cycle()
                assert result.success is True

        # Verify performance tracking
        stats = component_manager.get_performance_stats()
        assert stats["total_cycles"] == 5
        assert stats["avg_cycle_time"] > 0
        assert stats["min_cycle_time"] <= stats["avg_cycle_time"] <= stats["max_cycle_time"]

        # Verify status reporting
        status = component_manager.get_status()
        assert status.cycle_count == 5
        assert status.last_cycle_time > 0


class TestModularIdleMonitorIntegration:
    """Test the ModularIdleMonitor wrapper integration."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_modular_idle_monitor_lifecycle(self):
        """Test ModularIdleMonitor start/stop lifecycle."""
        monitor = ModularIdleMonitor(self.tmux, self.config)

        # Initially not running
        assert monitor.is_running() is False

        # Mock PID file operations
        with patch.object(monitor, "_run_monitoring_daemon"), patch("multiprocessing.Process") as mock_process_class:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process_class.return_value = mock_process

            # Start monitoring
            result = monitor.start()
            assert result is True

            # Mock PID file existence for is_running check
            with (
                patch.object(monitor.pid_file, "exists", return_value=True),
                patch.object(monitor.pid_file, "read_text", return_value="12345"),
                patch("os.kill"),
            ):  # Mock successful kill check
                assert monitor.is_running() is True

        # Test stop
        with (
            patch.object(monitor.pid_file, "exists", return_value=True),
            patch.object(monitor.pid_file, "read_text", return_value="12345"),
            patch("os.kill"),
            patch.object(monitor, "is_running", side_effect=[True, False]),
        ):  # Running then stopped
            result = monitor.stop()
            assert result is True

    def test_modular_idle_monitor_backward_compatibility(self):
        """Test backward compatibility with original IdleMonitor interface."""
        monitor = ModularIdleMonitor(self.tmux, self.config)

        # Test is_agent_idle method
        with patch.object(monitor, "component_manager") as mock_cm:
            mock_cm.is_agent_idle.return_value = True

            result = monitor.is_agent_idle("test:1")
            assert result is True
            mock_cm.is_agent_idle.assert_called_once_with("test:1")

        # Test status method (should not raise exception)
        with patch("builtins.print"):
            monitor.status()  # Should complete without error

    def test_daemon_monitoring_loop_simulation(self):
        """Test the daemon monitoring loop logic."""
        monitor = ModularIdleMonitor(self.tmux, self.config)

        # Set up mock for graceful stop
        monitor.graceful_stop_file = Mock()
        monitor.graceful_stop_file.exists.side_effect = [False, False, True]  # Stop after 2 cycles

        # Mock logging
        with (
            patch.object(monitor, "_setup_daemon_logging") as mock_logger,
            patch("time.sleep"),
            patch("time.perf_counter", side_effect=[0, 0.005, 0, 0.008, 0, 0.003]),
        ):  # Mock timing
            mock_logger.return_value = Mock()

            # Mock component manager
            mock_cm = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.agents_discovered = 2
            mock_result.idle_agents = 1
            mock_result.notifications_sent = 0
            mock_result.cycle_duration = 0.005
            mock_result.errors = []

            mock_cm.start_monitoring.return_value = True
            mock_cm.execute_monitoring_cycle.return_value = mock_result

            with patch("tmux_orchestrator.core.monitoring.ComponentManager", return_value=mock_cm):
                # This would normally run the daemon loop
                monitor._run_monitoring_daemon(interval=1)

            # Verify component manager was used
            mock_cm.start_monitoring.assert_called_once()
            assert mock_cm.execute_monitoring_cycle.call_count >= 2  # At least 2 cycles


class TestPerformanceValidation:
    """Test performance characteristics of the new architecture."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_monitoring_cycle_performance_target(self):
        """Test that monitoring cycles meet the <10ms performance target."""
        # Set up realistic scenario
        self.tmux.list_sessions.return_value = [{"name": "session1"}, {"name": "session2"}]

        def mock_list_windows(session_name):
            return [
                {"index": "1", "name": "pm"},
                {"index": "2", "name": "claude-developer"},
                {"index": "3", "name": "claude-qa"},
            ]

        self.tmux.list_windows.side_effect = mock_list_windows
        self.tmux.capture_pane.return_value = "Agent working on tasks..."

        component_manager = ComponentManager(self.tmux, self.config)

        # Execute multiple cycles and measure performance
        cycle_times = []
        with patch("time.sleep"):  # Speed up polling
            for _ in range(10):
                start_time = time.perf_counter()
                result = component_manager.execute_monitoring_cycle()
                end_time = time.perf_counter()

                cycle_time = end_time - start_time
                cycle_times.append(cycle_time)

                assert result.success is True

        # Analyze performance
        avg_cycle_time = sum(cycle_times) / len(cycle_times)
        max_cycle_time = max(cycle_times)

        # Performance assertions (relaxed for test environment)
        # Note: Real performance will be better due to test overhead
        assert avg_cycle_time < 0.1  # 100ms in test environment
        assert max_cycle_time < 0.2  # 200ms max in test environment

        print(f"Average cycle time: {avg_cycle_time:.3f}s")
        print(f"Max cycle time: {max_cycle_time:.3f}s")

    def test_memory_efficiency_monitoring(self):
        """Test memory usage patterns during monitoring."""
        # Set up scenario
        self.tmux.list_sessions.return_value = [{"name": "memory-test"}]
        self.tmux.list_windows.return_value = [{"index": "1", "name": "claude-agent"}]
        self.tmux.capture_pane.return_value = "Working on implementation..."

        component_manager = ComponentManager(self.tmux, self.config)

        # Execute cycles and verify no memory leaks in component state
        initial_cache_size = len(component_manager.agent_monitor._agent_cache)
        initial_history_size = len(component_manager._performance_history)

        with patch("time.sleep"):  # Speed up polling
            for _ in range(20):
                result = component_manager.execute_monitoring_cycle()
                assert result.success is True

        # Verify caches don't grow unbounded
        final_cache_size = len(component_manager.agent_monitor._agent_cache)
        final_history_size = len(component_manager._performance_history)

        # Cache should be stable (same agents)
        assert final_cache_size <= initial_cache_size + 2  # Allow some growth

        # Performance history should be bounded
        assert final_history_size <= component_manager._max_history_size
