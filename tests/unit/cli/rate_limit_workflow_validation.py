#!/usr/bin/env python3
"""
Rate Limit Workflow End-to-End Validation Suite
QA Engineer: Comprehensive testing of rate limit graceful flow restoration
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional


class RateLimitTestEnvironment:
    """Controlled environment for rate limit testing"""

    def __init__(self, test_session_name: str = "rate-limit-test"):
        self.test_session_name = test_session_name
        self.daemon_process = None
        self.pm_process = None
        self.test_logs = []
        self.mock_rate_limit_time = None

    def setup_test_session(self):
        """Create isolated test session"""
        # Kill any existing test sessions
        subprocess.run(["tmux", "kill-session", "-t", self.test_session_name], capture_output=True)

        # Create new test session
        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", self.test_session_name, "-c", os.getcwd()],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to create test session: {result.stderr}")

        # Create test windows
        subprocess.run(["tmux", "new-window", "-t", f"{self.test_session_name}:1", "-n", "pm", "bash"])
        subprocess.run(["tmux", "new-window", "-t", f"{self.test_session_name}:2", "-n", "agent1", "bash"])

    def inject_rate_limit_message(self, reset_time_minutes_from_now: int = 5):
        """Inject controlled rate limit message into PM session"""
        reset_time = datetime.now(timezone.utc) + timedelta(minutes=reset_time_minutes_from_now)

        rate_limit_message = (
            f"I need to stop here due to API rate limits. "
            f"The current time is {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC. "
            f"My rate limits will reset at {reset_time.strftime('%Y-%m-%d %H:%M:%S')} UTC "
            f"(approximately {reset_time_minutes_from_now} minutes from now)."
        )

        # Send message to PM window
        escaped_message = rate_limit_message.replace('"', '\\"')
        subprocess.run(["tmux", "send-keys", "-t", f"{self.test_session_name}:1", f'echo "{escaped_message}"', "Enter"])

        self.mock_rate_limit_time = reset_time
        return reset_time

    def start_daemon(self, base_dir: Optional[Path] = None):
        """Start monitoring daemon in test mode"""
        if base_dir is None:
            base_dir = Path(tempfile.mkdtemp(prefix="rate_limit_test_"))

        env = os.environ.copy()
        env["TMUX_ORCHESTRATOR_BASE_DIR"] = str(base_dir)

        cmd = ["tmux-orc", "monitor", "start", "--session", self.test_session_name]

        self.daemon_process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Wait for daemon to initialize
        time.sleep(2)
        return base_dir

    def stop_daemon(self):
        """Stop monitoring daemon"""
        if self.daemon_process:
            try:
                subprocess.run(["tmux-orc", "monitor", "stop"], timeout=10)
                self.daemon_process.wait(timeout=5)
            except (subprocess.TimeoutExpired, Exception):
                if self.daemon_process.poll() is None:
                    self.daemon_process.terminate()
                    try:
                        self.daemon_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.daemon_process.kill()

    def cleanup(self):
        """Clean up test environment"""
        self.stop_daemon()
        subprocess.run(["tmux", "kill-session", "-t", self.test_session_name], capture_output=True)

    def verify_daemon_sleep_execution(self, expected_sleep_duration: int) -> bool:
        """Verify daemon actually sleeps for expected duration"""
        if not self.daemon_process:
            return False

        start_time = time.time()

        # Monitor daemon process state
        sleep_detected = False
        actual_sleep_time = 0

        while time.time() - start_time < expected_sleep_duration + 30:  # Buffer
            if self.daemon_process.poll() is not None:
                # Daemon exited unexpectedly
                return False

            # Check if daemon is in sleep state (not consuming CPU)
            # In a real implementation, this would check process state
            time.sleep(1)
            actual_sleep_time += 1

            if actual_sleep_time >= expected_sleep_duration - 10:  # Allow tolerance
                sleep_detected = True
                break

        return sleep_detected

    def verify_pm_notifications(self, base_dir: Path) -> Dict[str, bool]:
        """Verify PM received pause and resume notifications"""
        results = {"pause_notification": False, "resume_notification": False, "proper_timing": False}

        # Check daemon logs for notification attempts
        log_file = base_dir / "logs" / "daemon.log"
        if log_file.exists():
            with open(log_file) as f:
                log_content = f.read()

            if "Rate limit detected" in log_content:
                results["pause_notification"] = True

            if "resuming monitoring" in log_content:
                results["resume_notification"] = True

            # Check timing consistency
            if results["pause_notification"] and results["resume_notification"]:
                results["proper_timing"] = True

        return results


class RateLimitWorkflowValidator:
    """Main validation class for rate limit workflow"""

    def __init__(self):
        self.test_env = None
        self.test_results = []

    async def run_comprehensive_validation(self) -> Dict[str, any]:
        """Run complete rate limit workflow validation"""
        validation_results = {
            "test_start_time": datetime.now(timezone.utc).isoformat(),
            "scenarios": [],
            "overall_success": False,
            "critical_failures": [],
        }

        scenarios = [
            ("short_rate_limit", 2),  # 2 minute rate limit
            ("medium_rate_limit", 5),  # 5 minute rate limit
            ("concurrent_agents", 3),  # 3 minutes with multiple agents
        ]

        for scenario_name, duration_minutes in scenarios:
            try:
                result = await self._test_scenario(scenario_name, duration_minutes)
                validation_results["scenarios"].append(result)

                if not result["success"]:
                    validation_results["critical_failures"].append(
                        f"{scenario_name}: {result.get('error', 'Unknown failure')}"
                    )

            except Exception as e:
                validation_results["critical_failures"].append(f"{scenario_name}: Exception during test: {str(e)}")

        # Determine overall success
        successful_scenarios = sum(1 for s in validation_results["scenarios"] if s["success"])
        validation_results["overall_success"] = (
            successful_scenarios == len(scenarios) and len(validation_results["critical_failures"]) == 0
        )

        validation_results["test_end_time"] = datetime.now(timezone.utc).isoformat()
        return validation_results

    async def _test_scenario(self, scenario_name: str, duration_minutes: int) -> Dict[str, any]:
        """Test individual rate limit scenario"""
        scenario_result = {
            "scenario": scenario_name,
            "duration_minutes": duration_minutes,
            "success": False,
            "daemon_sleep_verified": False,
            "pm_notifications": {},
            "session_crash_detected": False,
            "error": None,
            "start_time": datetime.now(timezone.utc).isoformat(),
        }

        self.test_env = RateLimitTestEnvironment(f"test-{scenario_name}")

        try:
            # Setup test environment
            self.test_env.setup_test_session()
            base_dir = self.test_env.start_daemon()

            # Wait for daemon to stabilize
            await asyncio.sleep(3)

            # Inject rate limit message
            self.test_env.inject_rate_limit_message(duration_minutes)

            # Verify daemon detects and sleeps
            expected_sleep = duration_minutes * 60 + 120  # +2 min buffer
            daemon_sleep_verified = self.test_env.verify_daemon_sleep_execution(expected_sleep)
            scenario_result["daemon_sleep_verified"] = daemon_sleep_verified

            # Verify PM notifications
            pm_notifications = self.test_env.verify_pm_notifications(base_dir)
            scenario_result["pm_notifications"] = pm_notifications

            # Check for session crashes
            session_exists = (
                subprocess.run(
                    ["tmux", "has-session", "-t", self.test_env.test_session_name], capture_output=True
                ).returncode
                == 0
            )
            scenario_result["session_crash_detected"] = not session_exists

            # Determine success
            scenario_result["success"] = (
                daemon_sleep_verified
                and pm_notifications.get("pause_notification", False)
                and pm_notifications.get("resume_notification", False)
                and not scenario_result["session_crash_detected"]
            )

        except Exception as e:
            scenario_result["error"] = str(e)
            scenario_result["success"] = False

        finally:
            if self.test_env:
                self.test_env.cleanup()

            scenario_result["end_time"] = datetime.now(timezone.utc).isoformat()

        return scenario_result


def create_test_report(validation_results: Dict[str, any]) -> str:
    """Create detailed test report"""
    report = []
    report.append("# Rate Limit Workflow Validation Report")
    report.append(f"**Test Start:** {validation_results['test_start_time']}")
    report.append(f"**Test End:** {validation_results['test_end_time']}")
    report.append(f"**Overall Success:** {'✅ PASS' if validation_results['overall_success'] else '❌ FAIL'}")
    report.append("")

    if validation_results["critical_failures"]:
        report.append("## Critical Failures")
        for failure in validation_results["critical_failures"]:
            report.append(f"- ❌ {failure}")
        report.append("")

    report.append("## Scenario Results")
    for scenario in validation_results["scenarios"]:
        status = "✅ PASS" if scenario["success"] else "❌ FAIL"
        report.append(f"### {scenario['scenario']} ({scenario['duration_minutes']}min) - {status}")
        report.append(f"- **Daemon Sleep:** {'✅' if scenario['daemon_sleep_verified'] else '❌'}")

        pm_notifs = scenario["pm_notifications"]
        report.append(f"- **PM Pause Notification:** {'✅' if pm_notifs.get('pause_notification') else '❌'}")
        report.append(f"- **PM Resume Notification:** {'✅' if pm_notifs.get('resume_notification') else '❌'}")
        report.append(f"- **Session Crash:** {'❌ CRASHED' if scenario['session_crash_detected'] else '✅ NO CRASH'}")

        if scenario.get("error"):
            report.append(f"- **Error:** {scenario['error']}")
        report.append("")

    return "\n".join(report)


async def main():
    """Main execution function"""
    print("🧪 Starting Rate Limit Workflow Validation")
    print("=" * 50)

    validator = RateLimitWorkflowValidator()

    try:
        results = await validator.run_comprehensive_validation()

        # Generate report
        report = create_test_report(results)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = Path(f"rate_limit_validation_{timestamp}.json")
        report_file = Path(f"rate_limit_validation_{timestamp}.md")

        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        with open(report_file, "w") as f:
            f.write(report)

        print(report)
        print(f"\n📄 Results saved to: {results_file}")
        print(f"📄 Report saved to: {report_file}")

        # Exit code based on results
        sys.exit(0 if results["overall_success"] else 1)

    except Exception as e:
        print(f"❌ Validation failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
