#!/usr/bin/env python3
"""Test daemon respawn prevention after graceful stop.

Critical test scenarios:
1. Daemon stops and stays stopped after graceful shutdown
2. No zombie processes or orphaned daemons
3. Clean state after stop operations
4. Proper signal handling
"""

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest


class TestDaemonNoRespawn:
    """Test that daemon doesn't respawn after graceful stop."""

    def setup_method(self):
        """Ensure clean state."""
        self._force_cleanup()

    def teardown_method(self):
        """Clean up after tests."""
        self._force_cleanup()

    def _force_cleanup(self):
        """Force cleanup of any daemon processes and files."""
        try:
            # Try graceful stop first
            subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=10)
            time.sleep(1)

            # Force cleanup files
            files_to_clean = [
                Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid"),
                Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.graceful"),
            ]

            for file_path in files_to_clean:
                if file_path.exists():
                    file_path.unlink()

            # Find and kill any remaining monitor processes
            try:
                result = subprocess.run(["pgrep", "-f", "idle-monitor"], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split("\n")
                    for pid in pids:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            time.sleep(0.5)
                            os.kill(int(pid), signal.SIGKILL)
                        except (ProcessLookupError, ValueError):
                            pass
            except FileNotFoundError:
                # pgrep not available
                pass

        except Exception:
            pass

    def test_daemon_stays_stopped_after_graceful_stop(self):
        """Test daemon doesn't restart after being gracefully stopped."""
        pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")

        # Start daemon
        start_result = subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, text=True, timeout=10)
        assert start_result.returncode == 0, f"Failed to start daemon: {start_result.stderr}"

        # Wait for daemon to fully start
        time.sleep(3)
        assert pid_file.exists(), "PID file should exist after start"

        # Get the PID
        with open(pid_file) as f:
            daemon_pid = int(f.read().strip())

        # Verify daemon is running
        try:
            os.kill(daemon_pid, 0)
            print(f"✅ Daemon started with PID {daemon_pid}")
        except ProcessLookupError:
            pytest.fail(f"Daemon process {daemon_pid} should be running")

        # Gracefully stop daemon
        stop_result = subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, text=True, timeout=10)
        assert stop_result.returncode == 0, f"Failed to stop daemon: {stop_result.stderr}"

        # Wait for stop to complete
        time.sleep(2)

        # Verify daemon stopped
        assert not pid_file.exists(), "PID file should be removed after stop"

        try:
            os.kill(daemon_pid, 0)
            pytest.fail(f"Daemon process {daemon_pid} should be stopped")
        except ProcessLookupError:
            print(f"✅ Daemon process {daemon_pid} correctly stopped")

        # Wait longer to ensure no respawn
        print("⏳ Waiting 10 seconds to verify no respawn...")
        time.sleep(10)

        # Verify still stopped
        assert not pid_file.exists(), "Daemon should not respawn - PID file still absent"

        try:
            os.kill(daemon_pid, 0)
            pytest.fail(f"Daemon process {daemon_pid} should not have respawned")
        except ProcessLookupError:
            print("✅ Daemon correctly stayed stopped - no respawn detected")

    def test_graceful_stop_signal_handling(self):
        """Test that graceful stop properly handles signals."""
        # Start daemon
        subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, timeout=10)
        time.sleep(2)

        pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")
        assert pid_file.exists()

        with open(pid_file) as f:
            daemon_pid = int(f.read().strip())

        # Create graceful stop file manually to simulate stop command
        graceful_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.graceful")
        graceful_file.touch()

        # Send SIGTERM to daemon
        try:
            os.kill(daemon_pid, signal.SIGTERM)
            print(f"✅ Sent SIGTERM to daemon {daemon_pid}")
        except ProcessLookupError:
            pytest.fail("Daemon should be running to receive signal")

        # Wait for graceful shutdown
        time.sleep(3)

        # Verify daemon handled the signal and stopped
        try:
            os.kill(daemon_pid, 0)
            pytest.fail("Daemon should have stopped after SIGTERM")
        except ProcessLookupError:
            print("✅ Daemon gracefully handled SIGTERM")

        # PID file should be cleaned up
        assert not pid_file.exists(), "PID file should be removed"

        # Graceful file should be cleaned up
        assert not graceful_file.exists(), "Graceful stop file should be cleaned up"

    def test_no_zombie_processes_after_stop(self):
        """Test that stopping daemon doesn't leave zombie processes."""
        # Start daemon
        subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, timeout=10)
        time.sleep(2)

        pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")
        with open(pid_file) as f:
            daemon_pid = int(f.read().strip())

        # Stop daemon
        subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=10)
        time.sleep(2)

        # Check for zombie processes
        try:
            # Look for zombie processes related to our daemon
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                lines = result.stdout.split("\n")
                zombie_lines = [line for line in lines if "<defunct>" in line or "Z+" in line]
                daemon_zombies = [line for line in zombie_lines if str(daemon_pid) in line]

                assert len(daemon_zombies) == 0, f"Found zombie processes: {daemon_zombies}"
                print("✅ No zombie processes detected")
            else:
                print("⚠️ Could not check for zombie processes - ps command failed")

        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("⚠️ Could not check for zombie processes - ps not available")

    def test_multiple_stop_commands_safe(self):
        """Test that multiple stop commands don't cause issues."""
        # Start daemon
        subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, timeout=10)
        time.sleep(2)

        # First stop
        stop1 = subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, text=True, timeout=10)
        assert stop1.returncode == 0
        time.sleep(1)

        # Second stop (should handle gracefully)
        stop2 = subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, text=True, timeout=10)
        assert stop2.returncode == 0
        # Should indicate already stopped or similar
        print(f"Second stop result: {stop2.stdout.strip()}")

        # Third stop (should still handle gracefully)
        stop3 = subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, text=True, timeout=10)
        assert stop3.returncode == 0
        print("✅ Multiple stop commands handled safely")

    def test_daemon_cleanup_after_unexpected_termination(self):
        """Test cleanup when daemon terminates unexpectedly."""
        # Start daemon
        subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, timeout=10)
        time.sleep(2)

        pid_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid")
        assert pid_file.exists()

        with open(pid_file) as f:
            daemon_pid = int(f.read().strip())

        # Kill daemon with SIGKILL (simulates crash)
        try:
            os.kill(daemon_pid, signal.SIGKILL)
            print(f"✅ Forcefully killed daemon {daemon_pid}")
        except ProcessLookupError:
            pytest.fail("Daemon should be running")

        time.sleep(1)

        # Verify process is gone
        try:
            os.kill(daemon_pid, 0)
            pytest.fail("Daemon should be dead after SIGKILL")
        except ProcessLookupError:
            print("✅ Daemon process terminated")

        # Try to start new daemon - should work and clean up stale PID file
        start_result = subprocess.run(["tmux-orc", "monitor", "start"], capture_output=True, text=True, timeout=10)
        assert start_result.returncode == 0
        time.sleep(2)

        # Verify new daemon is running
        assert pid_file.exists(), "New PID file should exist"
        with open(pid_file) as f:
            new_pid = int(f.read().strip())

        assert new_pid != daemon_pid, "New daemon should have different PID"

        try:
            os.kill(new_pid, 0)
            print(f"✅ New daemon running with PID {new_pid}")
        except ProcessLookupError:
            pytest.fail("New daemon should be running")


def run_no_respawn_tests():
    """Run all no-respawn tests."""
    print("\n" + "=" * 60)
    print("🧪 DAEMON NO-RESPAWN TESTS")
    print("=" * 60)

    test = TestDaemonNoRespawn()

    tests = [
        ("Daemon stays stopped after graceful stop", test.test_daemon_stays_stopped_after_graceful_stop),
        ("Graceful stop signal handling", test.test_graceful_stop_signal_handling),
        ("No zombie processes after stop", test.test_no_zombie_processes_after_stop),
        ("Multiple stop commands safe", test.test_multiple_stop_commands_safe),
        ("Cleanup after unexpected termination", test.test_daemon_cleanup_after_unexpected_termination),
    ]

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}...")
        test.setup_method()
        try:
            test_func()
            print(f"✅ {test_name} passed")
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            raise
        finally:
            test.teardown_method()

    print("\n" + "=" * 60)
    print("🎉 ALL NO-RESPAWN TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_no_respawn_tests()
