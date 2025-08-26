#!/usr/bin/env python3
"""
Comprehensive test suite for PM crash detection and recovery.
Tests daemon's ability to detect and recover crashed PMs.
"""

import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager

# TMUXManager import removed - using comprehensive_mock_tmux fixture


class TestPMCrashDetection:
    """Test PM crash detection scenarios."""

    def setup_method(self):
        """Setup test environment."""
        # self.tmux = comprehensive_mock_tmux  # Removed - use comprehensive_mock_tmux fixture
        self.test_session = f"test-pm-{os.getpid()}"
        self.daemon_logs = []

    def teardown_method(self):
        """Cleanup test environment."""
        # Kill test session
        subprocess.run(["tmux", "kill-session", "-t", self.test_session], capture_output=True)

    def spawn_test_pm(self, session_name=None):
        """Spawn a test PM and return target."""
        session = session_name or self.test_session

        # Create session if needed
        if not self.tmux.has_session(session):
            self.tmux.create_session(session)

        # Spawn PM
        result = subprocess.run(["tmux-orc", "spawn", "pm", "--session", session], capture_output=True, text=True)

        if result.returncode == 0:
            # Extract target from output
            for line in result.stdout.split("\n"):
                if "Successfully spawned" in line:
                    # Parse target
                    return f"{session}:1"  # Assuming PM is in window 1

        raise RuntimeError(f"Failed to spawn PM: {result.stderr}")

    def get_pm_pid(self, target):
        """Get PID of PM process in target window."""
        # Get pane PID
        result = subprocess.run(
            ["tmux", "list-panes", "-t", target, "-F", "#{pane_pid}"], capture_output=True, text=True
        )

        if result.returncode == 0:
            pane_pid = int(result.stdout.strip())
            # Find claude process under this pane
            try:
                import psutil

                parent = psutil.Process(pane_pid)
                for child in parent.children(recursive=True):
                    if "claude" in child.cmdline():
                        return child.pid
            except Exception:
                pass

        return None

    def wait_for_condition(self, condition_func, timeout=30, interval=1):
        """Wait for condition to be true."""
        start = time.time()
        while time.time() - start < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        return False

    def daemon_detected_crash(self, pm_target):
        """Check if daemon detected PM crash."""
        # Check daemon logs for crash detection
        log_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/logs/idle-monitor.log")
        if log_file.exists():
            with open(log_file) as f:
                content = f.read()
                return (
                    f"PM crash detected in {pm_target}" in content
                    or f"PM not responding in {pm_target}" in content
                    or f"Missing PM in {pm_target}" in content
                )
        return False

    @pytest.mark.integration
    def test_pm_process_kill_detection(self):
        """Test detection when PM process is killed."""
        # Spawn PM
        pm_target = self.spawn_test_pm()
        time.sleep(5)  # Let PM initialize

        # Get PM PID
        pm_pid = self.get_pm_pid(pm_target)
        assert pm_pid is not None, "Could not find PM process"

        # Start monitoring
        with patch("tmux_orchestrator.core.monitor.IdleMonitor._run_monitoring_daemon"):
            monitor = IdleMonitor(self.tmux)
            monitor_thread = threading.Thread(
                target=monitor._monitoring_loop,
                args=(10,),  # 10 second interval
            )
            monitor_thread.daemon = True
            monitor_thread.start()

            # Kill PM process
            os.kill(pm_pid, signal.SIGKILL)

            # Wait for detection
            detected = self.wait_for_condition(lambda: self.daemon_detected_crash(pm_target), timeout=30)

            assert detected, "Daemon did not detect PM crash within timeout"

    @pytest.mark.integration
    def test_pm_window_closure_detection(self):
        """Test detection when PM window is closed."""
        # Spawn PM
        pm_target = self.spawn_test_pm()
        time.sleep(5)

        # Close PM window
        subprocess.run(["tmux", "kill-window", "-t", pm_target], check=True)

        # Start monitoring and check detection
        with patch("tmux_orchestrator.core.monitor.IdleMonitor._run_monitoring_daemon"):
            monitor = IdleMonitor(self.tmux)

            # Directly test detection logic
            agents = monitor._get_active_agents()
            pm_agents = [a for a in agents if a.get("type") == "pm"]

            # Should not find PM since window was killed
            assert len(pm_agents) == 0, "PM still detected after window closure"

    @pytest.mark.integration
    def test_pm_unresponsive_detection(self):
        """Test detection when PM becomes unresponsive."""
        # Spawn PM
        pm_target = self.spawn_test_pm()
        time.sleep(5)

        # Get PM PID and freeze it
        pm_pid = self.get_pm_pid(pm_target)
        assert pm_pid is not None

        # Send SIGSTOP to freeze PM
        os.kill(pm_pid, signal.SIGSTOP)

        try:
            # Test idle detection logic
            with patch("tmux_orchestrator.core.monitor.IdleMonitor._run_monitoring_daemon"):
                monitor = IdleMonitor(self.tmux)

                # Simulate monitoring iterations
                for _ in range(3):
                    pane_content = monitor.tmux.capture_pane(pm_target)
                    is_idle = monitor._is_agent_idle(pm_target, pane_content)

                    # After freezing, content should not change
                    time.sleep(2)

                assert is_idle, "Frozen PM not detected as idle"

        finally:
            # Unfreeze PM
            os.kill(pm_pid, signal.SIGCONT)

    def test_pm_claude_interface_lost(self):
        """Test detection when Claude interface is lost."""
        # Mock scenario where Claude UI disappears
        mock_tmux = Mock(spec=TMUXManager)
        mock_tmux.capture_pane.return_value = "bash-5.1$ "  # Just shell prompt

        monitor = IdleMonitor(mock_tmux)

        # Test interface detection
        with patch("tmux_orchestrator.core.monitor_helpers.is_claude_interface_present") as mock_check:
            mock_check.return_value = False

            # Should detect missing interface
            pane_content = "bash-5.1$ "
            has_interface = monitor._check_claude_interface("test:0", pane_content)

            assert not has_interface, "Failed to detect missing Claude interface"


