#!/usr/bin/env python3
"""
Final Rate Limit Validation - PM Notification System Test
Focus on verifying PM notifications work correctly during rate limits
"""

import json
import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_environment():
    """Create isolated test environment"""
    test_dir = Path(tempfile.mkdtemp(prefix="final_rate_limit_test_"))
    session_name = "final-rate-test"

    # Clean up existing session
    subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)

    # Create session with PM window
    subprocess.run(["tmux", "new-session", "-d", "-s", session_name, "-n", "pm", "bash"], check=True)

    return test_dir, session_name


def test_pm_notification_system():
    """Test PM notification during rate limit scenario"""

    test_dir, session_name = create_test_environment()

    try:
        logger.info(f"Testing PM notifications with test dir: {test_dir}")

        # Set environment
        env = os.environ.copy()
        env["TMUX_ORCHESTRATOR_BASE_DIR"] = str(test_dir)

        # Start daemon with short interval for faster testing
        logger.info("Starting daemon...")
        daemon_cmd = ["tmux-orc", "monitor", "start", "--interval", "3"]
        daemon_process = subprocess.Popen(
            daemon_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        time.sleep(5)  # Wait for daemon startup

        if daemon_process.poll() is not None:
            stdout, stderr = daemon_process.communicate()
            logger.error(f"Daemon startup failed: {stdout} {stderr}")
            return False

        logger.info("✅ Daemon started successfully")

        # Step 1: Send a rate limit message to PM
        # Using format that matches the actual Claude rate limit message
        future_time = datetime.now(timezone.utc)
        # Format: 6pm style (Claude uses %-I for no leading zero)
        hour = (future_time.hour + 1) % 24
        if hour == 0:
            time_str = "12am"
        elif hour < 12:
            time_str = f"{hour}am"
        elif hour == 12:
            time_str = "12pm"
        else:
            time_str = f"{hour-12}pm"

        rate_limit_message = f"I need to stop here due to API rate limits. Your limit will reset at {time_str} (UTC)."

        logger.info(f"Sending rate limit message: {rate_limit_message}")

        # Send message to PM session
        subprocess.run(["tmux", "send-keys", "-t", f"{session_name}:pm", f'echo "{rate_limit_message}"', "Enter"])

        # Wait for daemon to process (multiple cycles)
        logger.info("Waiting for daemon to detect rate limit...")
        time.sleep(15)

        # Step 2: Check daemon logs for expected behavior
        daemon_log = test_dir / "logs" / "idle-monitor.log"
        log_content = ""

        if daemon_log.exists():
            with open(daemon_log) as f:
                log_content = f.read()
        else:
            logger.warning("No daemon log file found")

        logger.info(f"Daemon log content:\n{log_content}")

        # Step 3: Analyze results
        results = {
            "rate_limit_detected": False,
            "sleep_duration_calculated": False,
            "daemon_sleep_initiated": False,
            "pm_notification_attempted": False,
            "session_maintained": False,
        }

        # Check for rate limit detection
        if any(phrase in log_content.lower() for phrase in ["rate limit", "reset at", time_str.lower()]):
            results["rate_limit_detected"] = True
            logger.info("✅ Rate limit detected in logs")
        else:
            logger.warning("❌ Rate limit not detected in logs")

        # Check for sleep calculation
        if "sleep" in log_content.lower() or "seconds" in log_content.lower():
            results["sleep_duration_calculated"] = True
            logger.info("✅ Sleep duration mentioned in logs")

        # Check for daemon sleep initiation
        if "sleeping for" in log_content.lower():
            results["daemon_sleep_initiated"] = True
            logger.info("✅ Daemon sleep initiated")

        # Check for PM notification attempts
        if any(phrase in log_content.lower() for phrase in ["notifying pm", "pm notification", "sending message"]):
            results["pm_notification_attempted"] = True
            logger.info("✅ PM notification attempted")

        # Check session is still alive
        session_check = subprocess.run(["tmux", "has-session", "-t", session_name], capture_output=True)

        if session_check.returncode == 0:
            results["session_maintained"] = True
            logger.info("✅ Session maintained during test")
        else:
            logger.warning("❌ Session was killed during test")

        return results

    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        return None

    finally:
        # Cleanup
        try:
            daemon_process.terminate()
            daemon_process.wait(timeout=5)
        except Exception:
            pass

        subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)
        subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True)


def generate_final_report(test_results):
    """Generate comprehensive final validation report"""

    if test_results is None:
        return {"status": "FAILED", "error": "Test execution failed"}

    success_count = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)

    overall_success = success_count >= (total_tests * 0.6)  # 60% pass rate

    report = {
        "validation_timestamp": datetime.now(timezone.utc).isoformat(),
        "test_summary": {
            "total_checks": total_tests,
            "successful_checks": success_count,
            "success_rate": f"{(success_count/total_tests)*100:.1f}%",
            "overall_status": "PASS" if overall_success else "FAIL",
        },
        "detailed_results": test_results,
        "critical_findings": [],
        "workflow_status": {
            "expected_flow": [
                "1. Daemon detects rate limit message",
                "2. Calculates sleep duration until reset + buffer",
                "3. Notifies PM about pause and expected resume time",
                "4. Daemon sleeps for calculated period",
                "5. Session remains alive during rate limit",
                "6. Daemon resumes and notifies PM",
            ],
            "current_status": "PARTIAL" if success_count > 0 else "BROKEN",
        },
        "recommendations": [],
    }

    # Add specific findings
    if not test_results.get("rate_limit_detected", False):
        report["critical_findings"].append("Rate limit detection regex may not be working correctly")
        report["recommendations"].append("Review rate limit message patterns in monitor_helpers.py")

    if not test_results.get("daemon_sleep_initiated", False):
        report["critical_findings"].append("Daemon sleep mechanism not functioning")
        report["recommendations"].append("Verify time.sleep() execution in monitor.py:1928")

    if not test_results.get("session_maintained", False):
        report["critical_findings"].append("Sessions crashing during rate limits instead of graceful pause")
        report["recommendations"].append("Check for unexpected daemon termination or session cleanup")

    if not test_results.get("pm_notification_attempted", False):
        report["critical_findings"].append("PM notification system not working")
        report["recommendations"].append("Verify PM notification logic in monitor.py")

    return report


def main():
    """Execute final validation and generate report"""

    print("🏁 Final Rate Limit Validation")
    print("=" * 50)

    # Run PM notification test
    logger.info("Starting PM notification system test...")
    test_results = test_pm_notification_system()

    # Generate report
    final_report = generate_final_report(test_results)

    # Save report
    report_file = Path("FINAL_RATE_LIMIT_VALIDATION.json")
    with open(report_file, "w") as f:
        json.dump(final_report, f, indent=2)

    # Display results
    print("\n📊 Test Results:")
    if test_results:
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name.replace('_', ' ').title()}: {status}")

    print(f"\n🎯 Overall Status: {final_report['test_summary']['overall_status']}")
    print(f"Success Rate: {final_report['test_summary']['success_rate']}")

    if final_report["critical_findings"]:
        print("\n🚨 Critical Issues Found:")
        for finding in final_report["critical_findings"]:
            print(f"  • {finding}")

    if final_report["recommendations"]:
        print("\n💡 Recommendations:")
        for rec in final_report["recommendations"]:
            print(f"  • {rec}")

    print(f"\n📄 Full report saved to: {report_file}")

    return 0 if final_report["test_summary"]["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    exit(main())
