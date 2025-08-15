"""Tests for DaemonSupervisor."""

import os
import tempfile
import time
from unittest.mock import Mock, patch

from tmux_orchestrator.core.daemon_supervisor import DaemonSupervisor


class TestDaemonSupervisor:
    """Test DaemonSupervisor functionality."""

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

    def test_init_creates_supervisor(self):
        """Test that DaemonSupervisor initializes correctly."""
        supervisor = DaemonSupervisor("test-daemon")

        assert supervisor.daemon_name == "test-daemon"
        assert supervisor.pid_file.parent.exists()
        assert str(supervisor.pid_file).endswith("test-daemon.pid")
        assert str(supervisor.heartbeat_file).endswith("test-daemon.heartbeat")
        assert str(supervisor.supervisor_pid_file).endswith("test-daemon-supervisor.pid")
        assert str(supervisor.graceful_stop_file).endswith("test-daemon.graceful")

    def test_init_uses_configurable_path(self):
        """Test that DaemonSupervisor uses configurable base directory."""
        supervisor = DaemonSupervisor("test-daemon")

        # Should use environment variable path
        assert str(supervisor.pid_file.parent) == self.test_dir

    def test_is_daemon_running_no_pid_file(self):
        """Test is_daemon_running when no PID file exists."""
        supervisor = DaemonSupervisor("test-daemon")

        assert not supervisor.is_daemon_running()

    def test_is_daemon_running_invalid_pid(self):
        """Test is_daemon_running with invalid PID in file."""
        supervisor = DaemonSupervisor("test-daemon")

        # Create PID file with invalid PID
        supervisor.pid_file.write_text("invalid_pid")

        assert not supervisor.is_daemon_running()

    def test_is_daemon_running_nonexistent_pid(self):
        """Test is_daemon_running with nonexistent PID."""
        supervisor = DaemonSupervisor("test-daemon")

        # Create PID file with nonexistent PID
        supervisor.pid_file.write_text("99999")

        assert not supervisor.is_daemon_running()

    @patch("os.kill")
    def test_is_daemon_running_valid_pid(self, mock_kill):
        """Test is_daemon_running with valid PID."""
        supervisor = DaemonSupervisor("test-daemon")

        # Create PID file with current process PID
        supervisor.pid_file.write_text(str(os.getpid()))

        assert supervisor.is_daemon_running()
        mock_kill.assert_called_once_with(os.getpid(), 0)

    @patch("os.kill", side_effect=ProcessLookupError())
    def test_is_daemon_running_dead_process(self, mock_kill):
        """Test is_daemon_running with dead process PID."""
        supervisor = DaemonSupervisor("test-daemon")

        # Create PID file with current process PID
        supervisor.pid_file.write_text(str(os.getpid()))

        assert not supervisor.is_daemon_running()
        # Should clean up the stale PID file
        assert not supervisor.pid_file.exists()

    def test_is_daemon_healthy_no_process(self):
        """Test is_daemon_healthy when daemon is not running."""
        supervisor = DaemonSupervisor("test-daemon")

        assert not supervisor.is_daemon_healthy()

    @patch.object(DaemonSupervisor, "is_daemon_running", return_value=True)
    def test_is_daemon_healthy_no_heartbeat(self, mock_running):
        """Test is_daemon_healthy when no heartbeat file exists."""
        supervisor = DaemonSupervisor("test-daemon")

        assert not supervisor.is_daemon_healthy()

    @patch.object(DaemonSupervisor, "is_daemon_running", return_value=True)
    def test_is_daemon_healthy_fresh_heartbeat(self, mock_running):
        """Test is_daemon_healthy with fresh heartbeat."""
        supervisor = DaemonSupervisor("test-daemon")

        # Create fresh heartbeat file
        supervisor.heartbeat_file.touch()

        assert supervisor.is_daemon_healthy()

    @patch.object(DaemonSupervisor, "is_daemon_running", return_value=True)
    def test_is_daemon_healthy_stale_heartbeat(self, mock_running):
        """Test is_daemon_healthy with stale heartbeat."""
        supervisor = DaemonSupervisor("test-daemon")

        # Create old heartbeat file
        supervisor.heartbeat_file.touch()
        # Make it old by modifying the access time
        old_time = time.time() - supervisor.heartbeat_timeout - 10
        os.utime(supervisor.heartbeat_file, (old_time, old_time))

        assert not supervisor.is_daemon_healthy()

    @patch("subprocess.Popen")
    def test_start_daemon_already_running(self, mock_popen):
        """Test start_daemon when daemon is already running."""
        supervisor = DaemonSupervisor("test-daemon")

        with patch.object(supervisor, "is_daemon_running", return_value=True):
            result = supervisor.start_daemon(["python", "-c", "print('test')"])

        assert result is True
        mock_popen.assert_not_called()

    @patch("subprocess.Popen")
    @patch("time.sleep")  # Speed up the test
    def test_start_daemon_success(self, mock_sleep, mock_popen):
        """Test successful daemon start."""
        supervisor = DaemonSupervisor("test-daemon")

        # Mock the process and ensure PID file is created during the loop
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        def create_pid_file(*args, **kwargs):
            supervisor.pid_file.write_text("12345")

        mock_sleep.side_effect = create_pid_file

        with patch.object(supervisor, "is_daemon_running", return_value=True):
            result = supervisor.start_daemon(["python", "-c", "print('test')"])

        assert result is True

    @patch("subprocess.Popen", side_effect=Exception("Start failed"))
    def test_start_daemon_failure(self, mock_popen):
        """Test daemon start failure."""
        supervisor = DaemonSupervisor("test-daemon")

        result = supervisor.start_daemon(["invalid-command"])

        assert result is False

    @patch("os.kill")
    def test_stop_daemon_graceful(self, mock_kill):
        """Test graceful daemon stop."""
        supervisor = DaemonSupervisor("test-daemon")

        # Set up running daemon
        supervisor.pid_file.write_text("12345")

        with patch.object(supervisor, "is_daemon_running", side_effect=[True, False]):
            result = supervisor.stop_daemon()

        assert result is True
        mock_kill.assert_called_with(12345, 15)  # SIGTERM

    def test_stop_daemon_no_pid_file(self):
        """Test stop daemon when no PID file exists."""
        supervisor = DaemonSupervisor("test-daemon")

        result = supervisor.stop_daemon()

        assert result is True  # Success because daemon is already stopped

    def test_get_status_basic(self):
        """Test get_status returns proper status dictionary."""
        supervisor = DaemonSupervisor("test-daemon")

        status = supervisor.get_status()

        assert isinstance(status, dict)
        assert "daemon_running" in status
        assert "daemon_healthy" in status
        assert isinstance(status["daemon_running"], bool)
        assert isinstance(status["daemon_healthy"], bool)

    def test_different_daemon_names_separate_files(self):
        """Test that different daemon names create separate files."""
        supervisor1 = DaemonSupervisor("daemon1")
        supervisor2 = DaemonSupervisor("daemon2")

        assert supervisor1.pid_file != supervisor2.pid_file
        assert supervisor1.heartbeat_file != supervisor2.heartbeat_file
        assert supervisor1.supervisor_pid_file != supervisor2.supervisor_pid_file
        assert supervisor1.graceful_stop_file != supervisor2.graceful_stop_file

    def test_configuration_attributes(self):
        """Test that supervisor has proper configuration attributes."""
        supervisor = DaemonSupervisor("test-daemon")

        assert hasattr(supervisor, "heartbeat_timeout")
        assert hasattr(supervisor, "check_interval")
        assert isinstance(supervisor.heartbeat_timeout, int)
        assert isinstance(supervisor.check_interval, int)
        assert supervisor.heartbeat_timeout > 0
        assert supervisor.check_interval > 0


class TestDaemonSupervisorIntegration:
    """Integration tests for DaemonSupervisor."""

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

    @patch("subprocess.Popen")
    @patch("time.sleep")
    def test_restart_daemon_with_backoff(self, mock_sleep, mock_popen):
        """Test restart_daemon_with_backoff functionality."""
        supervisor = DaemonSupervisor("test-daemon")

        # Mock successful restart
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        def create_pid_file(*args, **kwargs):
            supervisor.pid_file.write_text("12345")

        mock_sleep.side_effect = create_pid_file

        with patch.object(supervisor, "is_daemon_running", return_value=True):
            result = supervisor.restart_daemon_with_backoff(["sleep", "10"])

        assert result is True

    def test_status_integration(self):
        """Test complete status check integration."""
        supervisor = DaemonSupervisor("test-status")

        # Test initial state
        status = supervisor.get_status()
        assert not status["daemon_running"]
        assert not status["daemon_healthy"]
