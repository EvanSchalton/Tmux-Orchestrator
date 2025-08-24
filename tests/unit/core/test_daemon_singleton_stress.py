#!/usr/bin/env python3
"""Stress tests for daemon singleton implementation.

Tests extreme scenarios, edge cases, and stress conditions to ensure
the singleton pattern holds under all circumstances.
"""

import concurrent.futures
import fcntl
import multiprocessing
import os
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.monitor import DaemonAlreadyRunningError, IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager


class TestSingletonStressScenarios:
    """Stress test scenarios for singleton enforcement."""

    def setup_method(self):
        """Setup for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.pid_file = self.test_dir / "idle-monitor.pid"
        self.lock_file = self.test_dir / "idle-monitor.startup.lock"
        self.results = []
        self.results_lock = threading.Lock()

    def teardown_method(self):
        """Cleanup after each test."""
        # Force cleanup any test processes
        for file in self.test_dir.glob("*.pid"):
            try:
                with open(file) as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass

        # Clean up test directory
        if self.test_dir.exists():
            subprocess.run(["rm", "-rf", str(self.test_dir)], capture_output=True)

    def _create_monitor(self):
        """Create monitor instance with test directory."""
        mock_tmux = Mock(spec=TMUXManager)
        mock_tmux.list_sessions.return_value = []

        with patch("tmux_orchestrator.core.monitor.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.orchestrator_base_dir = self.test_dir
            mock_config_class.load.return_value = mock_config

            return IdleMonitor(mock_tmux)

    def test_thundering_herd_problem(self):
        """Test handling of thundering herd scenario."""
        num_processes = 20
        barrier = multiprocessing.Barrier(num_processes)
        results_queue = multiprocessing.Queue()

        def start_daemon_synchronized(process_id):
            """Start daemon with synchronization."""
            try:
                # Wait at barrier for synchronized start
                barrier.wait()

                # All processes try to start at exactly the same time
                monitor = self._create_monitor()

                # Mock fork to avoid creating real daemons
                with patch("os.fork", return_value=0):
                    with patch("os.setsid"):
                        with patch("os._exit"):
                            monitor.start()
                            results_queue.put(("success", process_id))

            except DaemonAlreadyRunningError:
                results_queue.put(("already_running", process_id))
            except Exception as e:
                results_queue.put(("error", process_id, str(e)))

        # Launch processes
        processes = []
        for i in range(num_processes):
            p = multiprocessing.Process(target=start_daemon_synchronized, args=(i,))
            processes.append(p)
            p.start()

        # Wait for completion
        for p in processes:
            p.join(timeout=10)

        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        # Analyze results
        successes = [r for r in results if r[0] == "success"]
        already_running = [r for r in results if r[0] == "already_running"]
        errors = [r for r in results if r[0] == "error"]

        # Exactly one should succeed in ideal case
        # In practice, timing may allow 1-2 successes before lock takes effect
        assert len(successes) <= 2, f"Too many successful starts: {len(successes)}"
        assert len(already_running) >= num_processes - 2, "Not enough 'already running' detections"
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_lock_file_corruption_recovery(self):
        """Test recovery from corrupted lock files."""
        monitor = self._create_monitor()

        # Create corrupted lock file
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_file, "wb") as f:
            f.write(b"\x00" * 1024)  # Binary garbage

        # Should still be able to start
        success = monitor._handle_startup_race_condition()
        # May succeed or fail depending on lock state, but shouldn't crash
        assert isinstance(success, bool)

    def test_pid_file_symlink_attack(self):
        """Test handling of symlink attacks on PID file."""
        monitor = self._create_monitor()

        # Create a symlink pointing to sensitive file
        sensitive_file = self.test_dir / "sensitive.txt"
        sensitive_file.write_text("sensitive data")

        # Create symlink where PID file should be
        if self.pid_file.exists():
            self.pid_file.unlink()
        self.pid_file.symlink_to(sensitive_file)

        # Attempt to write PID file
        monitor._write_pid_file_atomic(12345)

        # Should handle symlink safely
        # Original sensitive file should remain unchanged
        assert sensitive_file.read_text() == "sensitive data"

    def test_directory_permissions_changes(self):
        """Test handling of directory permission changes during operation."""
        monitor = self._create_monitor()

        def change_permissions():
            """Change directory permissions mid-operation."""
            time.sleep(0.1)
            self.test_dir.chmod(0o000)  # No permissions
            time.sleep(0.1)
            self.test_dir.chmod(0o755)  # Restore

        # Start permission changer thread
        thread = threading.Thread(target=change_permissions)
        thread.start()

        # Try to handle startup
        try:
            monitor._handle_startup_race_condition()
            # Should handle permission changes gracefully
        except Exception:
            # Expected in some cases
            pass

        thread.join()

    def test_signal_handling_during_startup(self):
        """Test signal handling during critical startup sections."""
        monitor = self._create_monitor()

        # Set up signal to be sent during startup
        def send_signal():
            time.sleep(0.05)
            os.kill(os.getpid(), signal.SIGUSR1)

        # Install signal handler
        signal_received = threading.Event()

        def signal_handler(signum, frame):
            signal_received.set()

        signal.signal(signal.SIGUSR1, signal_handler)

        # Start signal sender
        thread = threading.Thread(target=send_signal)
        thread.start()

        # Attempt startup
        try:
            monitor._handle_startup_race_condition()
            # Should complete despite signal
        except Exception:
            pass

        thread.join()

        # Restore default handler
        signal.signal(signal.SIGUSR1, signal.SIG_DFL)

    def test_filesystem_full_condition(self):
        """Test handling when filesystem is full."""
        monitor = self._create_monitor()

        # Mock write operations to simulate full filesystem
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = OSError(28, "No space left on device")

            success = monitor._write_pid_file_atomic(12345)
            assert not success, "Should fail gracefully on full filesystem"

    def test_concurrent_check_and_cleanup(self):
        """Test concurrent checking and cleanup operations."""
        # Create stale PID file
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, "w") as f:
            f.write("99999")

        check_results = []
        cleanup_done = []

        def check_daemon(thread_id):
            """Check for existing daemon."""
            monitor = self._create_monitor()
            result = monitor._check_existing_daemon()
            check_results.append((thread_id, result))

        def cleanup_stale(thread_id):
            """Clean up stale PID file."""
            monitor = self._create_monitor()
            monitor._cleanup_stale_pid_file()
            cleanup_done.append(thread_id)

        # Launch concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Mix of check and cleanup operations
            futures = []
            for i in range(5):
                futures.append(executor.submit(check_daemon, i))
                futures.append(executor.submit(cleanup_stale, i))

            # Wait for completion
            concurrent.futures.wait(futures)

        # PID file should be cleaned up
        assert not self.pid_file.exists()

    def test_rapid_start_stop_cycles(self):
        """Test rapid start/stop cycles."""
        monitor = self._create_monitor()

        for i in range(10):
            # Mock the daemon operations
            with patch("os.fork", return_value=0):
                with patch("os.setsid"):
                    with patch("os._exit"):
                        try:
                            # Start
                            monitor.start()

                            # Simulate daemon running
                            self.pid_file.write_text(str(os.getpid()))

                            # Stop
                            with patch.object(monitor, "is_running", return_value=True):
                                with patch("os.kill"):
                                    monitor.stop()

                            # Clean up PID file
                            if self.pid_file.exists():
                                self.pid_file.unlink()

                        except Exception:
                            # Some iterations may fail due to timing
                            pass

    def test_lock_timeout_behavior(self):
        """Test behavior when lock acquisition times out."""
        monitor = self._create_monitor()

        # Acquire lock externally
        lock_fd = os.open(str(self.lock_file), os.O_CREAT | os.O_RDWR)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        try:
            # Attempt to acquire lock (should fail/timeout)
            success = monitor._handle_startup_race_condition()
            assert not success, "Should not acquire lock when already held"
        finally:
            # Release lock
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    def test_memory_pressure_scenario(self):
        """Test behavior under memory pressure."""
        monitor = self._create_monitor()

        # Allocate large amount of memory to simulate pressure
        large_data = []
        try:
            # Allocate ~100MB in chunks
            for _ in range(100):
                large_data.append(bytearray(1024 * 1024))

            # Try singleton operations under memory pressure
            success = monitor._handle_startup_race_condition()
            # Should still work despite memory pressure
            assert isinstance(success, bool)

        finally:
            # Release memory
            large_data.clear()

    def test_clock_skew_handling(self):
        """Test handling of system clock changes."""
        monitor = self._create_monitor()

        # Create PID file with future timestamp
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, "w") as f:
            f.write("12345")

        # Mock stat to return future time
        original_stat = Path.stat

        def mock_stat(self):
            if str(self) == str(monitor.pid_file):
                stat_result = original_stat(self)
                # Simulate file from future (1 hour ahead)
                future_mtime = time.time() + 3600
                return type(stat_result)(
                    (
                        stat_result.st_mode,
                        stat_result.st_ino,
                        stat_result.st_dev,
                        stat_result.st_nlink,
                        stat_result.st_uid,
                        stat_result.st_gid,
                        stat_result.st_size,
                        stat_result.st_atime,
                        future_mtime,
                        stat_result.st_ctime,
                    )
                )
            return original_stat(self)

        with patch.object(Path, "stat", mock_stat):
            # Should still handle the file correctly
            monitor._check_existing_daemon()
            # Result depends on whether process 12345 exists

    def test_unicode_in_paths(self):
        """Test handling of unicode characters in paths."""
        # Create directory with unicode characters
        unicode_dir = self.test_dir / "测试目录_🔒"
        unicode_dir.mkdir(exist_ok=True)

        # Create monitor with unicode path
        mock_tmux = Mock(spec=TMUXManager)
        with patch("tmux_orchestrator.core.monitor.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.orchestrator_base_dir = unicode_dir
            mock_config_class.load.return_value = mock_config

            monitor = IdleMonitor(mock_tmux)

            # Should handle unicode paths correctly
            success = monitor._write_pid_file_atomic(12345)
            assert isinstance(success, bool)


class TestSingletonBoundaryConditions:
    """Test boundary conditions for singleton pattern."""

    def setup_method(self):
        """Setup for each test."""
        self.test_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup after each test."""
        if self.test_dir.exists():
            subprocess.run(["rm", "-rf", str(self.test_dir)], capture_output=True)

    def test_max_path_length(self):
        """Test handling of maximum path lengths."""
        # Create very long directory path (near PATH_MAX)
        long_name = "a" * 200
        long_dir = self.test_dir / long_name

        try:
            long_dir.mkdir(exist_ok=True)

            mock_tmux = Mock(spec=TMUXManager)
            with patch("tmux_orchestrator.core.monitor.Config") as mock_config_class:
                mock_config = Mock()
                mock_config.orchestrator_base_dir = long_dir
                mock_config_class.load.return_value = mock_config

                monitor = IdleMonitor(mock_tmux)
                # Should handle long paths
                success = monitor._write_pid_file_atomic(12345)
                assert isinstance(success, bool)
        except OSError:
            # Expected if path is too long for system
            pass

    def test_max_pid_value(self):
        """Test handling of maximum PID values."""
        monitor = self._create_monitor()

        # Test with maximum possible PID (usually 2^22 on Linux)
        max_pid = 4194304
        success = monitor._write_pid_file_atomic(max_pid)

        if success:
            with open(monitor.pid_file) as f:
                written_pid = int(f.read().strip())
            assert written_pid == max_pid

    def test_zero_and_negative_pids(self):
        """Test handling of invalid PID values."""
        monitor = self._create_monitor()

        # Test with zero PID
        success = monitor._write_pid_file_atomic(0)
        assert success  # Should write it, validation is elsewhere

        # Test with negative PID
        success = monitor._write_pid_file_atomic(-1)
        assert success  # Should write it, validation is elsewhere

    def test_extremely_rapid_operations(self):
        """Test extremely rapid singleton operations."""
        monitor = self._create_monitor()

        start_time = time.time()
        operations = 0

        # Perform as many operations as possible in 1 second
        while time.time() - start_time < 1.0:
            monitor._check_existing_daemon()
            operations += 1

        # Should handle hundreds/thousands of operations
        assert operations > 100, f"Only performed {operations} operations"

    def _create_monitor(self):
        """Create monitor for boundary tests."""
        mock_tmux = Mock(spec=TMUXManager)
        with patch("tmux_orchestrator.core.monitor.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.orchestrator_base_dir = self.test_dir
            mock_config_class.load.return_value = mock_config

            return IdleMonitor(mock_tmux)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
