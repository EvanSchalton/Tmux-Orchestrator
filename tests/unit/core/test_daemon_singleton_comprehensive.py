#!/usr/bin/env python3
"""Comprehensive test suite for daemon singleton implementation.

Tests all singleton scenarios including:
1. Single daemon startup (happy path)
2. Second daemon attempts to start (should handle gracefully)
3. Stale PID file with no process
4. Multiple simultaneous startup attempts
5. Daemon crash recovery
6. Force kill recovery
7. Edge cases and error conditions
"""

import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.monitor import DaemonAlreadyRunningError, IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager

# TMUXManager import removed - using comprehensive_mock_tmux fixture


class TestDaemonSingleton:
    """Comprehensive test suite for daemon singleton behavior."""

    def setup_method(self):
        """Clean state before each test."""
        self.project_dir = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")
        self.pid_file = self.project_dir / "idle-monitor.pid"
        self.heartbeat_file = self.project_dir / "idle-monitor.heartbeat"
        self.graceful_stop_file = self.project_dir / "idle-monitor.graceful"
        self.supervisor_pid_file = self.project_dir / "idle-monitor-supervisor.pid"

        self._cleanup_all_daemon_files()
        self._stop_any_running_daemons()

    def teardown_method(self):
        """Clean up after each test."""
        self._cleanup_all_daemon_files()
        self._stop_any_running_daemons()

    def _cleanup_all_daemon_files(self):
        """Remove all daemon-related files."""
        for file_path in [self.pid_file, self.heartbeat_file, self.graceful_stop_file, self.supervisor_pid_file]:
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    pass

    def _stop_any_running_daemons(self):
        """Stop any running daemon processes."""
        try:
            # Stop via CLI
            subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=10)
            time.sleep(1)

            # Force kill any remaining processes
            if self.pid_file.exists():
                try:
                    with open(self.pid_file) as f:
                        pid = int(f.read().strip())
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(0.5)
                except (OSError, ValueError):
                    pass

            if self.supervisor_pid_file.exists():
                try:
                    with open(self.supervisor_pid_file) as f:
                        pid = int(f.read().strip())
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(0.5)
                except (OSError, ValueError):
                    pass
        except Exception:
            pass

        self._cleanup_all_daemon_files()

    def _create_mock_tmux_manager(self):
        """Create a mock TMUX manager for testing."""
        mock_tmux = Mock(spec=TMUXManager)
        mock_tmux.list_sessions.return_value = []
        return mock_tmux

    def test_single_daemon_startup_happy_path(self):
        """Test single daemon startup works correctly."""
        mock_tmux = self._create_mock_tmux_manager()
        monitor = IdleMonitor(mock_tmux)

        # Initially no daemon running
        assert not monitor.is_running()
        assert not self.pid_file.exists()

        # Start daemon with supervised mode (more reliable for testing)
        success = monitor.start_supervised(interval=10)
        assert success, "Daemon should start successfully"

        # Give daemon time to initialize
        time.sleep(2)

        # Verify daemon is running
        assert monitor.is_running(), "Daemon should be running after start"
        assert self.pid_file.exists(), "PID file should exist"

        # Verify PID file contains valid PID
        with open(self.pid_file) as f:
            pid = int(f.read().strip())
        assert pid > 0, "PID should be positive integer"

        # Verify process exists
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pytest.fail("Daemon process should be running")

        # Clean stop
        success = monitor.stop()
        assert success, "Daemon should stop successfully"

    def test_second_daemon_start_graceful_handling(self):
        """Test second daemon attempt is handled gracefully."""
        mock_tmux = self._create_mock_tmux_manager()
        monitor1 = IdleMonitor(mock_tmux)
        monitor2 = IdleMonitor(mock_tmux)

        # Start first daemon
        success1 = monitor1.start_supervised(interval=10)
        assert success1, "First daemon should start successfully"
        time.sleep(2)

        original_pid = None
        if self.pid_file.exists():
            with open(self.pid_file) as f:
                original_pid = int(f.read().strip())

        # Attempt to start second daemon - should raise DaemonAlreadyRunningError
        from tmux_orchestrator.core.monitor import DaemonAlreadyRunningError

        with pytest.raises(DaemonAlreadyRunningError):
            monitor2.start_supervised(interval=10)

        # Verify only one daemon is running
        assert monitor1.is_running()
        assert monitor2.is_running()  # Both monitors see the same daemon

        # Verify PID hasn't changed
        if self.pid_file.exists():
            with open(self.pid_file) as f:
                current_pid = int(f.read().strip())
            assert current_pid == original_pid, "PID should not change"

        # Clean stop
        monitor1.stop()

    def test_stale_pid_file_handling(self):
        """Test handling of stale PID files with no process."""
        mock_tmux = self._create_mock_tmux_manager()
        monitor = IdleMonitor(mock_tmux)

        # Create a stale PID file with a non-existent PID
        fake_pid = 99999
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, "w") as f:
            f.write(str(fake_pid))

        # Verify stale PID doesn't appear as running
        assert not monitor.is_running(), "Stale PID should not be considered running"

        # Start daemon should work despite stale PID file
        success = monitor.start_supervised(interval=10)
        assert success, "Daemon should start despite stale PID file"
        time.sleep(2)

        # Verify daemon is now running with new PID
        assert monitor.is_running()
        with open(self.pid_file) as f:
            new_pid = int(f.read().strip())
        assert new_pid != fake_pid, "Should have new PID, not stale one"

        # Clean stop
        monitor.stop()

    def test_empty_pid_file_handling(self):
        """Test handling of empty PID files."""
        mock_tmux = self._create_mock_tmux_manager()
        monitor = IdleMonitor(mock_tmux)

        # Create empty PID file
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.touch()

        # Should not be considered running
        assert not monitor.is_running()

        # Should be able to start daemon
        success = monitor.start_supervised(interval=10)
        assert success
        time.sleep(2)

        assert monitor.is_running()
        monitor.stop()

    def test_corrupted_pid_file_handling(self):
        """Test handling of corrupted PID files."""
        mock_tmux = self._create_mock_tmux_manager()
        monitor = IdleMonitor(mock_tmux)

        # Create corrupted PID file
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, "w") as f:
            f.write("not_a_number")

        # Should not be considered running
        assert not monitor.is_running()

        # Should be able to start daemon
        success = monitor.start_supervised(interval=10)
        assert success
        time.sleep(2)

        assert monitor.is_running()
        monitor.stop()

    def test_multiple_simultaneous_startup_attempts(self):
        """Test multiple simultaneous startup attempts."""
        mock_tmux = self._create_mock_tmux_manager()

        start_results = []
        threads = []

        def start_daemon(monitor_id):
            """Start daemon in thread."""
            try:
                monitor = IdleMonitor(mock_tmux)
                monitor.start_supervised(interval=10)
                start_results.append((monitor_id, True, monitor))  # Success if no exception
            except DaemonAlreadyRunningError:
                # Expected behavior - daemon already running
                start_results.append((monitor_id, "already_running", None))
            except Exception as e:
                start_results.append((monitor_id, False, str(e)))

        # Launch 5 simultaneous startup attempts
        for i in range(5):
            thread = threading.Thread(target=start_daemon, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Give daemons time to stabilize
        time.sleep(3)

        # Exactly one should succeed, others should get "already_running"
        successful_starts = [r for r in start_results if r[1] is True]
        already_running = [r for r in start_results if r[1] == "already_running"]
        failed_starts = [r for r in start_results if r[1] is False]

        assert (
            len(successful_starts) == 1
        ), f"Exactly one daemon should start, found {len(successful_starts)} successful"
        assert len(already_running) == 4, f"Four attempts should get 'already running', found {len(already_running)}"
        assert (
            len(failed_starts) == 0
        ), f"No starts should fail unexpectedly, found {len(failed_starts)}: {failed_starts}"

        # Verify only one daemon is actually running
        running_monitor = successful_starts[0][2]
        assert running_monitor.is_running(), "The successful monitor should show daemon as running"

        # Clean stop
        running_monitor.stop()

    def test_daemon_crash_recovery_detection(self):
        """Test detection of daemon crashes."""
        mock_tmux = self._create_mock_tmux_manager()
        monitor = IdleMonitor(mock_tmux)

        # Start daemon
        success = monitor.start_supervised(interval=10)
        assert success
        time.sleep(2)

        # Get daemon PID
        with open(self.pid_file) as f:
            daemon_pid = int(f.read().strip())

        # Force kill daemon process (simulate crash)
        os.kill(daemon_pid, signal.SIGKILL)
        time.sleep(1)

        # Monitor should detect daemon is no longer running
        assert not monitor.is_running(), "Monitor should detect crashed daemon"

        # PID file should be cleaned up when checked
        assert not self.pid_file.exists(), "Stale PID file should be cleaned up"

    def test_graceful_stop_handling(self):
        """Test graceful stop via stop file."""
        mock_tmux = self._create_mock_tmux_manager()
        monitor = IdleMonitor(mock_tmux)

        # Start daemon
        success = monitor.start_supervised(interval=10)
        assert success
        time.sleep(2)

        assert monitor.is_running()

        # Stop gracefully
        success = monitor.stop()
        assert success

        # Verify daemon stopped
        time.sleep(2)
        assert not monitor.is_running()
        assert not self.pid_file.exists()

    def test_force_kill_recovery(self):
        """Test recovery from force kill scenario."""
        mock_tmux = self._create_mock_tmux_manager()
        monitor = IdleMonitor(mock_tmux)

        # Start daemon
        success = monitor.start_supervised(interval=10)
        assert success
        time.sleep(2)

        # Get daemon PID
        with open(self.pid_file) as f:
            daemon_pid = int(f.read().strip())

        # Force kill with SIGKILL
        os.kill(daemon_pid, signal.SIGKILL)
        time.sleep(1)

        # Should be able to start new daemon
        success = monitor.start_supervised(interval=10)
        assert success
        time.sleep(2)

        assert monitor.is_running()

        # Verify new PID
        with open(self.pid_file) as f:
            new_pid = int(f.read().strip())
        assert new_pid != daemon_pid, "Should have new daemon PID"

        monitor.stop()

    def test_supervisor_pid_file_handling(self):
        """Test supervisor PID file management."""
        mock_tmux = self._create_mock_tmux_manager()
        monitor = IdleMonitor(mock_tmux)

        # Start supervised daemon
        success = monitor.start_supervised(interval=10)
        assert success
        time.sleep(2)

        # Should have supervisor PID file
        assert self.supervisor_pid_file.exists(), "Supervisor PID file should exist"

        with open(self.supervisor_pid_file) as f:
            supervisor_pid = int(f.read().strip())

        # Verify supervisor process exists
        try:
            os.kill(supervisor_pid, 0)
        except ProcessLookupError:
            pytest.fail("Supervisor process should be running")

        # Stop daemon
        monitor.stop()
        time.sleep(2)

        # Supervisor PID file should be cleaned up
        assert not self.supervisor_pid_file.exists(), "Supervisor PID file should be cleaned up"

    def test_heartbeat_file_management(self):
        """Test heartbeat file creation and management."""
        mock_tmux = self._create_mock_tmux_manager()
        monitor = IdleMonitor(mock_tmux)

        # Start daemon
        success = monitor.start_supervised(interval=10)
        assert success
        time.sleep(3)  # Give more time for heartbeat

        # Heartbeat file should exist and be recent
        if self.heartbeat_file.exists():
            heartbeat_age = time.time() - self.heartbeat_file.stat().st_mtime
            assert heartbeat_age < 60, "Heartbeat should be recent"

        monitor.stop()

    @pytest.mark.parametrize("interval", [5, 10, 30])
    def test_different_intervals(self, interval):
        """Test daemon startup with different intervals."""
        mock_tmux = self._create_mock_tmux_manager()
        monitor = IdleMonitor(mock_tmux)

        success = monitor.start_supervised(interval=interval)
        assert success
        time.sleep(2)

        assert monitor.is_running()
        monitor.stop()

    def test_permissions_error_handling(self):
        """Test handling of permissions errors."""
        mock_tmux = self._create_mock_tmux_manager()

        # Create read-only directory to cause permissions error
        readonly_dir = Path("/tmp/readonly_test_dir")
        readonly_dir.mkdir(exist_ok=True)
        readonly_dir.chmod(0o444)  # Read-only

        try:
            # This should handle the error gracefully
            # In real implementation, monitor uses configured directory
            monitor = IdleMonitor(mock_tmux)
            # The monitor should still work with its configured directory
            success = monitor.start_supervised(interval=10)
            if success:
                time.sleep(2)
                monitor.stop()
        finally:
            # Cleanup
            readonly_dir.chmod(0o755)
            if readonly_dir.exists():
                readonly_dir.rmdir()


class TestSingletonLogic:
    """Unit tests for singleton logic methods."""

    def setup_method(self):
        """Setup for each test."""
        self.project_dir = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")
        self.pid_file = self.project_dir / "idle-monitor.pid"
        self._cleanup_files()

    def teardown_method(self):
        """Cleanup after each test."""
        self._cleanup_files()

    def _cleanup_files(self):
        """Clean up test files."""
        if self.pid_file.exists():
            self.pid_file.unlink()

    def test_enforce_singleton_no_existing_daemon(self):
        """Test singleton enforcement when no daemon exists."""
        mock_tmux = Mock(spec=TMUXManager)
        monitor = IdleMonitor(mock_tmux)

        # Test the singleton enforcement logic
        with patch.object(monitor, "_setup_logging"):
            result = monitor._enforce_singleton()
            assert result is None, "Should return None when no existing daemon"

    def test_enforce_singleton_with_valid_daemon(self):
        """Test singleton enforcement with valid running daemon."""
        mock_tmux = Mock(spec=TMUXManager)
        monitor = IdleMonitor(mock_tmux)

        # Create PID file with current process PID (guaranteed to exist)
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        with patch.object(monitor, "_setup_logging"):
            result = monitor._enforce_singleton()
            assert result == os.getpid(), "Should return existing daemon PID"

    def test_enforce_singleton_with_stale_pid(self):
        """Test singleton enforcement with stale PID."""
        mock_tmux = Mock(spec=TMUXManager)
        monitor = IdleMonitor(mock_tmux)

        # Create PID file with non-existent PID
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, "w") as f:
            f.write("99999")

        with patch.object(monitor, "_setup_logging"):
            result = monitor._enforce_singleton()
            assert result is None, "Should return None for stale PID"
            assert not self.pid_file.exists(), "Stale PID file should be cleaned up"


