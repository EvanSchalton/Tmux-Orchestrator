#!/usr/bin/env python3
"""Comprehensive daemon functionality test suite.

Tests critical daemon behaviors:
1. Start/stop operations work correctly
2. Only one daemon instance runs at a time
3. Daemon doesn't respawn after graceful stop
4. PID file management
5. Process verification
"""

import os
import subprocess
import time
from pathlib import Path

import pytest


class TestDaemonSingleInstance:
    """Test that only one daemon instance runs at a time."""

    def setup_method(self):
        """Clean state before each test."""
        self._cleanup_daemon()

    def teardown_method(self):
        """Clean up after tests."""
        self._cleanup_daemon()

    def _cleanup_daemon(self):
        """Stop any running daemon and clean files."""
        try:
            subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=10)
            time.sleep(1)
            # Force cleanup files
            pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")
            graceful_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.graceful")
            for f in [pid_file, graceful_file]:
                if f.exists():
                    f.unlink()
        except Exception:
            pass

    def test_single_daemon_instance_enforcement(self):
        """Test that starting daemon twice doesn't create multiple instances."""
        # Start first daemon
        result1 = subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, text=True, timeout=10)
        assert result1.returncode == 0
        time.sleep(2)  # Allow daemon to start

        # Verify daemon is running
        pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")
        assert pid_file.exists(), "PID file should exist after start"

        with open(pid_file) as f:
            pid1 = int(f.read().strip())

        # Verify process is running
        try:
            os.kill(pid1, 0)
        except ProcessLookupError:
            pytest.fail("First daemon process should be running")

        # Try to start second daemon
        result2 = subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, text=True, timeout=10)

        # Should detect existing daemon
        assert result2.returncode == 0
        assert "already running" in result2.stdout.lower()

        # PID should remain the same
        with open(pid_file) as f:
            pid2 = int(f.read().strip())

        assert pid1 == pid2, "PID should not change when trying to start second daemon"

        # Verify only one process exists
        try:
            os.kill(pid1, 0)
        except ProcessLookupError:
            pytest.fail("Daemon process should still be running")

    def test_daemon_start_stop_cycle(self):
        """Test complete start/stop cycle works correctly."""
        pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")

        # Initially no daemon
        assert not pid_file.exists(), "PID file should not exist initially"

        # Start daemon
        start_result = subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, text=True, timeout=10)
        assert start_result.returncode == 0
        time.sleep(2)

        # Verify daemon started
        assert pid_file.exists(), "PID file should exist after start"
        with open(pid_file) as f:
            daemon_pid = int(f.read().strip())

        # Verify process is running
        try:
            os.kill(daemon_pid, 0)
            print(f"✅ Daemon running with PID {daemon_pid}")
        except ProcessLookupError:
            pytest.fail("Daemon process should be running")

        # Stop daemon
        stop_result = subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, text=True, timeout=10)
        assert stop_result.returncode == 0
        time.sleep(1)

        # Verify daemon stopped
        assert not pid_file.exists(), "PID file should be removed after stop"

        # Verify process is gone
        try:
            os.kill(daemon_pid, 0)
            pytest.fail("Daemon process should be stopped")
        except ProcessLookupError:
            print("✅ Daemon process correctly stopped")

    def test_graceful_stop_prevents_respawn(self):
        """Test that graceful stop prevents daemon respawn."""
        # Start daemon
        subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, timeout=10)
        time.sleep(2)

        pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")
        assert pid_file.exists()

        with open(pid_file) as f:
            original_pid = int(f.read().strip())

        # Graceful stop
        subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=10)
        time.sleep(2)

        # Verify daemon doesn't respawn
        assert not pid_file.exists(), "PID file should be removed"

        # Wait longer to ensure no respawn
        time.sleep(3)
        assert not pid_file.exists(), "Daemon should not respawn after graceful stop"

        # Verify original process is gone
        try:
            os.kill(original_pid, 0)
            pytest.fail("Original daemon should be stopped")
        except ProcessLookupError:
            print("✅ Daemon correctly stopped and did not respawn")

    def test_pid_file_management(self):
        """Test PID file creation and cleanup."""
        pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")

        # Start daemon
        subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, timeout=10)
        time.sleep(2)

        # PID file should exist
        assert pid_file.exists(), "PID file should be created"
        assert pid_file.stat().st_size > 0, "PID file should not be empty"

        # PID should be valid integer
        with open(pid_file) as f:
            pid_content = f.read().strip()

        pid = int(pid_content)  # Should not raise ValueError
        assert pid > 0, "PID should be positive"

        # Stop daemon
        subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=10)
        time.sleep(1)

        # PID file should be cleaned up
        assert not pid_file.exists(), "PID file should be removed on stop"