class TestPMRecoveryEdgeCases:
    """Test edge cases where PM recovery might fail."""

    def test_pm_crash_loop_prevention(self):
        """Test prevention of PM crash loops."""
        monitor = IdleMonitor(Mock())

        # Simulate rapid PM crashes
        pm_target = "test:1"

        # Track recovery attempts
        with patch.object(monitor, "_recover_crashed_pm") as mock_recover:
            # Simulate 5 rapid crashes
            for i in range(5):
                monitor._handle_pm_crash(pm_target)
                time.sleep(0.1)  # Rapid crashes

            # Should implement backoff
            assert mock_recover.call_count < 5, "No backoff implemented for crash loop"

    def test_pm_recovery_permission_denied(self):
        """Test recovery when permissions are denied."""
        mock_tmux = Mock(spec=TMUXManager)
        mock_tmux.create_window.side_effect = PermissionError("Access denied")

        monitor = IdleMonitor(mock_tmux)

        # Attempt recovery
        with patch.object(monitor, "_log_error") as mock_log:
            success = monitor._spawn_replacement_pm("test:1")

            assert not success, "Recovery should fail with permission error"
            mock_log.assert_called_with("PM recovery failed: Permission denied")

    def test_pm_recovery_resource_exhaustion(self):
        """Test recovery under resource exhaustion."""
        mock_tmux = Mock(spec=TMUXManager)
        mock_tmux.create_window.side_effect = OSError("Cannot allocate memory")

        monitor = IdleMonitor(mock_tmux)

        # Test recovery with retries
        with patch("time.sleep"):  # Speed up test
            success = monitor._spawn_replacement_pm("test:1", max_retries=3)

            assert not success, "Recovery should fail under resource exhaustion"
            assert mock_tmux.create_window.call_count == 3, "Should retry on resource errors"

    def test_concurrent_pm_recovery_prevention(self):
        """Test prevention of concurrent PM recovery attempts."""
        monitor = IdleMonitor(Mock())

        # Track active recoveries
        monitor._active_recoveries = set()

        pm_target = "test:1"

        def mock_recovery():
            # Check if already recovering
            if pm_target in monitor._active_recoveries:
                return False

            monitor._active_recoveries.add(pm_target)
            time.sleep(1)  # Simulate recovery time
            monitor._active_recoveries.remove(pm_target)
            return True

        # Simulate concurrent recovery attempts
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(mock_recovery) for _ in range(3)]
            results = [f.result() for f in futures]

        # Only one should succeed
        successful = sum(1 for r in results if r)
        assert successful == 1, f"Multiple concurrent recoveries: {successful}"

    def test_pm_recovery_during_daemon_restart(self):
        """Test PM recovery robustness during daemon restart."""
        # This tests the supervisor's ability to handle daemon restarts

        # Create recovery state file
        state_file = Path("/tmp/pm_recovery_state.json")
        state = {"recovering": {"test:1": {"started": time.time(), "attempts": 1}}}

        import json

        with open(state_file, "w") as f:
            json.dump(state, f)

        try:
            # New daemon should check for incomplete recoveries
            monitor = IdleMonitor(Mock())

            with patch.object(monitor, "_resume_incomplete_recoveries") as mock_resume:
                monitor._check_recovery_state(state_file)
                mock_resume.assert_called_once()

        finally:
            state_file.unlink(missing_ok=True)

    def test_pm_corrupted_state_recovery(self):
        """Test recovery when PM is in corrupted state."""
        mock_tmux = Mock(spec=TMUXManager)

        # Simulate corrupted pane content
        mock_tmux.capture_pane.return_value = "\x00\x01\x02\xff\xfe" * 100  # Binary garbage

        monitor = IdleMonitor(mock_tmux)

        # Should detect corruption and attempt recovery
        is_corrupted = monitor._detect_pane_corruption("test:1")
        assert is_corrupted, "Failed to detect pane corruption"

        # Should attempt terminal reset
        with patch.object(monitor, "_reset_terminal") as mock_reset:
            monitor._handle_corrupted_pm("test:1")
            mock_reset.assert_called_once()


