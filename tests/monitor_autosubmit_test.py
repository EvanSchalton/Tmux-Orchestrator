#!/usr/bin/env python3
"""Test scenarios for monitor auto-submit functionality."""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class MonitorAutoSubmitTester:
    """Test harness for monitor auto-submit feature."""

    def __init__(self):
        self.log_file = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator/logs/idle-monitor.log")
        self.test_results = []

    def run_command(self, cmd):
        """Run a shell command and return output."""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def check_log_for_pattern(self, pattern, since_time=None):
        """Check if pattern appears in log after given time."""
        if not self.log_file.exists():
            return False

        with open(self.log_file) as f:
            lines = f.readlines()

        for line in lines:
            if pattern in line:
                if since_time:
                    # Parse timestamp from log line
                    try:
                        timestamp_str = line.split(" - ")[0]
                        log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                        if log_time >= since_time:
                            return True
                    except (ValueError, IndexError):
                        continue
                else:
                    return True
        return False

    def test_single_agent_stuck(self) -> None:
        """Test scenario: Single agent with stuck message."""
        print("\n=== Test 1: Single Agent with Stuck Message ===")
        test_start = datetime.now()

        # Create a test session with an agent
        print("Creating test agent...")
        session_name = "test-single-stuck"

        # Kill any existing session
        self.run_command(f"tmux kill-session -t {session_name} 2>/dev/null")

        # Create new session and start Claude
        self.run_command(f"tmux new-session -d -s {session_name}")
        time.sleep(1)

        # Start Claude in the session
        self.run_command(f"tmux send-keys -t {session_name}:0 'claude --dangerously-skip-permissions' Enter")
        time.sleep(5)  # Wait for Claude to start

        # Type a message but don't submit it
        print("Typing message without submitting...")
        self.run_command(f"tmux send-keys -t {session_name}:0 'This is a test message that will get stuck'")

        # Wait for monitor to detect and auto-submit
        print("Waiting for monitor to detect and auto-submit...")
        time.sleep(15)  # Monitor checks every 10 seconds

        # Check logs for auto-submission
        auto_submit_found = self.check_log_for_pattern(
            f"Auto-submitting stuck message for {session_name}:0", since_time=test_start
        )

        idle_detected = self.check_log_for_pattern(
            f"Agent {session_name}:0 is idle with Claude interface", since_time=test_start
        )

        # Check if message was submitted by looking at pane content
        _, pane_content, _ = self.run_command(f"tmux capture-pane -t {session_name}:0 -p")
        message_submitted = "assistant:" in pane_content or "I'll help" in pane_content

        # Clean up
        self.run_command(f"tmux kill-session -t {session_name}")

        # Record results
        result = {
            "test": "single_agent_stuck",
            "idle_detected": idle_detected,
            "auto_submit_triggered": auto_submit_found,
            "message_submitted": message_submitted,
            "success": idle_detected and auto_submit_found and message_submitted,
        }

        self.test_results.append(result)

        print(f"Idle detected: {idle_detected}")
        print(f"Auto-submit triggered: {auto_submit_found}")
        print(f"Message submitted: {message_submitted}")
        print(f"Test result: {'PASS' if result['success'] else 'FAIL'}")

        return result["success"]

    def test_multiple_agents_stuck(self) -> None:
        """Test scenario: Multiple agents stuck simultaneously."""
        print("\n=== Test 2: Multiple Agents Stuck Simultaneously ===")
        test_start = datetime.now()

        sessions = ["test-multi-1", "test-multi-2", "test-multi-3"]

        # Clean up any existing sessions
        for session in sessions:
            self.run_command(f"tmux kill-session -t {session} 2>/dev/null")

        # Create multiple agents
        print("Creating multiple test agents...")
        for i, session in enumerate(sessions):
            self.run_command(f"tmux new-session -d -s {session}")
            time.sleep(0.5)
            self.run_command(f"tmux send-keys -t {session}:0 'claude --dangerously-skip-permissions' Enter")

        time.sleep(5)  # Wait for all Claude instances to start

        # Type messages in all agents without submitting
        print("Typing messages in all agents without submitting...")
        for i, session in enumerate(sessions):
            self.run_command(f"tmux send-keys -t {session}:0 'Test message {i + 1} that will be stuck'")

        # Wait for monitor to process
        print("Waiting for monitor to detect and auto-submit all agents...")
        time.sleep(20)  # Give enough time for monitor cycles

        # Check results for each agent
        all_detected = True
        all_submitted = True

        for session in sessions:
            detected = self.check_log_for_pattern(
                f"Auto-submitting stuck message for {session}:0", since_time=test_start
            )

            _, pane_content, _ = self.run_command(f"tmux capture-pane -t {session}:0 -p")
            submitted = "assistant:" in pane_content or "I'll help" in pane_content

            print(f"{session} - Detected: {detected}, Submitted: {submitted}")

            all_detected = all_detected and detected
            all_submitted = all_submitted and submitted

        # Clean up
        for session in sessions:
            self.run_command(f"tmux kill-session -t {session}")

        # Record results
        result = {
            "test": "multiple_agents_stuck",
            "all_detected": all_detected,
            "all_submitted": all_submitted,
            "success": all_detected and all_submitted,
        }

        self.test_results.append(result)

        print(f"Test result: {'PASS' if result['success'] else 'FAIL'}")

        return result["success"]

    def test_repeated_stuck_agent(self) -> None:
        """Test scenario: Agent that gets stuck repeatedly."""
        print("\n=== Test 3: Agent Gets Stuck Repeatedly ===")
        test_start = datetime.now()

        session_name = "test-repeat-stuck"

        # Clean up
        self.run_command(f"tmux kill-session -t {session_name} 2>/dev/null")

        # Create agent
        print("Creating test agent...")
        self.run_command(f"tmux new-session -d -s {session_name}")
        time.sleep(1)
        self.run_command(f"tmux send-keys -t {session_name}:0 'claude --dangerously-skip-permissions' Enter")
        time.sleep(5)

        # Test multiple stuck scenarios
        submission_counts = []

        for i in range(3):
            print(f"\nRound {i + 1}: Creating stuck message...")

            # Clear any previous response
            self.run_command(f"tmux send-keys -t {session_name}:0 C-c")
            time.sleep(1)

            # Type new message without submitting
            self.run_command(f"tmux send-keys -t {session_name}:0 'Stuck message round {i + 1}'")

            # Wait for auto-submit
            time.sleep(15)

            # Count auto-submit occurrences
            count = 0
            if self.log_file.exists():
                with open(self.log_file) as f:
                    for line in f:
                        if f"Auto-submitting stuck message for {session_name}:0" in line:
                            try:
                                timestamp_str = line.split(" - ")[0]
                                log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                                if log_time >= test_start:
                                    count += 1
                            except (ValueError, IndexError):
                                continue

            submission_counts.append(count)
            print(f"Total auto-submissions so far: {count}")

        # Check for PM notification after multiple attempts
        pm_notified = self.check_log_for_pattern("still stuck after", since_time=test_start)

        # Clean up
        self.run_command(f"tmux kill-session -t {session_name}")

        # Verify no infinite loops (should have reasonable number of submissions)
        total_submissions = submission_counts[-1] if submission_counts else 0
        no_infinite_loop = total_submissions < 15  # Reasonable threshold

        # Record results
        result = {
            "test": "repeated_stuck_agent",
            "total_submissions": total_submissions,
            "pm_notified": pm_notified,
            "no_infinite_loop": no_infinite_loop,
            "success": total_submissions >= 3 and no_infinite_loop,
        }

        self.test_results.append(result)

        print(f"\nTotal submissions: {total_submissions}")
        print(f"PM notified after multiple attempts: {pm_notified}")
        print(f"No infinite loop: {no_infinite_loop}")
        print(f"Test result: {'PASS' if result['success'] else 'FAIL'}")

        return result["success"]

    def test_monitor_stability(self) -> None:
        """Test monitor stability during extended operation."""
        print("\n=== Test 4: Monitor Stability Check ===")

        # Check if monitor is still running
        _, pid_output, _ = self.run_command(
            "cat /workspaces/Tmux-Orchestrator/.tmux_orchestrator/idle-monitor.pid 2>/dev/null"
        )

        if pid_output:
            pid = pid_output.strip()
            _, _, ps_err = self.run_command(f"ps -p {pid}")
            monitor_running = ps_err == ""
        else:
            monitor_running = False

        # Check for recent log entries
        recent_activity = False
        if self.log_file.exists():
            # Get last modification time
            mtime = datetime.fromtimestamp(self.log_file.stat().st_mtime)
            recent_activity = (datetime.now() - mtime).seconds < 30

        # Check for errors in recent logs
        errors_found = False
        if self.log_file.exists():
            _, tail_output, _ = self.run_command(f"tail -100 {self.log_file} | grep -i error")
            errors_found = bool(tail_output.strip())

        # Record results
        result = {
            "test": "monitor_stability",
            "monitor_running": monitor_running,
            "recent_activity": recent_activity,
            "errors_found": errors_found,
            "success": monitor_running and recent_activity and not errors_found,
        }

        self.test_results.append(result)

        print(f"Monitor running: {monitor_running}")
        print(f"Recent activity: {recent_activity}")
        print(f"Errors in logs: {errors_found}")
        print(f"Test result: {'PASS' if result['success'] else 'FAIL'}")

        return result["success"]

    def generate_report(self):
        """Generate test report."""
        print("\n" + "=" * 50)
        print("MONITOR AUTO-SUBMIT TEST REPORT")
        print("=" * 50)
        print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Tests: {len(self.test_results)}")

        passed = sum(1 for r in self.test_results if r["success"])
        failed = len(self.test_results) - passed

        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed / len(self.test_results) * 100):.1f}%")

        print("\nDetailed Results:")
        print("-" * 50)

        for result in self.test_results:
            status = "PASS" if result["success"] else "FAIL"
            print(f"\nTest: {result['test']}")
            print(f"Status: {status}")

            # Print test-specific details
            for key, value in result.items():
                if key not in ["test", "success"]:
                    print(f"  {key}: {value}")

        # Save report to file
        report_path = Path("/workspaces/Tmux-Orchestrator/tests/monitor_autosubmit_report.md")
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, "w") as f:
            f.write("# Monitor Auto-Submit Test Report\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- Total Tests: {len(self.test_results)}\n")
            f.write(f"- Passed: {passed}\n")
            f.write(f"- Failed: {failed}\n")
            f.write(f"- Success Rate: {(passed / len(self.test_results) * 100):.1f}%\n\n")

            f.write("## Test Results\n\n")

            for result in self.test_results:
                status = "✅" if result["success"] else "❌"
                f.write(f"### {status} {result['test']}\n\n")

                for key, value in result.items():
                    if key not in ["test", "success"]:
                        f.write(f"- **{key}:** {value}\n")
                f.write("\n")

        print(f"\nReport saved to: {report_path}")

        return passed == len(self.test_results)


def main():
    """Run all tests."""
    tester = MonitorAutoSubmitTester()

    # Check if monitor is running
    _, _, check_err = tester.run_command("tmux-orc monitor status | grep -q 'is running'")
    if check_err:
        print("ERROR: Monitor is not running. Start it with: tmux-orc monitor start")
        sys.exit(1)

    print("Starting Monitor Auto-Submit Tests...")
    print("This will create and destroy test tmux sessions.")

    # Run all tests
    tester.test_single_agent_stuck()
    tester.test_multiple_agents_stuck()
    tester.test_repeated_stuck_agent()
    tester.test_monitor_stability()

    # Generate report
    all_passed = tester.generate_report()

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