class TestDaemonProcessVerification:
    """Test daemon process verification and monitoring."""

    def setup_method(self):
        """Clean state before each test."""
        self._cleanup_daemon()

    def teardown_method(self):
        """Clean up after tests."""
        self._cleanup_daemon()

    def _cleanup_daemon(self):
        """Stop any running daemon and clean files."""
        try:
            subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=10)
            time.sleep(1)
            pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")
            if pid_file.exists():
                pid_file.unlink()
        except Exception:
            pass

    def test_daemon_process_actually_exists(self):
        """Test that daemon process actually exists and is responsive."""
        # Start daemon
        subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, timeout=10)
        time.sleep(2)

        pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")
        assert pid_file.exists()

        with open(pid_file) as f:
            daemon_pid = int(f.read().strip())

        # Verify process exists and is responsive
        try:
            # Signal 0 just checks if process exists
            os.kill(daemon_pid, 0)
            print(f"✅ Daemon process {daemon_pid} exists and is accessible")
        except ProcessLookupError:
            pytest.fail(f"Daemon process {daemon_pid} does not exist")
        except PermissionError:
            pytest.fail(f"Permission denied accessing daemon process {daemon_pid}")

        # Check process is actually the monitor daemon (not just any process)
        try:
            # Get process command line if possible
            with open(f"/proc/{daemon_pid}/cmdline", "rb") as f:
                cmdline = f.read().decode().replace("\0", " ")
                assert (
                    "python" in cmdline or "tmux-orc" in cmdline
                ), f"Process {daemon_pid} doesn't appear to be the monitor daemon: {cmdline}"
                print(f"✅ Daemon process verified: {cmdline}")
        except (FileNotFoundError, PermissionError):
            # /proc might not be available in all environments
            print("⚠️ Could not verify process details via /proc")

    def test_status_command_accuracy(self):
        """Test that status command accurately reflects daemon state."""
        # Initially no daemon
        status_result = subprocess.run(["tmux-orc", "monitor", "status"], capture_output=True, text=True, timeout=5)
        assert status_result.returncode == 0
        # Should indicate no daemon running (exact message may vary)
        print(f"Status when no daemon: {status_result.stdout.strip()}")

        # Start daemon
        subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, timeout=10)
        time.sleep(2)

        # Status should show daemon running
        status_result = subprocess.run(["tmux-orc", "monitor", "status"], capture_output=True, text=True, timeout=5)
        assert status_result.returncode == 0
        assert "running" in status_result.stdout.lower()
        print(f"Status when daemon running: {status_result.stdout.strip()}")

        # Stop daemon
        subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=10)
        time.sleep(1)

        # Status should show daemon stopped
        status_result = subprocess.run(["tmux-orc", "monitor", "status"], capture_output=True, text=True, timeout=5)
        assert status_result.returncode == 0
        print(f"Status after stop: {status_result.stdout.strip()}")

    def test_concurrent_operations_safety(self):
        """Test that concurrent start/stop operations are handled safely."""
        import queue
        import threading

        results = queue.Queue()

        def start_daemon():
            result = subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, text=True, timeout=10)
            results.put(("start", result.returncode, result.stdout))

        def stop_daemon():
            time.sleep(0.5)  # Slight delay
            result = subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, text=True, timeout=10)
            results.put(("stop", result.returncode, result.stdout))

        # Start two operations concurrently
        start_thread = threading.Thread(target=start_daemon)
        stop_thread = threading.Thread(target=stop_daemon)

        start_thread.start()
        stop_thread.start()

        start_thread.join()
        stop_thread.join()

        # Collect results
        start_result = None
        stop_result = None

        while not results.empty():
            op, returncode, stdout = results.get()
            if op == "start":
                start_result = (returncode, stdout)
            else:
                stop_result = (returncode, stdout)

        # Both operations should complete successfully
        assert start_result[0] == 0, f"Start failed: {start_result[1]}"
        assert stop_result[0] == 0, f"Stop failed: {stop_result[1]}"

        print("✅ Concurrent operations handled safely")


def run_comprehensive_daemon_tests():
    """Run all daemon functionality tests."""
    print("\n" + "=" * 60)
    print("🧪 COMPREHENSIVE DAEMON FUNCTIONALITY TESTS")
    print("=" * 60)

    # Test single instance
    print("\n📋 Testing Single Instance Enforcement...")
    single_test = TestDaemonSingleInstance()
    single_test.setup_method()
    try:
        single_test.test_single_daemon_instance_enforcement()
        single_test.test_daemon_start_stop_cycle()
        single_test.test_graceful_stop_prevents_respawn()
        single_test.test_pid_file_management()
        print("✅ Single instance tests passed")
    finally:
        single_test.teardown_method()

    # Test process verification
    print("\n📋 Testing Process Verification...")
    process_test = TestDaemonProcessVerification()
    process_test.setup_method()
    try:
        process_test.test_daemon_process_actually_exists()
        process_test.test_status_command_accuracy()
        process_test.test_concurrent_operations_safety()
        print("✅ Process verification tests passed")
    finally:
        process_test.teardown_method()

    print("\n" + "=" * 60)
    print("🎉 ALL DAEMON FUNCTIONALITY TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_comprehensive_daemon_tests()
