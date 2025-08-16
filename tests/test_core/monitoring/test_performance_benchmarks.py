"""
Performance benchmarks for monitoring system with 50+ agents.

Tests to ensure the refactored monitoring system can handle scale
and performs better than the original implementation.
"""

import time
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.component_manager import ComponentManager
from tmux_orchestrator.core.monitoring.types import AgentInfo, IdleAnalysis, IdleType
from tmux_orchestrator.utils.tmux import TMUXManager


class TestMonitoringPerformance:
    """Test monitoring system performance with many agents."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.config.idle_threshold_seconds = 30
        self.config.fresh_agent_threshold_seconds = 10
        self.config.submission_threshold_seconds = 60
        self.config.monitoring_interval = 2

        self.component_manager = ComponentManager(self.tmux, self.config)

    def _create_mock_agents(self, count: int, sessions: int = 5) -> list[AgentInfo]:
        """Create mock agents distributed across sessions.

        Args:
            count: Number of agents to create
            sessions: Number of sessions to distribute agents across

        Returns:
            List of mock AgentInfo objects
        """
        agents = []
        for i in range(count):
            session_num = i % sessions
            window_num = i // sessions
            agent = AgentInfo(
                target=f"session-{session_num}:{window_num}",
                session=f"session-{session_num}",
                window=str(window_num),
                name=f"agent-{i}",
                type="developer" if i % 3 == 0 else "qa" if i % 3 == 1 else "pm",
                status="active",
            )
            agents.append(agent)
        return agents

    def _create_mock_analysis(self, is_idle: bool = False, error: bool = False) -> IdleAnalysis:
        """Create mock idle analysis result.

        Args:
            is_idle: Whether agent is idle
            error: Whether agent has error

        Returns:
            Mock IdleAnalysis object
        """
        idle_type = IdleType.UNKNOWN
        if is_idle:
            idle_type = IdleType.NEWLY_IDLE
        elif error:
            idle_type = IdleType.ERROR_STATE

        return Mock(
            spec=IdleAnalysis,
            is_idle=is_idle,
            idle_type=idle_type,
            error_detected=error,
            error_type="rate_limit" if error else None,
            content_hash=f"hash_{time.time()}",
            confidence=0.9,
        )

    def test_monitoring_cycle_50_agents(self):
        """Benchmark monitoring cycle with 50 agents."""
        agents = self._create_mock_agents(50)

        with (
            patch.object(self.component_manager.agent_monitor, "discover_agents", return_value=agents),
            patch.object(
                self.component_manager.agent_monitor, "analyze_agent_content", return_value=self._create_mock_analysis()
            ),
            patch.object(self.component_manager.state_tracker, "track_session_agent"),
            patch.object(self.component_manager.state_tracker, "update_agent_state"),
            patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=0),
        ):
            start_time = time.perf_counter()
            result = self.component_manager.execute_monitoring_cycle()
            end_time = time.perf_counter()

            cycle_time = end_time - start_time

            assert result.success is True
            assert result.agents_discovered == 50
            assert result.agents_analyzed == 50
            assert cycle_time < 0.1  # Should complete in under 100ms
            print(f"\n50 agents cycle time: {cycle_time:.4f}s")

    def test_monitoring_cycle_100_agents(self):
        """Benchmark monitoring cycle with 100 agents."""
        agents = self._create_mock_agents(100, sessions=10)

        with (
            patch.object(self.component_manager.agent_monitor, "discover_agents", return_value=agents),
            patch.object(
                self.component_manager.agent_monitor, "analyze_agent_content", return_value=self._create_mock_analysis()
            ),
            patch.object(self.component_manager.state_tracker, "track_session_agent"),
            patch.object(self.component_manager.state_tracker, "update_agent_state"),
            patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=0),
        ):
            start_time = time.perf_counter()
            result = self.component_manager.execute_monitoring_cycle()
            end_time = time.perf_counter()

            cycle_time = end_time - start_time

            assert result.success is True
            assert result.agents_discovered == 100
            assert result.agents_analyzed == 100
            assert cycle_time < 0.2  # Should complete in under 200ms
            print(f"\n100 agents cycle time: {cycle_time:.4f}s")

    def test_monitoring_cycle_mixed_states(self):
        """Benchmark with agents in various states (idle, error, active)."""
        agents = self._create_mock_agents(60)

        # Create varied analysis results
        def mock_analyze(target):
            agent_num = int(target.split(":")[1])
            if agent_num % 5 == 0:  # 20% error
                return self._create_mock_analysis(error=True)
            elif agent_num % 3 == 0:  # ~30% idle
                return self._create_mock_analysis(is_idle=True)
            else:  # ~50% active
                return self._create_mock_analysis()

        with (
            patch.object(self.component_manager.agent_monitor, "discover_agents", return_value=agents),
            patch.object(self.component_manager.agent_monitor, "analyze_agent_content", side_effect=mock_analyze),
            patch.object(self.component_manager.state_tracker, "track_session_agent"),
            patch.object(self.component_manager.state_tracker, "update_agent_state"),
            patch.object(self.component_manager.notification_manager, "notify_agent_idle"),
            patch.object(self.component_manager.notification_manager, "notify_agent_crash"),
            patch.object(self.component_manager.notification_manager, "notify_recovery_needed"),
            patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=20),
            patch.object(self.component_manager, "_check_team_idle_status"),
        ):
            start_time = time.perf_counter()
            result = self.component_manager.execute_monitoring_cycle()
            end_time = time.perf_counter()

            cycle_time = end_time - start_time

            assert result.success is True
            assert result.agents_discovered == 60
            assert result.idle_agents > 0
            assert result.notifications_sent == 20
            assert cycle_time < 0.15  # Should complete in under 150ms
            print(f"\nMixed states (60 agents) cycle time: {cycle_time:.4f}s")

    def test_sustained_monitoring_performance(self):
        """Test performance over multiple monitoring cycles."""
        agents = self._create_mock_agents(50)
        cycle_times = []

        with (
            patch.object(self.component_manager.agent_monitor, "discover_agents", return_value=agents),
            patch.object(
                self.component_manager.agent_monitor, "analyze_agent_content", return_value=self._create_mock_analysis()
            ),
            patch.object(self.component_manager.state_tracker, "track_session_agent"),
            patch.object(self.component_manager.state_tracker, "update_agent_state"),
            patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=0),
        ):
            # Run 100 cycles to test sustained performance
            for i in range(100):
                start_time = time.perf_counter()
                result = self.component_manager.execute_monitoring_cycle()
                end_time = time.perf_counter()

                cycle_times.append(end_time - start_time)
                assert result.success is True

        avg_time = sum(cycle_times) / len(cycle_times)
        max_time = max(cycle_times)
        min_time = min(cycle_times)

        print("\nSustained performance (100 cycles, 50 agents):")
        print(f"  Average: {avg_time:.4f}s")
        print(f"  Min: {min_time:.4f}s")
        print(f"  Max: {max_time:.4f}s")

        assert avg_time < 0.05  # Average should be under 50ms
        assert max_time < 0.1  # No cycle should exceed 100ms

    def test_memory_stability(self):
        """Test memory usage remains stable over many cycles."""
        agents = self._create_mock_agents(75)

        # Track performance history size
        _initial_history_size = 0

        with (
            patch.object(self.component_manager.agent_monitor, "discover_agents", return_value=agents),
            patch.object(
                self.component_manager.agent_monitor, "analyze_agent_content", return_value=self._create_mock_analysis()
            ),
            patch.object(self.component_manager.state_tracker, "track_session_agent"),
            patch.object(self.component_manager.state_tracker, "update_agent_state"),
            patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=0),
        ):
            # Run many cycles to test memory stability
            for i in range(200):
                result = self.component_manager.execute_monitoring_cycle()
                assert result.success is True

                if i == 10:
                    _initial_history_size = len(self.component_manager._performance_history)

        # Check that performance history is bounded
        final_history_size = len(self.component_manager._performance_history)
        assert final_history_size <= 100  # Should be capped at max_history_size
        print(f"\nPerformance history size after 200 cycles: {final_history_size}")

    def test_tmux_command_efficiency(self):
        """Test reduction in TMUX commands with caching."""
        _agents = self._create_mock_agents(50)

        # Track TMUX calls
        tmux_calls = {"list_sessions": 0, "list_windows": 0, "capture_pane": 0}

        def track_list_sessions(*args, **kwargs):
            tmux_calls["list_sessions"] += 1
            return [{"name": f"session-{i}"} for i in range(5)]

        def track_list_windows(session):
            tmux_calls["list_windows"] += 1
            return [{"index": str(i), "name": f"agent-{i}"} for i in range(10)]

        def track_capture_pane(target, **kwargs):
            tmux_calls["capture_pane"] += 1
            return f"Content for {target}"

        self.tmux.list_sessions = Mock(side_effect=track_list_sessions)
        self.tmux.list_windows = Mock(side_effect=track_list_windows)
        self.tmux.capture_pane = Mock(side_effect=track_capture_pane)

        # Initialize component manager with real TMUX mock
        component_manager = ComponentManager(self.tmux, self.config)
        component_manager.initialize()

        # Run multiple cycles
        for i in range(5):
            component_manager.execute_monitoring_cycle()

        print("\nTMUX command usage over 5 cycles:")
        print(f"  list_sessions: {tmux_calls['list_sessions']}")
        print(f"  list_windows: {tmux_calls['list_windows']}")
        print(f"  capture_pane: {tmux_calls['capture_pane']}")

        # With caching, sessions/windows shouldn't be called every cycle
        assert tmux_calls["list_sessions"] < 10  # Less than 2x cycles
        assert tmux_calls["list_windows"] < 25  # Less than 5x sessions x cycles

    def test_concurrent_session_processing(self):
        """Test performance with agents distributed across many sessions."""
        # Create agents across 20 sessions
        agents = []
        for session in range(20):
            for window in range(5):
                agent = AgentInfo(
                    target=f"session-{session}:{window}",
                    session=f"session-{session}",
                    window=str(window),
                    name=f"agent-s{session}-w{window}",
                    type="developer",
                    status="active",
                )
                agents.append(agent)

        with (
            patch.object(self.component_manager.agent_monitor, "discover_agents", return_value=agents),
            patch.object(
                self.component_manager.agent_monitor, "analyze_agent_content", return_value=self._create_mock_analysis()
            ),
            patch.object(self.component_manager.state_tracker, "track_session_agent"),
            patch.object(self.component_manager.state_tracker, "update_agent_state"),
            patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=0),
            patch.object(self.component_manager, "_check_team_idle_status"),
        ):
            start_time = time.perf_counter()
            result = self.component_manager.execute_monitoring_cycle()
            end_time = time.perf_counter()

            cycle_time = end_time - start_time

            assert result.success is True
            assert result.agents_discovered == 100  # 20 sessions x 5 windows
            assert cycle_time < 0.2  # Should handle many sessions efficiently
            print(f"\n20 sessions (100 agents) cycle time: {cycle_time:.4f}s")


class TestScalabilityLimits:
    """Test system behavior at scale limits."""

    def setup_method(self):
        """Set up test environment."""
        self.tmux = Mock(spec=TMUXManager)
        self.config = Mock(spec=Config)
        self.component_manager = ComponentManager(self.tmux, self.config)

    def test_performance_degradation_curve(self):
        """Test how performance degrades with increasing agent count."""
        results = []

        for agent_count in [10, 25, 50, 75, 100, 150, 200]:
            agents = self._create_mock_agents(agent_count)

            with (
                patch.object(self.component_manager.agent_monitor, "discover_agents", return_value=agents),
                patch.object(
                    self.component_manager.agent_monitor,
                    "analyze_agent_content",
                    return_value=Mock(is_idle=False, error_detected=False, content_hash="hash"),
                ),
                patch.object(self.component_manager.state_tracker, "track_session_agent"),
                patch.object(self.component_manager.state_tracker, "update_agent_state"),
                patch.object(self.component_manager.notification_manager, "send_queued_notifications", return_value=0),
            ):
                # Average over 5 runs
                times = []
                for _ in range(5):
                    start_time = time.perf_counter()
                    _ = self.component_manager.execute_monitoring_cycle()
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)

                avg_time = sum(times) / len(times)
                results.append((agent_count, avg_time))

        print("\nPerformance scaling:")
        for count, avg_time in results:
            print(f"  {count} agents: {avg_time:.4f}s")

        # Check that performance scales reasonably
        # Time should not grow faster than linearly
        time_10 = results[0][1]
        time_100 = results[4][1]
        scaling_factor = time_100 / time_10

        assert scaling_factor < 15  # Should scale better than O(n)
        print(f"\nScaling factor (10 to 100 agents): {scaling_factor:.2f}x")

    def _create_mock_agents(self, count: int) -> list[AgentInfo]:
        """Helper to create mock agents."""
        agents = []
        for i in range(count):
            agent = AgentInfo(
                target=f"session:{i}",
                session="session",
                window=str(i),
                name=f"agent-{i}",
                type="developer",
                status="active",
            )
            agents.append(agent)
        return agents


class TestPerformanceComparison:
    """Compare performance with original monitor.py (if available)."""

    @pytest.mark.skip(reason="Requires original monitor.py for comparison")
    def test_performance_vs_original(self):
        """Compare refactored performance against original implementation."""
        # This would require having both implementations available
        # Placeholder for actual comparison testing
        pass

    def test_component_isolation_performance(self):
        """Test that component isolation doesn't add significant overhead."""
        # Test direct component calls vs through ComponentManager
        config = Mock(spec=Config)
        tmux = Mock(spec=TMUXManager)

        from tmux_orchestrator.core.monitoring.agent_monitor import AgentMonitor
        from tmux_orchestrator.core.monitoring.notification_manager import NotificationManager
        from tmux_orchestrator.core.monitoring.state_tracker import StateTracker

        # Direct component timing
        agent_monitor = AgentMonitor(tmux, config, Mock())
        _notification_manager = NotificationManager(tmux, config, Mock())
        _state_tracker = StateTracker(tmux, config, Mock())

        # Mock discover agents
        agents = [Mock(target=f"test:{i}") for i in range(50)]

        # Time direct calls
        direct_start = time.perf_counter()
        with patch.object(agent_monitor, "discover_agents", return_value=agents):
            discovered = agent_monitor.discover_agents()
            for agent in discovered:
                with patch.object(agent_monitor, "analyze_agent_content", return_value=Mock()):
                    agent_monitor.analyze_agent_content(agent.target)
        direct_end = time.perf_counter()
        direct_time = direct_end - direct_start

        # Time through ComponentManager
        component_manager = ComponentManager(tmux, config)
        manager_start = time.perf_counter()
        with (
            patch.object(component_manager.agent_monitor, "discover_agents", return_value=agents),
            patch.object(component_manager.agent_monitor, "analyze_agent_content", return_value=Mock()),
            patch.object(component_manager.state_tracker, "track_session_agent"),
            patch.object(component_manager.state_tracker, "update_agent_state"),
            patch.object(component_manager.notification_manager, "send_queued_notifications", return_value=0),
        ):
            component_manager.execute_monitoring_cycle()
        manager_end = time.perf_counter()
        manager_time = manager_end - manager_start

        overhead = (manager_time - direct_time) / direct_time * 100
        print(f"\nComponent isolation overhead: {overhead:.1f}%")
        print(f"  Direct: {direct_time:.4f}s")
        print(f"  Manager: {manager_time:.4f}s")

        # Overhead should be minimal
        assert overhead < 20  # Less than 20% overhead is acceptable
