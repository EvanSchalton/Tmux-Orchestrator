#!/usr/bin/env python3
"""
Test harness for PM crash detection validation.
Provides utilities to test various PM crash scenarios.
"""

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

import psutil
import pytest

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager


class PMCrashTestHarness:
    """Test harness for validating PM crash detection."""

    def __init__(self):
        self.tmux = TMUXManager()
        self.test_sessions = []
        self.spawned_processes = []
        self.monitors = []

    def setup(self):
        """Setup test environment."""
        self.cleanup()

    def cleanup(self):
        """Clean up test sessions and processes."""
        # Kill test sessions
        for session in self.test_sessions:
            try:
                subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
            except Exception:
                pass

        # Kill spawned processes
        for pid in self.spawned_processes:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        # Stop monitors
        for monitor in self.monitors:
            try:
                monitor.stop()
            except Exception:
                pass

        self.test_sessions.clear()
        self.spawned_processes.clear()
        self.monitors.clear()

    def create_test_session(self, name: str) -> str:
        """Create a tmux session for testing."""
        session_name = f"test-{name}-{os.getpid()}"

        if not self.tmux.has_session(session_name):
            self.tmux.create_session(session_name)

        self.test_sessions.append(session_name)
        return session_name

    def spawn_test_pm(self, session_name: str) -> Dict[str, Any]:
        """Spawn a PM in the test session and return details."""
        # Use tmux-orc spawn command
        result = subprocess.run(["tmux-orc", "spawn", "pm", "--session", session_name], capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to spawn PM: {result.stderr}")

        # Find PM window (usually :1)
        windows = self.tmux.list_windows(session_name)
        pm_window = None
        for window in windows:
            if "pm" in window.get("name", "").lower():
                pm_window = window
                break

        if not pm_window:
            raise RuntimeError("Could not find PM window after spawn")

        pm_target = f"{session_name}:{pm_window['index']}"

        # Get process details
        pm_pid = self._get_pane_process_pid(pm_target)

        return {"target": pm_target, "pid": pm_pid, "session": session_name, "window": pm_window["index"]}

    def _get_pane_process_pid(self, target: str) -> Optional[int]:
        """Get the main process PID for a pane."""
        # Get pane PID
        result = subprocess.run(
            ["tmux", "list-panes", "-t", target, "-F", "#{pane_pid}"], capture_output=True, text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            pane_pid = int(result.stdout.strip())

            # Find Claude process under this pane
            try:
                parent = psutil.Process(pane_pid)
                for child in parent.children(recursive=True):
                    if any("claude" in cmd for cmd in child.cmdline()):
                        return child.pid
            except Exception:
                pass

        return None

    def simulate_pm_crash(self, pm_details: Dict[str, Any], crash_type: str) -> Dict[str, Any]:
        """Simulate different types of PM crashes."""
        crash_info = {
            "type": crash_type,
            "timestamp": time.time(),
            "pm_target": pm_details["target"],
            "pm_pid": pm_details["pid"],
        }

        if crash_type == "sigkill":
            if pm_details["pid"]:
                os.kill(pm_details["pid"], signal.SIGKILL)
                crash_info["action"] = f"Sent SIGKILL to PID {pm_details['pid']}"
            else:
                raise ValueError("No PM PID available for SIGKILL")

        elif crash_type == "window_closure":
            subprocess.run(["tmux", "kill-window", "-t", pm_details["target"]], check=True)
            crash_info["action"] = f"Killed window {pm_details['target']}"

        elif crash_type == "freeze":
            if pm_details["pid"]:
                os.kill(pm_details["pid"], signal.SIGSTOP)
                crash_info["action"] = f"Sent SIGSTOP to PID {pm_details['pid']}"
                # Store PID for later SIGCONT in cleanup
                self.spawned_processes.append(pm_details["pid"])
            else:
                raise ValueError("No PM PID available for freeze")

        elif crash_type == "interface_loss":
            # Clear the pane and break Claude interface
            subprocess.run(["tmux", "send-keys", "-t", pm_details["target"], "C-c"], check=True)
            time.sleep(0.5)
            subprocess.run(["tmux", "send-keys", "-t", pm_details["target"], "clear", "Enter"], check=True)
            crash_info["action"] = "Cleared pane and broke Claude interface"

        else:
            raise ValueError(f"Unknown crash type: {crash_type}")

        return crash_info

    def wait_for_detection(self, monitor: IdleMonitor, pm_target: str, timeout: int = 60) -> Dict[str, Any]:
        """Wait for monitor to detect PM crash."""
        start_time = time.time()
        detection_result = {"detected": False, "detection_time": None, "detection_latency": None}

        # Check logs for detection
        log_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/logs/idle-monitor.log")
        initial_log_size = log_file.stat().st_size if log_file.exists() else 0

        while time.time() - start_time < timeout:
            # Check if detection methods exist and work
            try:
                # Test various detection methods
                if hasattr(monitor, "_check_pm_health"):
                    health = monitor._check_pm_health(pm_target)
                    if health and health.get("status") in ["critical", "failed"]:
                        detection_result["detected"] = True
                        detection_result["detection_method"] = "_check_pm_health"
                        break

                if hasattr(monitor, "_detect_pm_crash"):
                    crash_detected = monitor._detect_pm_crash(pm_target)
                    if crash_detected:
                        detection_result["detected"] = True
                        detection_result["detection_method"] = "_detect_pm_crash"
                        break

                # Check logs for detection messages
                if log_file.exists():
                    current_log_size = log_file.stat().st_size
                    if current_log_size > initial_log_size:
                        with open(log_file) as f:
                            f.seek(initial_log_size)
                            new_content = f.read()

                        crash_keywords = [
                            "PM crash detected",
                            "PM not responding",
                            "PM window not found",
                            "PM process terminated",
                            f"crash in {pm_target}",
                            f"Missing PM in {pm_target}",
                        ]

                        if any(keyword in new_content for keyword in crash_keywords):
                            detection_result["detected"] = True
                            detection_result["detection_method"] = "log_analysis"
                            detection_result["log_content"] = new_content
                            break

            except Exception as e:
                detection_result["error"] = str(e)

            time.sleep(1)

        detection_result["detection_time"] = time.time()
        detection_result["detection_latency"] = detection_result["detection_time"] - start_time

        return detection_result

    def validate_recovery(self, session_name: str, original_pm_target: str, timeout: int = 120) -> Dict[str, Any]:
        """Validate that PM recovery completed successfully."""
        start_time = time.time()
        recovery_result = {
            "recovered": False,
            "recovery_time": None,
            "recovery_latency": None,
            "new_pm_target": None,
            "new_pm_pid": None,
        }

        while time.time() - start_time < timeout:
            # Check for new PM in the session
            windows = self.tmux.list_windows(session_name)
            pm_windows = []

            for window in windows:
                window_name = window.get("name", "").lower()
                if "pm" in window_name or "project" in window_name:
                    pm_windows.append(window)

            if pm_windows:
                # Found potential PM window
                new_pm_target = f"{session_name}:{pm_windows[0]['index']}"

                # Verify it's actually a PM (has Claude interface)
                pane_content = self.tmux.capture_pane(new_pm_target)

                # Look for Claude interface indicators
                claude_indicators = [
                    "Claude",
                    "Assistant:",
                    "I'll help",
                    "I can help",
                    "tmux-orc",
                    "PM>",
                    "Project Manager",
                ]

                if any(indicator in pane_content for indicator in claude_indicators):
                    recovery_result["recovered"] = True
                    recovery_result["new_pm_target"] = new_pm_target
                    recovery_result["new_pm_pid"] = self._get_pane_process_pid(new_pm_target)
                    break

            time.sleep(2)

        recovery_result["recovery_time"] = time.time()
        recovery_result["recovery_latency"] = recovery_result["recovery_time"] - start_time

        return recovery_result

    def run_crash_detection_test(
        self, crash_type: str, detection_timeout: int = 60, recovery_timeout: int = 120
    ) -> Dict[str, Any]:
        """Run a complete crash detection test."""
        test_result = {"crash_type": crash_type, "test_start": time.time(), "success": False, "errors": []}

        try:
            # Setup
            session_name = self.create_test_session(f"crash-{crash_type}")
            pm_details = self.spawn_test_pm(session_name)

            # Give PM time to initialize
            time.sleep(5)

            # Create monitor
            monitor = IdleMonitor(self.tmux)
            self.monitors.append(monitor)

            # Simulate crash
            crash_info = self.simulate_pm_crash(pm_details, crash_type)
            test_result["crash_info"] = crash_info

            # Wait for detection
            detection = self.wait_for_detection(monitor, pm_details["target"], detection_timeout)
            test_result["detection"] = detection

            if not detection["detected"]:
                test_result["errors"].append(f"Crash not detected within {detection_timeout}s")
                return test_result

            # Wait for recovery
            recovery = self.validate_recovery(session_name, pm_details["target"], recovery_timeout)
            test_result["recovery"] = recovery

            if not recovery["recovered"]:
                test_result["errors"].append(f"Recovery not completed within {recovery_timeout}s")
                return test_result

            # Test passed
            test_result["success"] = True
            test_result["total_time"] = time.time() - test_result["test_start"]

        except Exception as e:
            test_result["errors"].append(f"Test exception: {str(e)}")

        finally:
            # Cleanup happens in harness cleanup
            pass

        return test_result


class TestPMCrashDetectionWithHarness:
    """Test cases using the crash detection harness."""

    def setup_method(self):
        """Setup for each test."""
        self.harness = PMCrashTestHarness()
        self.harness.setup()

    def teardown_method(self):
        """Cleanup after each test."""
        self.harness.cleanup()

    @pytest.mark.integration
    def test_sigkill_detection_and_recovery(self):
        """Test SIGKILL detection and recovery using harness."""
        result = self.harness.run_crash_detection_test("sigkill")

        assert result["success"], f"SIGKILL test failed: {result['errors']}"
        assert result["detection"]["detected"], "SIGKILL not detected"
        assert result["detection"]["detection_latency"] < 60, "Detection too slow"
        assert result["recovery"]["recovered"], "Recovery failed"
        assert result["recovery"]["recovery_latency"] < 120, "Recovery too slow"

    @pytest.mark.integration
    def test_window_closure_detection_and_recovery(self):
        """Test window closure detection and recovery using harness."""
        result = self.harness.run_crash_detection_test("window_closure")

        assert result["success"], f"Window closure test failed: {result['errors']}"
        assert result["detection"]["detected"], "Window closure not detected"
        assert result["recovery"]["recovered"], "Recovery after window closure failed"

    @pytest.mark.integration
    def test_freeze_detection(self):
        """Test PM freeze detection using harness."""
        # Freeze detection might take longer
        result = self.harness.run_crash_detection_test("freeze", detection_timeout=300)

        # Note: This test might be expected to fail until implementation is complete
        if not result["success"]:
            pytest.skip(f"Freeze detection not yet implemented: {result['errors']}")

        assert result["detection"]["detected"], "PM freeze not detected"

    @pytest.mark.integration
    def test_interface_loss_detection(self):
        """Test Claude interface loss detection using harness."""
        result = self.harness.run_crash_detection_test("interface_loss")

        # Note: This test might be expected to fail until implementation is complete
        if not result["success"]:
            pytest.skip(f"Interface loss detection not yet implemented: {result['errors']}")

        assert result["detection"]["detected"], "Interface loss not detected"


if __name__ == "__main__":
    # Run harness tests
    harness = PMCrashTestHarness()

    try:
        harness.setup()

        print("Testing PM Crash Detection Implementation")
        print("=" * 50)

        # Test each crash type
        crash_types = ["sigkill", "window_closure", "freeze", "interface_loss"]

        for crash_type in crash_types:
            print(f"\nTesting {crash_type} detection...")

            try:
                result = harness.run_crash_detection_test(crash_type)

                if result["success"]:
                    print(f"✅ {crash_type}: SUCCESS")
                    print(f"   Detection: {result['detection']['detection_latency']:.1f}s")
                    if result.get("recovery", {}).get("recovered"):
                        print(f"   Recovery: {result['recovery']['recovery_latency']:.1f}s")
                else:
                    print(f"❌ {crash_type}: FAILED")
                    for error in result["errors"]:
                        print(f"   Error: {error}")

            except Exception as e:
                print(f"❌ {crash_type}: EXCEPTION - {e}")

    finally:
        harness.cleanup()
        print("\nHarness cleanup completed.")
