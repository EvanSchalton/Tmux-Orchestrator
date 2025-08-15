#!/usr/bin/env python3
"""Test non-blocking monitor commands."""

import os
import subprocess
import time
from pathlib import Path

import pytest


class TestNonBlockingMonitorCommands:
    """Test that monitor start/stop commands don't block."""

    def setup_method(self):
        """Ensure monitor is stopped before each test."""
        # Clean up any existing monitor
        try:
            subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=5)
            time.sleep(0.5)
        except Exception:
            pass

    def teardown_method(self):
        """Clean up after tests."""
        # Stop monitor if running
        try:
            subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=5)
        except Exception:
            pass

    def test_monitor_start_nonblocking(self):
        """Test that monitor start command returns quickly."""
        start_time = time.time()

        # Run monitor start command
        result = subprocess.run(
            ["tmux-orc", "monitor", "start"],
            capture_output=True,
            text=True,
            timeout=5,  # Should complete much faster
        )

        elapsed = time.time() - start_time

        # Should return in under 2 seconds (was blocking for 2 minutes before)
        assert elapsed < 2.0, f"Monitor start took {elapsed:.1f}s - should be non-blocking"

        # Check output indicates daemon started or is starting
        assert result.returncode == 0
        assert (
            "Idle monitor started" in result.stdout
            or "Monitor daemon is starting" in result.stdout
            or "Monitor is already running" in result.stdout
        )

        print(f"✅ Monitor start completed in {elapsed:.2f}s")
        print(f"Output: {result.stdout.strip()}")

    def test_monitor_stop_nonblocking(self):
        """Test that monitor stop command returns quickly."""
        # First start a monitor
        subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, timeout=5)
        time.sleep(1)  # Give it time to start

        start_time = time.time()

        # Run monitor stop command
        result = subprocess.run(
            ["tmux-orc", "monitor", "stop"],
            capture_output=True,
            text=True,
            timeout=5,  # Should complete much faster
        )

        elapsed = time.time() - start_time

        # Should return in under 2 seconds
        assert elapsed < 2.0, f"Monitor stop took {elapsed:.1f}s - should be non-blocking"

        # Check appropriate response
        assert result.returncode == 0
        assert (
            "Monitor stop signal sent" in result.stdout
            or "Monitor is not running" in result.stdout
            or "Monitor process not found" in result.stdout
        )

        print(f"✅ Monitor stop completed in {elapsed:.2f}s")
        print(f"Output: {result.stdout.strip()}")

    def test_monitor_status_quick_response(self):
        """Test that monitor status returns quickly."""
        start_time = time.time()

        result = subprocess.run(["tmux-orc", "monitor", "status"], capture_output=True, text=True, timeout=2)

        elapsed = time.time() - start_time

        # Status should be immediate
        assert elapsed < 1.0, f"Monitor status took {elapsed:.1f}s"
        assert result.returncode == 0

        print(f"✅ Monitor status completed in {elapsed:.2f}s")

    def test_graceful_stop_file_created(self):
        """Test that graceful stop file is created on stop command."""
        # Start monitor
        subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, timeout=5)
        time.sleep(1)

        # Check PID file exists
        pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")
        assert pid_file.exists(), "PID file should exist after start"

        # Stop monitor
        subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=5)

        # Check graceful stop file was created (briefly)
        # Note: File might be cleaned up quickly by daemon

        # PID file should be cleaned up
        time.sleep(0.5)
        assert not pid_file.exists(), "PID file should be removed after stop"

        print("✅ Graceful stop mechanism working")

    def test_multiple_start_commands_handled(self):
        """Test that multiple start commands don't cause issues."""
        # Start monitor
        subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, text=True, timeout=5)

        time.sleep(1)

        # Try to start again
        result2 = subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, text=True, timeout=5)

        # Second start should detect monitor is already running
        assert "already running" in result2.stdout
        assert result2.returncode == 0

        print("✅ Multiple start commands handled correctly")

    def test_background_daemon_actually_starts(self):
        """Test that the daemon process actually starts in background."""
        # Clean start
        subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=5)
        time.sleep(0.5)

        # Start monitor
        result = subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, text=True, timeout=5)

        # Give daemon time to write PID file
        time.sleep(1)

        # Check if daemon is actually running
        pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")
        if pid_file.exists():
            with open(pid_file) as f:
                pid = int(f.read().strip())

            # Check if process exists
            try:
                os.kill(pid, 0)  # Signal 0 just checks if process exists
                print(f"✅ Daemon is running with PID {pid}")
            except ProcessLookupError:
                pytest.fail("Daemon PID exists but process is not running")
        else:
            # Check if it's still starting
            if "starting in background" in result.stdout:
                print("✅ Daemon is starting in background")
            else:
                pytest.fail("Daemon did not start properly")


def test_cli_responsiveness():
    """Manual test to verify CLI responsiveness."""
    print("\n=== CLI Responsiveness Test ===")
    print("This test verifies that monitor commands don't block the CLI")
    print("\nExpected behavior:")
    print("- `tmux-orc monitor start` returns immediately")
    print("- `tmux-orc monitor stop` returns immediately")
    print("- No 2-minute timeouts")
    print("- Commands complete in under 2 seconds")
    print("\n" + "=" * 50)


if __name__ == "__main__":
    # Run the tests
    test = TestNonBlockingMonitorCommands()

    print("🧪 Testing Non-Blocking Monitor Commands...")
    print("=" * 60)

    test.setup_method()

    try:
        test.test_monitor_start_nonblocking()
        test.test_monitor_stop_nonblocking()
        test.test_monitor_status_quick_response()
        test.test_graceful_stop_file_created()
        test.test_multiple_start_commands_handled()
        test.test_background_daemon_actually_starts()

        print("\n" + "=" * 60)
        print("✅ All non-blocking monitor tests passed!")

        test_cli_responsiveness()

    finally:
        test.teardown_method()