class TestPMRecoveryIntegration:
    """Integration tests for complete PM recovery flow."""

    @pytest.mark.slow
    def test_end_to_end_pm_recovery(self):
        """Test complete PM recovery flow."""
        from tests.conftest import MockTMUXManager

        tmux = MockTMUXManager()
        test_session = "test-e2e-recovery"

        try:
            # Create session
            tmux.create_session(test_session)

            # Spawn PM
            result = subprocess.run(
                ["tmux-orc", "spawn", "pm", "--session", test_session], capture_output=True, text=True
            )
            assert result.returncode == 0

            # Wait for PM to initialize
            time.sleep(10)

            # Kill PM window to trigger recovery
            pm_target = f"{test_session}:1"
            subprocess.run(["tmux", "kill-window", "-t", pm_target], check=True)

            # Wait for daemon to detect and recover
            # In real scenario, daemon would be running
            recovery_start = time.time()

            # Check for recovery (would be done by daemon)
            recovered = False
            while time.time() - recovery_start < 120:  # 2 minute timeout
                windows = tmux.list_windows(test_session)
                pm_windows = [w for w in windows if "pm" in w.get("name", "").lower()]

                if pm_windows:
                    recovered = True
                    break

                time.sleep(5)

            assert recovered, "PM was not recovered within timeout"

            # Verify recovery timing
            recovery_time = time.time() - recovery_start
            assert recovery_time < 60, f"Recovery took too long: {recovery_time}s"

        finally:
            # Cleanup
            subprocess.run(["tmux", "kill-session", "-t", test_session], capture_output=True)

    def test_pm_recovery_with_team_notification(self):
        """Test PM recovery includes team notification."""
        # Mock team agents
        team_agents = [
            {"target": "test:2", "name": "dev1", "type": "developer"},
            {"target": "test:3", "name": "qa1", "type": "qa"},
        ]

        monitor = IdleMonitor(Mock())

        with patch.object(monitor, "_get_team_agents") as mock_team:
            mock_team.return_value = team_agents

            with patch.object(monitor, "_notify_agent") as mock_notify:
                monitor._notify_team_of_pm_recovery("test:1")

                # Each team member should be notified
                assert mock_notify.call_count == len(team_agents)

                # Check notification content
                for call in mock_notify.call_args_list:
                    target, message = call[0]
                    assert "PM has been recovered" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
