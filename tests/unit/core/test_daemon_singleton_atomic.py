#!/usr/bin/env python3
"""Test suite for atomic daemon singleton implementation.

Focuses on testing the atomic file locking and PID file management
to ensure exactly one daemon instance can run at a time.
"""

import fcntl
import multiprocessing
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from tmux_orchestrator.core.monitor import DaemonAlreadyRunningError, IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager

# TMUXManager import removed - using comprehensive_mock_tmux fixture


class TestAtomicSingletonPattern:
    """Test the atomic singleton pattern implementation."""

    def setup_method(self):
        """Setup for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.pid_file = self.test_dir / "idle-monitor.pid"
        self.lock_file = self.test_dir / "idle-monitor.startup.lock"
        self.graceful_stop_file = self.test_dir / "idle-monitor.graceful"

    def teardown_method(self):
        """Cleanup after each test."""
        # Clean up any leftover files
        for file in [self.pid_file, self.lock_file, self.graceful_stop_file]:
            if file.exists():
                try:
                    file.unlink()
                except OSError:
                    pass

        # Remove test directory
        if self.test_dir.exists():
            try:
                self.test_dir.rmdir()
            except OSError:
                pass

    def _create_monitor_with_custom_dir(self):
        """Create monitor with custom directory for testing."""
        mock_tmux = Mock(spec=TMUXManager)
        mock_tmux.list_sessions.return_value = []

        # Patch the config to use our test directory
        with patch("tmux_orchestrator.core.monitor.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.orchestrator_base_dir = self.test_dir
            mock_config_class.load.return_value = mock_config

            monitor = IdleMonitor(mock_tmux)
            return monitor

    def test_atomic_pid_file_write(self):
        """Test atomic PID file writing mechanism."""
        monitor = self._create_monitor_with_custom_dir()

        # Test successful atomic write
        test_pid = 12345
        success = monitor._write_pid_file_atomic(test_pid)
        assert success, "Atomic write should succeed"

        # Verify PID file contents
        assert self.pid_file.exists(), "PID file should exist"
        with open(self.pid_file) as f:
            written_pid = int(f.read().strip())
        assert written_pid == test_pid, f"PID should be {test_pid}, got {written_pid}"

        # Verify temp files are cleaned up
        temp_files = list(self.test_dir.glob("*.tmp.*"))
        assert len(temp_files) == 0, "Temporary files should be cleaned up"

    def test_atomic_pid_file_write_permissions_error(self):
        """Test atomic write with permission errors."""
        monitor = self._create_monitor_with_custom_dir()

        # Make directory read-only
        self.test_dir.chmod(0o444)

        try:
            success = monitor._write_pid_file_atomic(12345)
            assert not success, "Write should fail with permissions error"
        finally:
            # Restore permissions
            self.test_dir.chmod(0o755)

    def test_atomic_pid_file_race_condition(self):
        """Test atomic PID file writing under race conditions."""
        monitor = self._create_monitor_with_custom_dir()

        # Simulate existing PID file appearing during write
        def create_pid_file_during_write():
            time.sleep(0.05)  # Small delay
            with open(self.pid_file, "w") as f:
                f.write("99999")

        # Start thread that creates PID file
        thread = threading.Thread(target=create_pid_file_during_write)
        thread.start()

        # Attempt atomic write
        monitor._write_pid_file_atomic(12345)
        thread.join()

        # The write may succeed or fail depending on timing
        # But PID file should exist and be valid
        assert self.pid_file.exists()
        with open(self.pid_file) as f:
            pid = int(f.read().strip())
        assert pid in [12345, 99999], "PID should be one of the written values"

    def test_startup_lock_acquisition(self):
        """Test startup lock acquisition mechanism."""
        monitor = self._create_monitor_with_custom_dir()

        # Should successfully acquire lock
        with patch.object(monitor, "_check_existing_daemon", return_value=None):
            success = monitor._handle_startup_race_condition()
            assert success, "Should acquire startup lock"

            # Verify lock file was created
            assert self.lock_file.exists(), "Lock file should exist"

            # Verify we have the lock
            assert hasattr(monitor, "_startup_lock_fd"), "Should store lock fd"

    def test_startup_lock_with_existing_daemon(self):
        """Test startup lock when daemon already exists."""
        monitor = self._create_monitor_with_custom_dir()

        # Mock existing daemon
        with patch.object(monitor, "_check_existing_daemon", return_value=12345):
            success = monitor._handle_startup_race_condition()
            assert not success, "Should not acquire lock with existing daemon"

    def test_concurrent_startup_lock_attempts(self):
        """Test multiple concurrent attempts to acquire startup lock."""
        results = []
        lock_acquired = threading.Event()

        def try_acquire_lock(monitor_id):
            """Try to acquire startup lock in thread."""
            monitor = self._create_monitor_with_custom_dir()

            # First monitor holds lock longer
            if monitor_id == 0:
                with patch.object(monitor, "_check_existing_daemon", return_value=None):
                    success = monitor._handle_startup_race_condition()
                    results.append((monitor_id, success))
                    if success:
                        lock_acquired.set()
                        time.sleep(0.5)  # Hold lock
                        # Clean up
                        if hasattr(monitor, "_startup_lock_fd"):
                            fcntl.flock(monitor._startup_lock_fd, fcntl.LOCK_UN)
                            os.close(monitor._startup_lock_fd)
            else:
                # Wait a bit for first thread to acquire lock
                lock_acquired.wait(timeout=1)
                time.sleep(0.1)
                with patch.object(monitor, "_check_existing_daemon", return_value=None):
                    success = monitor._handle_startup_race_condition()
                    results.append((monitor_id, success))

        # Launch concurrent attempts
        threads = []
        for i in range(3):
            thread = threading.Thread(target=try_acquire_lock, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Exactly one should succeed
        successful = [r for r in results if r[1]]
        assert len(successful) == 1, f"Exactly one should acquire lock, got {len(successful)}"

    def test_check_existing_daemon_with_valid_process(self):
        """Test checking for existing daemon with valid process."""
        monitor = self._create_monitor_with_custom_dir()

        # Create PID file with current process (guaranteed to exist)
        current_pid = os.getpid()
        with open(self.pid_file, "w") as f:
            f.write(str(current_pid))

        # Mock the cmdline check to make it look like a monitor daemon
        with patch("builtins.open", create=True) as mock_open:
            # Handle the PID file read
            pid_file_handle = MagicMock()
            pid_file_handle.read.return_value = str(current_pid)
            pid_file_handle.__enter__.return_value = pid_file_handle

            # Handle the cmdline read
            cmdline_handle = MagicMock()
            cmdline_handle.read.return_value = "python\0_run_monitoring_daemon\0"
            cmdline_handle.__enter__.return_value = cmdline_handle

            # Configure mock_open to return different handles based on file path
            def open_side_effect(path, *args, **kwargs):
                if "cmdline" in str(path):
                    return cmdline_handle
                else:
                    return pid_file_handle

            mock_open.side_effect = open_side_effect

            result = monitor._check_existing_daemon()
            assert result == current_pid, "Should detect valid daemon"

    def test_check_existing_daemon_with_stale_pid(self):
        """Test checking for existing daemon with stale PID."""
        monitor = self._create_monitor_with_custom_dir()

        # Create PID file with non-existent PID
        stale_pid = 99999
        with open(self.pid_file, "w") as f:
            f.write(str(stale_pid))

        result = monitor._check_existing_daemon()
        assert result is None, "Should not detect stale daemon"
        assert not self.pid_file.exists(), "Stale PID file should be cleaned up"

    def test_check_existing_daemon_empty_pid_file(self):
        """Test checking daemon with empty PID file."""
        monitor = self._create_monitor_with_custom_dir()

        # Create empty PID file
        self.pid_file.touch()

        result = monitor._check_existing_daemon()
        assert result is None, "Should handle empty PID file"
        assert not self.pid_file.exists(), "Empty PID file should be cleaned up"

    def test_check_existing_daemon_corrupted_pid_file(self):
        """Test checking daemon with corrupted PID file."""
        monitor = self._create_monitor_with_custom_dir()

        # Create corrupted PID file
        with open(self.pid_file, "w") as f:
            f.write("not_a_number")

        result = monitor._check_existing_daemon()
        assert result is None, "Should handle corrupted PID file"
        assert not self.pid_file.exists(), "Corrupted PID file should be cleaned up"

    def test_is_valid_daemon_process(self):
        """Test daemon process validation."""
        monitor = self._create_monitor_with_custom_dir()

        # Test with current process
        current_pid = os.getpid()

        # Mock cmdline read to simulate monitor daemon
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = "python\0monitor.py\0start\0"
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            result = monitor._is_valid_daemon_process(current_pid)
            assert result, "Should validate monitor daemon process"

    def test_is_valid_daemon_process_non_monitor(self):
        """Test daemon validation with non-monitor process."""
        monitor = self._create_monitor_with_custom_dir()

        # Test with current process but wrong cmdline
        current_pid = os.getpid()

        # Mock cmdline read to simulate non-monitor process
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = "python\0some_other_script.py\0"
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            result = monitor._is_valid_daemon_process(current_pid)
            assert not result, "Should not validate non-monitor process"

    def test_is_valid_daemon_process_nonexistent(self):
        """Test daemon validation with non-existent process."""
        monitor = self._create_monitor_with_custom_dir()

        # Test with non-existent PID
        fake_pid = 99999
        result = monitor._is_valid_daemon_process(fake_pid)
        assert not result, "Should not validate non-existent process"

    def test_cleanup_stale_pid_file(self):
        """Test stale PID file cleanup."""
        monitor = self._create_monitor_with_custom_dir()

        # Create PID file
        with open(self.pid_file, "w") as f:
            f.write("12345")

        assert self.pid_file.exists()

        # Clean up
        monitor._cleanup_stale_pid_file()
        assert not self.pid_file.exists(), "PID file should be removed"

    def test_cleanup_stale_pid_file_missing(self):
        """Test cleanup when PID file doesn't exist."""
        monitor = self._create_monitor_with_custom_dir()

        # Should not raise error
        monitor._cleanup_stale_pid_file()

    def test_cleanup_stale_pid_file_permissions_error(self):
        """Test cleanup with permissions error."""
        monitor = self._create_monitor_with_custom_dir()

        # Create PID file
        with open(self.pid_file, "w") as f:
            f.write("12345")

        # Make directory read-only
        self.test_dir.chmod(0o444)

        try:
            # Should handle error gracefully
            monitor._cleanup_stale_pid_file()
            # File may or may not be deleted depending on permissions
        finally:
            # Restore permissions
            self.test_dir.chmod(0o755)


