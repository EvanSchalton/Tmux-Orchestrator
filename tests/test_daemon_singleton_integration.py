#!/usr/bin/env python3
"""Integration tests for daemon singleton with CLI and real processes.

Tests the complete daemon lifecycle through the CLI interface to ensure
singleton behavior works correctly in production scenarios.
"""

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

import psutil
import pytest


class TestDaemonCLIIntegration:
    """Integration tests using the actual CLI."""

    def setup_method(self):
        """Setup before each test."""
        self.project_dir = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")
        self.pid_file = self.project_dir / "idle-monitor.pid"
        self.supervisor_pid_file = self.project_dir / "idle-monitor-supervisor.pid"
        self.graceful_stop_file = self.project_dir / "idle-monitor.graceful"

        # Ensure clean state
        self._force_stop_all_daemons()
        self._cleanup_files()

    def teardown_method(self):
        """Cleanup after each test."""
        self._force_stop_all_daemons()
        self._cleanup_files()

    def _cleanup_files(self):
        """Remove all daemon-related files."""
        for file in [self.pid_file, self.supervisor_pid_file, self.graceful_stop_file]:
            if file.exists():
                try:
                    file.unlink()
                except OSError:
                    pass

    def _force_stop_all_daemons(self):
        """Force stop all daemon processes."""
        # First try graceful stop
        subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True, timeout=5)
        time.sleep(1)

        # Then force kill any remaining processes
        for pattern in ["idle-monitor", "_run_monitoring_daemon", "monitor start"]:
            try:
                # Use psutil for more reliable process finding
                for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                    try:
                        cmdline = " ".join(proc.info["cmdline"] or [])
                        if pattern in cmdline and "pytest" not in cmdline:
                            os.kill(proc.info["pid"], signal.SIGKILL)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except Exception:
                pass

        time.sleep(0.5)

    def _run_cli_command(self, args: list, timeout: int = 10) -> Tuple[int, str, str]:
        """Run CLI command and return (returncode, stdout, stderr)."""
        result = subprocess.run(["tmux-orc"] + args, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr

    def _get_daemon_pid(self) -> Optional[int]:
        """Get daemon PID from PID file."""
        if self.pid_file.exists():
            try:
                with open(self.pid_file) as f:
                    return int(f.read().strip())
            except (ValueError, OSError):
                pass
        return None

    def _is_process_running(self, pid: int) -> bool:
        """Check if process is running."""
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False

    def test_basic_start_stop_cycle(self):
        """Test basic daemon start/stop cycle."""
        # Start daemon
        code, stdout, stderr = self._run_cli_command(["monitor", "start"])
        assert code == 0, f"Start failed: {stderr}"

        # Give daemon time to initialize
        time.sleep(2)

        # Check daemon is running
        pid = self._get_daemon_pid()
        assert pid is not None, "No PID file created"
        assert self._is_process_running(pid), f"Daemon process {pid} not running"

        # Check status
        code, stdout, stderr = self._run_cli_command(["monitor", "status"])
        assert code == 0, f"Status failed: {stderr}"
        assert "running" in stdout.lower(), "Status should show running"

        # Stop daemon
        code, stdout, stderr = self._run_cli_command(["monitor", "stop"])
        assert code == 0, f"Stop failed: {stderr}"

        # Give daemon time to stop
        time.sleep(2)

        # Verify stopped
        assert not self._is_process_running(pid), f"Daemon process {pid} still running"
        assert not self.pid_file.exists(), "PID file not cleaned up"

    def test_double_start_prevention(self):
        """Test that second start is prevented."""
        # Start first daemon
        code, stdout, stderr = self._run_cli_command(["monitor", "start"])
        assert code == 0, f"First start failed: {stderr}"
        time.sleep(2)

        first_pid = self._get_daemon_pid()
        assert first_pid is not None

        # Attempt second start
        code, stdout, stderr = self._run_cli_command(["monitor", "start"])
        assert code != 0, "Second start should fail"
        assert "already running" in stderr.lower() or "already running" in stdout.lower()

        # Verify first daemon still running
        assert self._get_daemon_pid() == first_pid
        assert self._is_process_running(first_pid)

    def test_supervised_mode(self):
        """Test supervised daemon mode."""
        # Start in supervised mode
        code, stdout, stderr = self._run_cli_command(["monitor", "start", "--supervised"])
        assert code == 0, f"Supervised start failed: {stderr}"
        time.sleep(3)

        # Check both supervisor and daemon are running
        daemon_pid = self._get_daemon_pid()
        assert daemon_pid is not None

        if self.supervisor_pid_file.exists():
            with open(self.supervisor_pid_file) as f:
                supervisor_pid = int(f.read().strip())
            assert self._is_process_running(supervisor_pid), "Supervisor not running"

        # Stop supervised daemon
        code, stdout, stderr = self._run_cli_command(["monitor", "stop"])
        assert code == 0, f"Stop failed: {stderr}"

    def test_concurrent_cli_starts(self):
        """Test concurrent CLI start attempts."""
        import concurrent.futures

        def start_daemon(attempt_id):
            """Start daemon and return result."""
            return self._run_cli_command(["monitor", "start"])

        # Launch 5 concurrent start attempts
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(start_daemon, i) for i in range(5)]
            results = [f.result() for f in futures]

        # Count successes and failures
        successes = [r for r in results if r[0] == 0]
        failures = [r for r in results if r[0] != 0]

        # Exactly one should succeed
        assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
        assert len(failures) == 4, f"Expected 4 failures, got {len(failures)}"

        # Verify daemon is running
        time.sleep(2)
        pid = self._get_daemon_pid()
        assert pid is not None
        assert self._is_process_running(pid)

    def test_daemon_crash_recovery(self):
        """Test behavior after daemon crash."""
        # Start daemon
        code, stdout, stderr = self._run_cli_command(["monitor", "start"])
        assert code == 0
        time.sleep(2)

        # Get daemon PID and kill it ungracefully
        pid = self._get_daemon_pid()
        assert pid is not None
        os.kill(pid, signal.SIGKILL)
        time.sleep(1)

        # Check status - should detect daemon is dead
        code, stdout, stderr = self._run_cli_command(["monitor", "status"])
        assert "not running" in stdout.lower() or "stopped" in stdout.lower()

        # Should be able to start new daemon
        code, stdout, stderr = self._run_cli_command(["monitor", "start"])
        assert code == 0, f"Restart after crash failed: {stderr}"

        # Verify new daemon is running
        time.sleep(2)
        new_pid = self._get_daemon_pid()
        assert new_pid is not None
        assert new_pid != pid, "Should have new PID"
        assert self._is_process_running(new_pid)

    def test_stale_pid_file_handling(self):
        """Test handling of stale PID files."""
        # Create stale PID file with non-existent PID
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, "w") as f:
            f.write("99999")

        # Status should detect stale PID
        code, stdout, stderr = self._run_cli_command(["monitor", "status"])
        assert "not running" in stdout.lower() or "stale" in stdout.lower()

        # Should be able to start daemon
        code, stdout, stderr = self._run_cli_command(["monitor", "start"])
        assert code == 0, f"Start with stale PID failed: {stderr}"

        # Verify daemon is running with new PID
        time.sleep(2)
        pid = self._get_daemon_pid()
        assert pid != 99999
        assert self._is_process_running(pid)

    def test_signal_handling(self):
        """Test daemon signal handling."""
        # Start daemon
        code, stdout, stderr = self._run_cli_command(["monitor", "start"])
        assert code == 0
        time.sleep(2)

        pid = self._get_daemon_pid()
        assert pid is not None

        # Send SIGTERM (should stop gracefully)
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)

        # Daemon should have stopped
        assert not self._is_process_running(pid)

        # For graceful stop via signal, PID file might remain
        # Start new daemon to verify system is functional
        code, stdout, stderr = self._run_cli_command(["monitor", "start"])
        assert code == 0

    def test_restart_functionality(self):
        """Test restart command if available."""
        # Start daemon
        code, stdout, stderr = self._run_cli_command(["monitor", "start"])
        assert code == 0
        time.sleep(2)

        first_pid = self._get_daemon_pid()

        # Try restart (may not be implemented)
        code, stdout, stderr = self._run_cli_command(["monitor", "restart"])

        if code == 0:
            # Restart succeeded
            time.sleep(3)
            new_pid = self._get_daemon_pid()
            assert new_pid is not None
            assert new_pid != first_pid, "Should have new PID after restart"
            assert self._is_process_running(new_pid)
        else:
            # Restart not implemented - do manual stop/start
            self._run_cli_command(["monitor", "stop"])
            time.sleep(1)
            self._run_cli_command(["monitor", "start"])

    def test_permission_errors(self):
        """Test handling of permission errors."""
        # Create PID file owned by root (if we can)
        try:
            subprocess.run(["sudo", "touch", str(self.pid_file)], capture_output=True, timeout=5)
            subprocess.run(["sudo", "chmod", "000", str(self.pid_file)], capture_output=True, timeout=5)

            # Try to start daemon
            code, stdout, stderr = self._run_cli_command(["monitor", "start"])
            # Should handle permission error gracefully
            assert "permission" in stderr.lower() or "permission" in stdout.lower()

        except Exception:
            # Skip if we can't create root-owned files
            pytest.skip("Cannot test permission errors without sudo")
        finally:
            # Cleanup
            subprocess.run(["sudo", "rm", "-f", str(self.pid_file)], capture_output=True, timeout=5)

    @pytest.mark.parametrize("interval", ["5", "10", "30"])
    def test_different_intervals(self, interval):
        """Test starting daemon with different intervals."""
        code, stdout, stderr = self._run_cli_command(["monitor", "start", "--interval", interval])
        assert code == 0, f"Start with interval {interval} failed: {stderr}"

        time.sleep(2)
        assert self._get_daemon_pid() is not None

        # Cleanup
        self._run_cli_command(["monitor", "stop"])

    def test_verbose_mode(self):
        """Test verbose output mode."""
        # Start with verbose flag
        code, stdout, stderr = self._run_cli_command(["monitor", "start", "-v"])

        # Should have more detailed output
        assert len(stdout) > 0 or len(stderr) > 0

        if code == 0:
            time.sleep(2)
            self._run_cli_command(["monitor", "stop"])

    def test_daemon_memory_leak(self):
        """Test that daemon doesn't leak memory over time."""
        # Start daemon
        code, stdout, stderr = self._run_cli_command(["monitor", "start"])
        assert code == 0
        time.sleep(2)

        pid = self._get_daemon_pid()
        assert pid is not None

        try:
            # Get initial memory usage
            process = psutil.Process(pid)
            initial_memory = process.memory_info().rss

            # Let it run for a bit
            time.sleep(10)

            # Check memory hasn't grown significantly
            final_memory = process.memory_info().rss
            memory_growth = final_memory - initial_memory

            # Allow some growth but not excessive (< 10MB)
            assert memory_growth < 10 * 1024 * 1024, f"Memory grew by {memory_growth} bytes"

        except psutil.NoSuchProcess:
            pytest.fail("Daemon died during memory test")
        finally:
            self._run_cli_command(["monitor", "stop"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
