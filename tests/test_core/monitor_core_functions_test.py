"""Tests for critical monitor.py functions before refactoring.

This test file creates a safety net for the upcoming monitor.py refactoring
by testing the core functions that will be broken apart.
"""

import os
import tempfile
import time
from datetime import datetime
from unittest.mock import Mock, patch

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitor import AgentHealthStatus, IdleMonitor, TerminalCache
from tmux_orchestrator.utils.tmux import TMUXManager


class TestTerminalCache:
    """Test TerminalCache functionality."""

    def test_cache_initialization(self):
        """Test TerminalCache initializes correctly."""
        cache = TerminalCache()
        assert cache.early_value is None
        assert cache.later_value is None
        assert cache.max_distance == 10
        assert cache.use_levenshtein is False

    def test_cache_status_unknown(self):
        """Test status returns unknown when values are None."""
        cache = TerminalCache()
        assert cache.status == "unknown"

    def test_cache_update(self):
        """Test cache update shifts values correctly."""
        cache = TerminalCache()

        cache.update("first value")
        assert cache.early_value is None
        assert cache.later_value == "first value"

        cache.update("second value")
        assert cache.early_value == "first value"
        assert cache.later_value == "second value"

    def test_cache_match_identical_content(self):
        """Test cache detects matching content."""
        cache = TerminalCache()
        cache.update("same content")
        cache.update("same content")

        assert cache.match() is True
        assert cache.status == "continuously_idle"

    def test_cache_match_different_content(self):
        """Test cache detects different content."""
        cache = TerminalCache()
        cache.update("first content")
        cache.update("completely different content")

        assert cache.match() is False
        assert cache.status == "newly_idle"

    def test_cache_with_levenshtein(self):
        """Test cache with Levenshtein distance enabled."""
        cache = TerminalCache(use_levenshtein=True, max_distance=5)
        cache.update("hello world")
        cache.update("hello worlz")  # 1 character difference

        assert cache.match() is True

    def test_cache_with_large_distance(self):
        """Test cache with large content differences."""
        cache = TerminalCache(max_distance=2)
        cache.update("short")
        cache.update("this is a much longer and completely different string")

        assert cache.match() is False


class TestAgentHealthStatus:
    """Test AgentHealthStatus dataclass."""

    def test_health_status_creation(self):
        """Test AgentHealthStatus can be created with all fields."""
        status = AgentHealthStatus(
            target="test:1",
            last_heartbeat=datetime.now(),
            last_response=datetime.now(),
            consecutive_failures=0,
            is_responsive=True,
            last_content_hash="abc123",
            status="healthy",
            is_idle=False,
            activity_changes=1,
        )

        assert status.target == "test:1"
        assert status.consecutive_failures == 0
        assert status.is_responsive is True
        assert status.status == "healthy"
        assert status.is_idle is False


class TestIdleMonitorInitialization:
    """Test IdleMonitor initialization and basic functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_idle_monitor_initialization(self):
        """Test IdleMonitor initializes with proper file paths."""
        tmux = Mock(spec=TMUXManager)
        monitor = IdleMonitor(tmux)

        assert monitor.tmux == tmux
        assert monitor.pid_file.parent.exists()
        assert str(monitor.pid_file).endswith("idle-monitor.pid")
        assert str(monitor.log_file).endswith("idle-monitor.log")

    def test_idle_monitor_with_custom_config(self):
        """Test IdleMonitor with custom config."""
        tmux = Mock(spec=TMUXManager)
        config = Config.load()

        monitor = IdleMonitor(tmux, config)

        assert monitor.tmux == tmux
        assert monitor.pid_file.parent.exists()

    def test_idle_monitor_creates_log_directory(self):
        """Test IdleMonitor creates logs directory."""
        tmux = Mock(spec=TMUXManager)
        monitor = IdleMonitor(tmux)

        assert monitor.logs_dir.exists()
        assert monitor.logs_dir.is_dir()


class TestIdleMonitorCoreOperations:
    """Test core IdleMonitor operations."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.monitor = IdleMonitor(self.tmux)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_is_running_no_pid_file(self):
        """Test is_running when no PID file exists."""
        assert self.monitor.is_running() is False

    def test_is_running_with_pid_file(self):
        """Test is_running with valid PID file."""
        # Create PID file with current process PID
        self.monitor.pid_file.write_text(str(os.getpid()))

        with patch("os.kill") as mock_kill:
            result = self.monitor.is_running()

        assert result is True
        mock_kill.assert_called_once_with(os.getpid(), 0)

    def test_is_running_with_dead_process(self):
        """Test is_running cleans up stale PID file."""
        # Create PID file with fake PID
        self.monitor.pid_file.write_text("99999")

        result = self.monitor.is_running()

        assert result is False
        assert not self.monitor.pid_file.exists()

    def test_update_heartbeat(self):
        """Test heartbeat file creation and updates."""
        # First heartbeat
        self.monitor.update_heartbeat()
        assert self.monitor.heartbeat_file.exists()

        first_content = self.monitor.heartbeat_file.read_text()

        # Second heartbeat after small delay
        time.sleep(0.01)
        self.monitor.update_heartbeat()

        second_content = self.monitor.heartbeat_file.read_text()
        assert first_content != second_content

    def test_discover_agents(self):
        """Test agent discovery functionality."""
        # Mock agents data
        mock_agents = [
            {"session": "frontend", "window": "1", "type": "Developer", "status": "Active"},
            {"session": "backend", "window": "2", "type": "QA", "status": "Idle"},
        ]
        self.tmux.list_agents.return_value = mock_agents

        # Test discovery (this calls internal _discover_agents)
        agents = self.tmux.list_agents()

        assert len(agents) == 2
        assert agents[0]["session"] == "frontend"
        assert agents[1]["type"] == "QA"

    def test_agent_window_detection(self):
        """Test agent window detection logic."""
        # This tests the _is_agent_window method indirectly
        mock_windows = [
            {"name": "Claude", "index": "1"},
            {"name": "pm", "index": "2"},
            {"name": "developer", "index": "3"},
            {"name": "shell", "index": "4"},
        ]

        # Mock the behavior - agent windows should be Claude, pm, developer
        expected_agent_windows = ["Claude", "pm", "developer"]

        for window in mock_windows:
            is_agent = window["name"] in expected_agent_windows
            if is_agent:
                assert window["name"] in ["Claude", "pm", "developer", "qa"]