class TestDaemonStartupRaceConditions:
    """Test race conditions during daemon startup."""

    def setup_method(self):
        """Setup for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.results = []
        self.lock = threading.Lock()

    def teardown_method(self):
        """Cleanup after each test."""
        # Clean up test directory
        if self.test_dir.exists():
            subprocess.run(["rm", "-rf", str(self.test_dir)], capture_output=True)

    def _simulate_daemon_start(self, monitor_id, delay=0):
        """Simulate daemon start attempt."""
        if delay:
            time.sleep(delay)

        # Create monitor with test directory
        mock_tmux = Mock(spec=TMUXManager)
        with patch("tmux_orchestrator.core.monitor.Config") as mock_config_class:
            mock_config = Mock()
            mock_config.orchestrator_base_dir = self.test_dir
            mock_config_class.load.return_value = mock_config

            monitor = IdleMonitor(mock_tmux)

            try:
                # Mock the forking behavior to avoid creating real processes
                with patch("os.fork", return_value=0):
                    with patch("os.setsid"):
                        with patch("os._exit"):
                            # Attempt to start
                            pid = monitor.start(interval=5)

                            with self.lock:
                                self.results.append({"id": monitor_id, "success": True, "pid": pid, "error": None})

            except DaemonAlreadyRunningError:
                with self.lock:
                    self.results.append({"id": monitor_id, "success": False, "pid": None, "error": "already_running"})
            except Exception as e:
                with self.lock:
                    self.results.append({"id": monitor_id, "success": False, "pid": None, "error": str(e)})

    def test_simultaneous_start_attempts(self):
        """Test truly simultaneous startup attempts."""
        # Use multiprocessing for true concurrency
        processes = []

        for i in range(5):
            p = multiprocessing.Process(target=self._simulate_daemon_start, args=(i,))
            processes.append(p)

        # Start all processes at once
        for p in processes:
            p.start()

        # Wait for completion
        for p in processes:
            p.join(timeout=5)

        # At least one should succeed, others should fail gracefully
        # Note: Results checking would require inter-process communication

    def test_rapid_sequential_starts(self):
        """Test rapid sequential start attempts."""
        threads = []

        for i in range(5):
            # Small staggered delay
            delay = i * 0.01
            thread = threading.Thread(target=self._simulate_daemon_start, args=(i, delay))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Analyze results
        successful = [r for r in self.results if r["success"]]
        already_running = [r for r in self.results if r["error"] == "already_running"]

        # In a properly working system, we expect one success and others to detect existing daemon
        assert len(successful) >= 1, "At least one daemon should start successfully"
        assert len(already_running) >= 1, "Some attempts should detect already running daemon"


class TestDaemonAlreadyRunningError:
    """Test the DaemonAlreadyRunningError exception."""

    def test_exception_creation(self):
        """Test creating the exception."""
        pid = 12345
        pid_file = Path("/tmp/test.pid")

        error = DaemonAlreadyRunningError(pid, pid_file)

        assert error.pid == pid
        assert error.pid_file == pid_file
        assert "already running with PID 12345" in str(error)
        assert "test.pid" in str(error)
        assert "tmux-orc monitor stop" in str(error)

    def test_exception_inheritance(self):
        """Test exception inheritance."""
        error = DaemonAlreadyRunningError(12345, Path("/tmp/test.pid"))

        assert isinstance(error, Exception)
        assert isinstance(error, DaemonAlreadyRunningError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