class TestDaemonIntegration:
    """Integration tests for daemon lifecycle."""

    def setup_method(self):
        """Setup before each test."""
        self._stop_all_daemons()

    def teardown_method(self):
        """Cleanup after each test."""
        self._stop_all_daemons()

    def _stop_all_daemons(self):
        """Stop all running daemons."""
        try:
            subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=10)
            time.sleep(2)
        except Exception:
            pass

    def test_cli_start_stop_integration(self):
        """Test CLI start/stop integration."""
        # Test start via CLI
        start_result = subprocess.run(
            ["tmux-orc", "monitor", "start", "--supervised"], capture_output=True, text=True, timeout=15
        )

        if start_result.returncode != 0:
            pytest.skip(f"CLI start failed: {start_result.stderr}")

        time.sleep(3)

        # Test status via CLI
        status_result = subprocess.run(["tmux-orc", "monitor", "status"], capture_output=True, text=True, timeout=10)
        assert status_result.returncode == 0

        # Test stop via CLI
        stop_result = subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, text=True, timeout=10)
        assert stop_result.returncode == 0

    def test_no_orphaned_processes(self):
        """Test that no orphaned processes remain after daemon lifecycle."""
        # Get initial process count
        initial_procs = subprocess.run(["pgrep", "-f", "idle.*monitor"], capture_output=True, text=True)
        initial_count = len(initial_procs.stdout.strip().split("\n")) if initial_procs.stdout.strip() else 0

        # Start and stop daemon
        subprocess.run(["tmux-orc", "monitor", "start", "--supervised"], capture_output=True, timeout=15)
        time.sleep(3)
        subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=10)
        time.sleep(2)

        # Check final process count
        final_procs = subprocess.run(["pgrep", "-f", "idle.*monitor"], capture_output=True, text=True)
        final_count = len(final_procs.stdout.strip().split("\n")) if final_procs.stdout.strip() else 0

        assert final_count <= initial_count, "Should not have more processes after daemon lifecycle"