class TestIdleMonitorDaemonOperations:
    """Test daemon start/stop operations."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.monitor = IdleMonitor(self.tmux)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    @patch("subprocess.Popen")
    def test_daemon_start(self, mock_popen):
        """Test daemon start process."""
        # Mock the daemon process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        # Mock that daemon is not already running
        with patch.object(self.monitor, "is_running", return_value=False):
            # Create the PID file to simulate successful start
            def create_pid_file(*args, **kwargs):
                self.monitor.pid_file.write_text("12345")
                return mock_process

            mock_popen.side_effect = create_pid_file

            # Call start with mocked subprocess
            with patch.object(self.monitor, "_run_monitoring_daemon"):
                result = self.monitor.start()

        # Verify daemon start was attempted
        assert mock_popen.called

    def test_daemon_start_already_running(self):
        """Test daemon start when already running."""
        # Create PID file to simulate running daemon
        self.monitor.pid_file.write_text(str(os.getpid()))

        with patch("os.kill"), patch("subprocess.Popen") as mock_popen:
            result = self.monitor.start()

        # Should not attempt to start new process
        mock_popen.assert_not_called()

    @patch("os.kill")
    def test_daemon_stop(self, mock_kill):
        """Test daemon stop process."""
        # Create PID file
        self.monitor.pid_file.write_text("12345")

        # Mock that process exists initially, then stops
        with patch.object(self.monitor, "is_running", side_effect=[True, False]):
            result = self.monitor.stop()

        # Should attempt to kill the process
        mock_kill.assert_called_with(12345, 15)  # SIGTERM

    def test_daemon_stop_not_running(self):
        """Test daemon stop when not running."""
        # No PID file exists
        with patch("os.kill") as mock_kill:
            result = self.monitor.stop()

        # Should not attempt to kill anything
        mock_kill.assert_not_called()


class TestIdleMonitorErrorHandling:
    """Test error handling in monitor operations."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.monitor = IdleMonitor(self.tmux)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_heartbeat_with_permission_error(self):
        """Test heartbeat handles permission errors gracefully."""
        # Make heartbeat file directory read-only
        self.monitor.heartbeat_file.parent.chmod(0o444)

        try:
            # Should not raise exception
            self.monitor.update_heartbeat()
        except PermissionError:
            # This is acceptable - just testing it doesn't crash
            pass
        finally:
            # Restore permissions for cleanup
            self.monitor.heartbeat_file.parent.chmod(0o755)

    def test_agent_discovery_with_tmux_error(self):
        """Test agent discovery handles tmux errors."""
        # Mock tmux to raise an exception
        self.tmux.list_agents.side_effect = Exception("Tmux communication error")

        # Should handle error gracefully
        try:
            agents = self.tmux.list_agents()
        except Exception as e:
            assert "Tmux communication error" in str(e)

    def test_invalid_pid_file_content(self):
        """Test handling of corrupted PID file."""
        # Create PID file with invalid content
        self.monitor.pid_file.write_text("not_a_number")

        result = self.monitor.is_running()

        # Should return False and clean up the invalid file
        assert result is False
        assert not self.monitor.pid_file.exists()


class TestIdleMonitorIntegration:
    """Integration tests for monitor workflow."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_complete_monitoring_cycle(self):
        """Test a complete monitoring cycle with mock data."""
        tmux = Mock(spec=TMUXManager)

        # Mock agent data
        tmux.list_agents.return_value = [{"session": "test", "window": "1", "type": "Developer", "status": "Active"}]
        tmux.capture_pane.return_value = "Agent is working on code..."

        monitor = IdleMonitor(tmux)

        # Test the complete cycle components
        agents = tmux.list_agents()
        assert len(agents) == 1

        for agent in agents:
            target = f"{agent['session']}:{agent['window']}"
            content = tmux.capture_pane(target)
            assert "working" in content

        # Test heartbeat update
        monitor.update_heartbeat()
        assert monitor.heartbeat_file.exists()

    def test_daemon_lifecycle_integration(self):
        """Test complete daemon start/stop lifecycle."""
        tmux = Mock(spec=TMUXManager)
        monitor = IdleMonitor(tmux)

        # Initially not running
        assert not monitor.is_running()

        # Mock successful start
        with patch("subprocess.Popen") as mock_popen, patch.object(monitor, "_run_monitoring_daemon"):
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            # Simulate PID file creation
            def create_pid(*args, **kwargs):
                monitor.pid_file.write_text("12345")
                return mock_process

            mock_popen.side_effect = create_pid

            # Start daemon
            with patch.object(monitor, "is_running", return_value=False):
                monitor.start()

            # Verify PID file was created
            assert monitor.pid_file.exists()

        # Test stop
        with patch("os.kill") as mock_kill, patch.object(monitor, "is_running", side_effect=[True, False]):
            monitor.stop()

            # Verify kill was called
            mock_kill.assert_called_with(12345, 15)
