"""Unit tests for core/monitoring module.

This module tests all monitoring interfaces, types, and components.
Focused on validating business logic with comprehensive mock testing for fast execution.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.interfaces import (
    CrashDetectorInterface,
    DaemonManagerInterface,
    HealthCheckerInterface,
    MonitoringStrategyInterface,
    MonitorServiceInterface,
    PMRecoveryManagerInterface,
    ServiceContainerInterface,
)
from tmux_orchestrator.core.monitoring.types import (
    AgentInfo,
    AgentState,
    IdleAnalysis,
    IdleType,
    MonitorComponent,
    MonitorStatus,
    NotificationEvent,
    NotificationType,
    PluginInfo,
    PluginStatus,
)
from tmux_orchestrator.utils.tmux import TMUXManager

# TMUXManager import removed - using comprehensive_mock_tmux fixture


class TestMonitoringTypes:
    """Test monitoring data types and enums."""

    def test_idle_type_enum_values(self, test_uuid: str) -> None:
        """Test IdleType enum has all expected values."""
        expected_values = {
            "unknown",
            "newly_idle",
            "continuously_idle",
            "fresh_agent",
            "compaction_state",
            "error_state",
        }
        actual_values = {idle_type.value for idle_type in IdleType}
        assert actual_values == expected_values, f"IdleType enum mismatch - Test ID: {test_uuid}"

    def test_notification_type_enum_values(self, test_uuid: str) -> None:
        """Test NotificationType enum has all expected values."""
        expected_values = {"agent_crash", "agent_idle", "agent_fresh", "team_idle", "recovery_needed", "pm_escalation"}
        actual_values = {notif_type.value for notif_type in NotificationType}
        assert actual_values == expected_values, f"NotificationType enum mismatch - Test ID: {test_uuid}"

    def test_plugin_status_enum_values(self, test_uuid: str) -> None:
        """Test PluginStatus enum has all expected values."""
        expected_values = {"discovered", "loaded", "failed", "disabled"}
        actual_values = {status.value for status in PluginStatus}
        assert actual_values == expected_values, f"PluginStatus enum mismatch - Test ID: {test_uuid}"

    def test_agent_info_dataclass(self, test_uuid: str) -> None:
        """Test AgentInfo dataclass creation and properties."""
        # Arrange
        agent = AgentInfo(
            target="session:1",
            session="session",
            window="1",
            name="developer",
            type="developer",
            status="active",
            last_seen=datetime.now(),
        )

        # Act & Assert
        assert agent.target == "session:1"
        assert agent.session == "session"
        assert agent.window == "1"
        assert agent.name == "developer"
        assert agent.type == "developer"
        assert agent.status == "active"
        assert agent.last_seen is not None
        assert agent.display_name == "developer (developer)"

    def test_idle_analysis_dataclass(self, test_uuid: str) -> None:
        """Test IdleAnalysis dataclass creation."""
        # Arrange
        analysis = IdleAnalysis(
            target="session:1",
            is_idle=True,
            idle_type=IdleType.NEWLY_IDLE,
            confidence=0.85,
            last_activity=datetime.now(),
            content_hash="abc123",
            error_detected=False,
            error_type=None,
        )

        # Act & Assert
        assert analysis.target == "session:1"
        assert analysis.is_idle is True
        assert analysis.idle_type == IdleType.NEWLY_IDLE
        assert analysis.confidence == 0.85
        assert analysis.last_activity is not None
        assert analysis.content_hash == "abc123"
        assert analysis.error_detected is False
        assert analysis.error_type is None

    def test_notification_event_dataclass(self, test_uuid: str) -> None:
        """Test NotificationEvent dataclass and formatted message."""
        # Arrange
        timestamp = datetime.now()
        event = NotificationEvent(
            type=NotificationType.AGENT_CRASH,
            target="session:1",
            message="Agent crashed",
            timestamp=timestamp,
            session="session",
            metadata={"error": "timeout"},
        )

        # Act & Assert
        assert event.type == NotificationType.AGENT_CRASH
        assert event.target == "session:1"
        assert event.message == "Agent crashed"
        assert event.timestamp == timestamp
        assert event.session == "session"
        assert event.metadata == {"error": "timeout"}
        assert event.formatted_message == "[session:session:1] Agent crashed"

    def test_monitor_status_dataclass(self, test_uuid: str) -> None:
        """Test MonitorStatus dataclass creation."""
        # Arrange
        uptime = timedelta(hours=2, minutes=30)
        status = MonitorStatus(
            is_running=True,
            active_agents=5,
            idle_agents=2,
            last_cycle_time=1.25,
            uptime=uptime,
            cycle_count=150,
            errors_detected=1,
            start_time=datetime.now(),
            end_time=None,
        )

        # Act & Assert
        assert status.is_running is True
        assert status.active_agents == 5
        assert status.idle_agents == 2
        assert status.last_cycle_time == 1.25
        assert status.uptime == uptime
        assert status.cycle_count == 150
        assert status.errors_detected == 1
        assert status.start_time is not None
        assert status.end_time is None

    def test_agent_state_dataclass(self, test_uuid: str) -> None:
        """Test AgentState dataclass initialization and defaults."""
        # Arrange
        state = AgentState(target="session:1", session="session", window="1")

        # Act & Assert
        assert state.target == "session:1"
        assert state.session == "session"
        assert state.window == "1"
        assert state.last_content is None
        assert state.last_content_hash is None
        assert state.last_activity is None
        assert state.consecutive_idle_count == 0
        assert state.submission_attempts == 0
        assert state.last_submission_time is None
        assert state.is_fresh is True
        assert state.error_count == 0
        assert state.last_error_time is None

    def test_plugin_info_dataclass(self, test_uuid: str) -> None:
        """Test PluginInfo dataclass with post_init processing."""
        # Arrange
        from pathlib import Path

        plugin = PluginInfo(
            name="test_plugin",
            file_path=Path("/path/to/plugin.py"),
            module_name="test_plugin",
            class_name="TestPlugin",
            status=PluginStatus.LOADED,
            description="Test plugin",
            version="1.0.0",
            author="Test Author",
        )

        # Act & Assert
        assert plugin.name == "test_plugin"
        assert plugin.file_path == Path("/path/to/plugin.py")
        assert plugin.module_name == "test_plugin"
        assert plugin.class_name == "TestPlugin"
        assert plugin.status == PluginStatus.LOADED
        assert plugin.description == "Test plugin"
        assert plugin.version == "1.0.0"
        assert plugin.author == "Test Author"
        assert plugin.dependencies == []  # Should be initialized by __post_init__


class TestMonitorComponent:
    """Test MonitorComponent base class."""

    def test_monitor_component_initialization(self, test_uuid: str) -> None:
        """Test MonitorComponent base initialization."""
        # Arrange
        mock_tmux = Mock(spec=TMUXManager)
        mock_config = Mock(spec=Config)
        mock_logger = Mock(spec=logging.Logger)

        # Create a concrete implementation for testing
        class TestComponent(MonitorComponent):
            def initialize(self) -> bool:
                return True

            def cleanup(self) -> None:
                pass

        # Act
        component = TestComponent(mock_tmux, mock_config, mock_logger)

        # Assert
        assert component.tmux is mock_tmux
        assert component.config is mock_config
        assert component.logger is mock_logger
        assert component.initialize() is True


class TestCrashDetectorInterface:
    """Test CrashDetectorInterface implementation requirements."""

    def test_crash_detector_interface_methods(self, test_uuid: str) -> None:
        """Test that CrashDetectorInterface defines required methods."""
        # Act & Assert
        assert hasattr(CrashDetectorInterface, "detect_crash")
        assert hasattr(CrashDetectorInterface, "detect_pm_crash")

        # Verify method signatures by checking they raise NotImplementedError
        class TestDetector(CrashDetectorInterface):
            pass

        TestDetector()

        with pytest.raises(TypeError):
            # Should fail to instantiate due to abstract methods
            pass

    def test_crash_detector_implementation(self, test_uuid: str) -> None:
        """Test concrete CrashDetectorInterface implementation."""

        # Arrange
        class ConcreteCrashDetector(CrashDetectorInterface):
            def detect_crash(self, agent_info, window_content, idle_duration=None):
                if "ERROR" in str(window_content):
                    return True, "Error detected in output"
                return False, None

            def detect_pm_crash(self, session_name):
                if session_name == "crashed-session":
                    return True, "crashed-session:pm"
                return False, None

        detector = ConcreteCrashDetector()
        agent_info = Mock()

        # Act & Assert
        # Test crash detection
        is_crashed, reason = detector.detect_crash(agent_info, ["ERROR: Something failed"], 10.0)
        assert is_crashed is True
        assert "Error detected" in reason

        # Test no crash
        is_crashed, reason = detector.detect_crash(agent_info, ["Normal output"], 5.0)
        assert is_crashed is False
        assert reason is None

        # Test PM crash detection
        is_crashed, target = detector.detect_pm_crash("crashed-session")
        assert is_crashed is True
        assert target == "crashed-session:pm"

        # Test no PM crash
        is_crashed, target = detector.detect_pm_crash("healthy-session")
        assert is_crashed is False
        assert target is None


class TestPMRecoveryManagerInterface:
    """Test PMRecoveryManagerInterface implementation requirements."""

    def test_pm_recovery_manager_methods(self, test_uuid: str) -> None:
        """Test PMRecoveryManagerInterface required methods."""
        # Act & Assert
        required_methods = [
            "initialize",
            "cleanup",
            "check_pm_health",
            "should_attempt_recovery",
            "recover_pm",
            "get_recovery_status",
        ]

        for method in required_methods:
            assert hasattr(PMRecoveryManagerInterface, method)

    def test_pm_recovery_manager_implementation(self, test_uuid: str) -> None:
        """Test concrete PMRecoveryManagerInterface implementation."""

        # Arrange
        class ConcreteRecoveryManager(PMRecoveryManagerInterface):
            def __init__(self):
                self.initialized = False
                self.recovery_attempts = {}

            def initialize(self) -> bool:
                self.initialized = True
                return True

            def cleanup(self) -> None:
                self.initialized = False

            def check_pm_health(self, session_name):
                if session_name == "healthy-session":
                    return True, "healthy-session:pm", None
                return False, None, "PM not responding"

            def should_attempt_recovery(self, session_name) -> bool:
                return session_name not in self.recovery_attempts or self.recovery_attempts[session_name] < 3

            def recover_pm(self, session_name, crashed_target=None) -> bool:
                if self.should_attempt_recovery(session_name):
                    self.recovery_attempts[session_name] = self.recovery_attempts.get(session_name, 0) + 1
                    return True
                return False

            def get_recovery_status(self) -> dict[str, Any]:
                return {"initialized": self.initialized, "recovery_attempts": self.recovery_attempts}

        manager = ConcreteRecoveryManager()

        # Act & Assert
        # Test initialization
        assert manager.initialize() is True
        assert manager.initialized is True

        # Test health check
        is_healthy, target, issue = manager.check_pm_health("healthy-session")
        assert is_healthy is True
        assert target == "healthy-session:pm"
        assert issue is None

        # Test unhealthy PM
        is_healthy, target, issue = manager.check_pm_health("unhealthy-session")
        assert is_healthy is False
        assert target is None
        assert "not responding" in issue

        # Test recovery
        assert manager.should_attempt_recovery("new-session") is True
        assert manager.recover_pm("new-session") is True

        # Test recovery status
        status = manager.get_recovery_status()
        assert status["initialized"] is True
        assert "new-session" in status["recovery_attempts"]

        # Test cleanup
        manager.cleanup()
        assert manager.initialized is False


class TestDaemonManagerInterface:
    """Test DaemonManagerInterface implementation requirements."""

    def test_daemon_manager_methods(self, test_uuid: str) -> None:
        """Test DaemonManagerInterface required methods."""
        required_methods = [
            "is_running",
            "get_pid",
            "start_daemon",
            "stop_daemon",
            "restart_daemon",
            "cleanup_stale_files",
            "should_shutdown",
            "get_daemon_info",
        ]

        for method in required_methods:
            assert hasattr(DaemonManagerInterface, method)

    def test_daemon_manager_implementation(self, test_uuid: str) -> None:
        """Test concrete DaemonManagerInterface implementation."""

        # Arrange
        class ConcreteDaemonManager(DaemonManagerInterface):
            def __init__(self):
                self.running = False
                self.pid = None
                self.shutdown_requested = False

            def is_running(self) -> bool:
                return self.running

            def get_pid(self) -> int | None:
                return self.pid if self.running else None

            def start_daemon(self, target_func, args=()) -> int:
                self.running = True
                self.pid = 12345
                return self.pid

            def stop_daemon(self, timeout=10) -> bool:
                if self.running:
                    self.running = False
                    self.pid = None
                    return True
                return False

            def restart_daemon(self, target_func, args=()) -> int:
                self.stop_daemon()
                return self.start_daemon(target_func, args)

            def cleanup_stale_files(self) -> None:
                pass  # Mock cleanup

            def should_shutdown(self) -> bool:
                return self.shutdown_requested

            def get_daemon_info(self) -> dict:
                return {"running": self.running, "pid": self.pid, "shutdown_requested": self.shutdown_requested}

        manager = ConcreteDaemonManager()

        # Act & Assert
        # Test initial state
        assert manager.is_running() is False
        assert manager.get_pid() is None

        # Test start daemon
        pid = manager.start_daemon(lambda: None)
        assert pid == 12345
        assert manager.is_running() is True
        assert manager.get_pid() == 12345

        # Test daemon info
        info = manager.get_daemon_info()
        assert info["running"] is True
        assert info["pid"] == 12345

        # Test stop daemon
        assert manager.stop_daemon() is True
        assert manager.is_running() is False
        assert manager.get_pid() is None

        # Test restart daemon
        new_pid = manager.restart_daemon(lambda: None)
        assert new_pid == 12345
        assert manager.is_running() is True


class TestHealthCheckerInterface:
    """Test HealthCheckerInterface implementation requirements."""

    @pytest.mark.asyncio
    async def test_health_checker_methods(self, test_uuid: str) -> None:
        """Test HealthCheckerInterface required methods."""
        required_methods = ["check_agent_health", "get_health_metrics"]

        for method in required_methods:
            assert hasattr(HealthCheckerInterface, method)

    @pytest.mark.asyncio
    async def test_health_checker_implementation(self, test_uuid: str) -> None:
        """Test concrete HealthCheckerInterface implementation."""

        # Arrange
        class ConcreteHealthChecker(HealthCheckerInterface):
            def __init__(self):
                self.health_data = {}

            async def check_agent_health(self, target) -> tuple[bool, str | None]:
                if target == "healthy:agent":
                    return True, None
                return False, "Agent not responding"

            async def get_health_metrics(self) -> dict[str, Any]:
                return {
                    "total_agents": 5,
                    "healthy_agents": 3,
                    "unhealthy_agents": 2,
                    "last_check": datetime.now().isoformat(),
                }

        checker = ConcreteHealthChecker()

        # Act & Assert
        # Test healthy agent
        is_healthy, issue = await checker.check_agent_health("healthy:agent")
        assert is_healthy is True
        assert issue is None

        # Test unhealthy agent
        is_healthy, issue = await checker.check_agent_health("unhealthy:agent")
        assert is_healthy is False
        assert "not responding" in issue

        # Test health metrics
        metrics = await checker.get_health_metrics()
        assert metrics["total_agents"] == 5
        assert metrics["healthy_agents"] == 3
        assert metrics["unhealthy_agents"] == 2
        assert "last_check" in metrics


class TestMonitorServiceInterface:
    """Test MonitorServiceInterface implementation requirements."""

    @pytest.mark.asyncio
    async def test_monitor_service_methods(self, test_uuid: str) -> None:
        """Test MonitorServiceInterface required methods."""
        required_methods = ["initialize", "cleanup", "run_monitoring_cycle", "get_component"]

        for method in required_methods:
            assert hasattr(MonitorServiceInterface, method)

    @pytest.mark.asyncio
    async def test_monitor_service_implementation(self, test_uuid: str) -> None:
        """Test concrete MonitorServiceInterface implementation."""

        # Arrange
        class ConcreteMonitorService(MonitorServiceInterface):
            def __init__(self):
                self.initialized = False
                self.components = {}

            def initialize(self) -> bool:
                self.initialized = True
                return True

            def cleanup(self) -> None:
                self.initialized = False
                self.components.clear()

            async def run_monitoring_cycle(self) -> MonitorStatus:
                return MonitorStatus(
                    is_running=self.initialized,
                    active_agents=3,
                    idle_agents=1,
                    last_cycle_time=0.5,
                    uptime=timedelta(minutes=30),
                    cycle_count=60,
                    errors_detected=0,
                )

            def get_component(self, component_type: str) -> Any | None:
                return self.components.get(component_type)

        service = ConcreteMonitorService()

        # Act & Assert
        # Test initialization
        assert service.initialize() is True
        assert service.initialized is True

        # Test monitoring cycle
        status = await service.run_monitoring_cycle()
        assert status.is_running is True
        assert status.active_agents == 3
        assert status.idle_agents == 1
        assert status.last_cycle_time == 0.5

        # Test component retrieval
        assert service.get_component("nonexistent") is None

        # Test cleanup
        service.cleanup()
        assert service.initialized is False


class TestServiceContainerInterface:
    """Test ServiceContainerInterface implementation requirements."""

    def test_service_container_methods(self, test_uuid: str) -> None:
        """Test ServiceContainerInterface required methods."""
        required_methods = ["register", "resolve", "has"]

        for method in required_methods:
            assert hasattr(ServiceContainerInterface, method)

    def test_service_container_implementation(self, test_uuid: str) -> None:
        """Test concrete ServiceContainerInterface implementation."""

        # Arrange
        class ConcreteServiceContainer(ServiceContainerInterface):
            def __init__(self):
                self.services = {}
                self.singletons = {}

            def register(self, interface_type: type, implementation: Any, singleton: bool = True) -> None:
                self.services[interface_type] = {"implementation": implementation, "singleton": singleton}

            def resolve(self, interface_type: type) -> Any:
                if interface_type not in self.services:
                    raise ValueError(f"Service {interface_type} not registered")

                service_info = self.services[interface_type]

                if service_info["singleton"]:
                    if interface_type not in self.singletons:
                        implementation = service_info["implementation"]
                        if callable(implementation):
                            self.singletons[interface_type] = implementation()
                        else:
                            self.singletons[interface_type] = implementation
                    return self.singletons[interface_type]
                else:
                    implementation = service_info["implementation"]
                    return implementation() if callable(implementation) else implementation

            def has(self, interface_type: type) -> bool:
                return interface_type in self.services

        container = ConcreteServiceContainer()

        # Act & Assert
        # Test registration and resolution
        class TestService:
            def __init__(self):
                self.value = "test"

        container.register(TestService, TestService, singleton=True)
        assert container.has(TestService) is True

        # Test singleton behavior
        service1 = container.resolve(TestService)
        service2 = container.resolve(TestService)
        assert service1 is service2  # Should be same instance
        assert service1.value == "test"

        # Test non-singleton registration
        container.register(str, lambda: "new_instance", singleton=False)
        instance1 = container.resolve(str)
        instance2 = container.resolve(str)
        assert instance1 == instance2 == "new_instance"

        # Test unregistered service
        with pytest.raises(ValueError):
            container.resolve(int)

        assert container.has(int) is False


class TestMonitoringStrategyInterface:
    """Test MonitoringStrategyInterface implementation requirements."""

    @pytest.mark.asyncio
    async def test_monitoring_strategy_methods(self, test_uuid: str) -> None:
        """Test MonitoringStrategyInterface required methods."""
        required_methods = ["get_name", "get_description", "execute", "get_required_components"]

        for method in required_methods:
            assert hasattr(MonitoringStrategyInterface, method)

    @pytest.mark.asyncio
    async def test_monitoring_strategy_implementation(self, test_uuid: str) -> None:
        """Test concrete MonitoringStrategyInterface implementation."""

        # Arrange
        class ConcreteMonitoringStrategy(MonitoringStrategyInterface):
            def get_name(self) -> str:
                return "test_strategy"

            def get_description(self) -> str:
                return "Test monitoring strategy"

            async def execute(self, context: dict[str, Any]) -> MonitorStatus:
                return MonitorStatus(
                    is_running=True,
                    active_agents=context.get("agent_count", 0),
                    idle_agents=0,
                    last_cycle_time=0.3,
                    uptime=timedelta(minutes=15),
                    cycle_count=30,
                    errors_detected=0,
                )

            def get_required_components(self) -> list[type]:
                return [TMUXManager, Config]

        strategy = ConcreteMonitoringStrategy()

        # Act & Assert
        assert strategy.get_name() == "test_strategy"
        assert strategy.get_description() == "Test monitoring strategy"

        required_components = strategy.get_required_components()
        assert TMUXManager in required_components
        assert Config in required_components

        # Test execution
        context = {"agent_count": 5}
        status = await strategy.execute(context)
        assert status.is_running is True
        assert status.active_agents == 5
        assert status.idle_agents == 0


class TestMonitoringPerformance:
    """Performance tests for monitoring components."""

    def test_agent_info_creation_performance(self, test_uuid: str) -> None:
        """Test AgentInfo creation performance for large numbers."""
        start_time = time.time()

        agents = []
        for i in range(1000):
            agent = AgentInfo(
                target=f"session-{i}:window-{i}",
                session=f"session-{i}",
                window=f"window-{i}",
                name=f"agent-{i}",
                type="developer",
                status="active",
                last_seen=datetime.now(),
            )
            agents.append(agent)

        creation_time = time.time() - start_time

        assert len(agents) == 1000
        assert creation_time < 1.0, f"AgentInfo creation took {creation_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

        # Test property access performance
        start_time = time.time()
        display_names = [agent.display_name for agent in agents]
        access_time = time.time() - start_time

        assert len(display_names) == 1000
        assert access_time < 0.5, f"Property access took {access_time:.3f}s (>0.5s limit) - Test ID: {test_uuid}"

    def test_notification_event_batch_creation(self, test_uuid: str) -> None:
        """Test batch creation of notification events."""
        start_time = time.time()

        events = []
        timestamp = datetime.now()

        for i in range(500):
            event = NotificationEvent(
                type=NotificationType.AGENT_IDLE,
                target=f"session-{i}:agent-{i}",
                message=f"Agent {i} is idle",
                timestamp=timestamp,
                session=f"session-{i}",
                metadata={"idle_duration": i * 10},
            )
            events.append(event)

        creation_time = time.time() - start_time

        assert len(events) == 500
        assert creation_time < 1.0, f"Batch event creation took {creation_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

        # Test formatted message generation performance
        start_time = time.time()
        formatted = [event.formatted_message for event in events]
        format_time = time.time() - start_time

        assert len(formatted) == 500
        assert format_time < 0.5, f"Message formatting took {format_time:.3f}s (>0.5s limit) - Test ID: {test_uuid}"


class TestMonitoringEdgeCases:
    """Edge case tests for monitoring components."""

    def test_agent_info_with_special_characters(self, test_uuid: str) -> None:
        """Test AgentInfo with special characters and unicode."""
        # Arrange
        agent = AgentInfo(
            target="session-测试:window-1",
            session="session-测试",
            window="window-1",
            name="developer-🚀",
            type="frontend-dev",
            status="active-👍",
            last_seen=datetime.now(),
        )

        # Act & Assert
        assert agent.target == "session-测试:window-1"
        assert agent.session == "session-测试"
        assert agent.name == "developer-🚀"
        assert agent.type == "frontend-dev"
        assert agent.status == "active-👍"
        assert agent.display_name == "developer-🚀 (frontend-dev)"

    def test_notification_event_with_large_metadata(self, test_uuid: str) -> None:
        """Test NotificationEvent with large metadata objects."""
        # Arrange
        large_metadata = {
            "error_log": "ERROR: " + "x" * 1000,  # Large error message
            "stack_trace": ["frame" + str(i) for i in range(100)],
            "environment": {f"var_{i}": f"value_{i}" for i in range(50)},
            "history": [{"timestamp": datetime.now(), "event": f"event_{i}"} for i in range(20)],
        }

        event = NotificationEvent(
            type=NotificationType.AGENT_CRASH,
            target="session:agent",
            message="Agent crashed with large context",
            timestamp=datetime.now(),
            session="session",
            metadata=large_metadata,
        )

        # Act & Assert
        assert event.type == NotificationType.AGENT_CRASH
        assert len(event.metadata["error_log"]) > 1000
        assert len(event.metadata["stack_trace"]) == 100
        assert len(event.metadata["environment"]) == 50
        assert len(event.metadata["history"]) == 20

    def test_monitor_status_with_extreme_values(self, test_uuid: str) -> None:
        """Test MonitorStatus with extreme values."""
        # Arrange
        very_long_uptime = timedelta(days=365, hours=23, minutes=59, seconds=59)

        status = MonitorStatus(
            is_running=True,
            active_agents=999999,
            idle_agents=0,
            last_cycle_time=0.001,  # Very fast cycle
            uptime=very_long_uptime,
            cycle_count=999999999,  # Very high cycle count
            errors_detected=0,
            start_time=datetime.now() - very_long_uptime,
            end_time=None,
        )

        # Act & Assert
        assert status.is_running is True
        assert status.active_agents == 999999
        assert status.last_cycle_time == 0.001
        assert status.uptime.days == 365
        assert status.cycle_count == 999999999

    def test_agent_state_edge_case_values(self, test_uuid: str) -> None:
        """Test AgentState with edge case values."""
        # Arrange
        very_old_time = datetime.now() - timedelta(days=30)

        state = AgentState(
            target="session:agent",
            session="session",
            window="agent",
            last_content="",  # Empty content
            last_content_hash="",  # Empty hash
            last_activity=very_old_time,
            consecutive_idle_count=999999,  # Very high idle count
            submission_attempts=0,
            last_submission_time=None,
            is_fresh=False,
            error_count=999,  # High error count
            last_error_time=very_old_time,
        )

        # Act & Assert
        assert state.target == "session:agent"
        assert state.last_content == ""
        assert state.last_content_hash == ""
        assert state.consecutive_idle_count == 999999
        assert state.error_count == 999
        assert state.is_fresh is False

    def test_plugin_info_with_missing_optional_fields(self, test_uuid: str) -> None:
        """Test PluginInfo with minimal required fields."""
        # Arrange
        from pathlib import Path

        plugin = PluginInfo(
            name="minimal_plugin",
            file_path=Path("/path/to/plugin.py"),
            module_name="minimal_plugin",
            class_name="MinimalPlugin",
            status=PluginStatus.DISCOVERED,
            # All optional fields omitted
        )

        # Act & Assert
        assert plugin.name == "minimal_plugin"
        assert plugin.file_path == Path("/path/to/plugin.py")
        assert plugin.status == PluginStatus.DISCOVERED
        assert plugin.description is None
        assert plugin.version is None
        assert plugin.author is None
        assert plugin.instance is None
        assert plugin.error is None
        assert plugin.dependencies == []  # Should be set by __post_init__
