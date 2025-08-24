#!/usr/bin/env python3
"""
Rate Limit Fix Validation - Corrected Implementation
Tests the actual rate limit detection and sleep behavior
"""

import json
import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_rate_limit_regex_patterns():
    """Test rate limit detection regex against actual Claude messages"""

    # Import the actual function
    from tmux_orchestrator.core.monitor_helpers import extract_rate_limit_reset_time

    # Test messages that match Claude's actual rate limit format
    test_messages = [
        "I apologize, but I need to stop here due to API rate limits. Your limit will reset at 6pm (UTC).",
        "Due to rate limiting, I must pause. Your limit will reset at 12:30am (UTC).",
        "API rate limits reached. Your limit will reset at 11am (UTC).",
        "Your limit will reset at 3:45pm (UTC) in about 2 hours.",
        "This doesn't contain the right format",
    ]

    results = []
    for i, msg in enumerate(test_messages, 1):
        reset_time = extract_rate_limit_reset_time(msg)
        logger.info(f"Test {i}: '{msg[:50]}...' -> {reset_time}")
        results.append((msg, reset_time))

    # Should find reset times in first 4 messages
    successful_detections = sum(1 for _, reset_time in results if reset_time is not None)
    expected_detections = 4

    logger.info(f"Regex test: {successful_detections}/{expected_detections} successful detections")
    return successful_detections == expected_detections


def test_sleep_duration_calculation():
    """Test the sleep duration calculation logic"""

    from tmux_orchestrator.core.monitor_helpers import calculate_sleep_duration

    # Test current time
    now = datetime.now(timezone.utc)

    # Test cases: (reset_time_str, expected_range_hours)
    test_cases = [
        ("6pm", (0, 24)),  # Should be within next 24 hours
        ("12:30am", (0, 24)),
        ("11am", (0, 24)),
        ("3:45pm", (0, 24)),
    ]

    all_passed = True
    for reset_time_str, (min_hours, max_hours) in test_cases:
        try:
            sleep_seconds = calculate_sleep_duration(reset_time_str, now)
            sleep_hours = sleep_seconds / 3600

            if min_hours <= sleep_hours <= max_hours:
                logger.info(f"✅ {reset_time_str}: {sleep_seconds}s ({sleep_hours:.1f}h)")
            else:
                logger.error(f"❌ {reset_time_str}: {sleep_seconds}s ({sleep_hours:.1f}h) outside expected range")
                all_passed = False

        except Exception as e:
            logger.error(f"❌ {reset_time_str}: Exception - {e}")
            all_passed = False

    return all_passed


def test_end_to_end_rate_limit_workflow():
    """Test complete rate limit workflow with corrected message format"""

    test_dir = Path(tempfile.mkdtemp(prefix="rate_limit_e2e_"))
    session_name = "rate-limit-e2e-test"

    try:
        logger.info(f"Starting E2E test with base dir: {test_dir}")

        # Clean up any existing session
        subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)

        # Create test session
        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", session_name, "-n", "pm", "bash"], capture_output=True, text=True
        )

        if result.returncode != 0:
            logger.error(f"Failed to create session: {result.stderr}")
            return False

        # Set environment and start daemon
        env = os.environ.copy()
        env["TMUX_ORCHESTRATOR_BASE_DIR"] = str(test_dir)

        daemon_process = subprocess.Popen(
            ["tmux-orc", "monitor", "start", "--interval", "5"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Wait for daemon to initialize
        time.sleep(3)

        # Check daemon is running
        if daemon_process.poll() is not None:
            stdout, _ = daemon_process.communicate()
            logger.error(f"Daemon failed to start: {stdout}")
            return False

        logger.info("✅ Daemon started successfully")

        # Inject proper rate limit message format
        reset_time = datetime.now(timezone.utc) + timedelta(minutes=2)
        rate_limit_msg = f"I need to stop here due to API rate limits. Your limit will reset at {reset_time.strftime('%-I:%M%p').lower()} (UTC)."

        logger.info(f"Injecting rate limit message: {rate_limit_msg}")

        subprocess.run(["tmux", "send-keys", "-t", f"{session_name}:pm", f'echo "{rate_limit_msg}"', "Enter"])

        # Wait for daemon to detect and process
        time.sleep(10)

        # Check daemon logs
        daemon_log = test_dir / "logs" / "daemon.log"
        log_content = ""
        if daemon_log.exists():
            with open(daemon_log) as f:
                log_content = f.read()

        logger.info(f"Daemon log content:\n{log_content}")

        # Look for expected behaviors
        rate_limit_detected = "Rate limit detected" in log_content
        sleep_initiated = "sleeping for" in log_content.lower()

        logger.info(f"Rate limit detected: {rate_limit_detected}")
        logger.info(f"Sleep initiated: {sleep_initiated}")

        # Check if session is still alive
        session_alive = subprocess.run(["tmux", "has-session", "-t", session_name], capture_output=True).returncode == 0

        logger.info(f"Session alive: {session_alive}")

        return rate_limit_detected and sleep_initiated and session_alive

    except Exception as e:
        logger.error(f"E2E test failed: {e}")
        return False

    finally:
        # Cleanup
        try:
            if "daemon_process" in locals():
                daemon_process.terminate()
                daemon_process.wait(timeout=5)
        except Exception:
            pass

        subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)
        subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True)


def main():
    """Run comprehensive rate limit validation"""
    print("🔍 Rate Limit Fix Validation")
    print("=" * 50)

    # Test 1: Regex pattern detection
    logger.info("Test 1: Rate limit message detection")
    test1_pass = test_rate_limit_regex_patterns()
    print(f"✅ Regex patterns: {'PASS' if test1_pass else 'FAIL'}")

    # Test 2: Sleep duration calculation
    logger.info("Test 2: Sleep duration calculation")
    test2_pass = test_sleep_duration_calculation()
    print(f"✅ Sleep calculation: {'PASS' if test2_pass else 'FAIL'}")

    # Test 3: End-to-end workflow
    logger.info("Test 3: End-to-end workflow")
    test3_pass = test_end_to_end_rate_limit_workflow()
    print(f"✅ E2E workflow: {'PASS' if test3_pass else 'FAIL'}")

    overall_pass = test1_pass and test2_pass and test3_pass
    print(f"\n🏁 Overall Result: {'✅ ALL TESTS PASS' if overall_pass else '❌ TESTS FAILED'}")

    # Generate validation report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tests": {"regex_detection": test1_pass, "sleep_calculation": test2_pass, "end_to_end_workflow": test3_pass},
        "overall_success": overall_pass,
        "expected_workflow": [
            "1. Daemon detects rate limit message with correct regex",
            "2. Calculates sleep duration until reset time + 2 min buffer",
            "3. Logs rate limit detection and sleep duration",
            "4. Daemon sleeps for calculated period",
            "5. Session remains alive during sleep",
            "6. Daemon resumes after sleep period",
        ],
        "findings": {
            "rate_limit_regex": "Matches 'Your limit will reset at X (UTC)' pattern",
            "sleep_calculation": "Adds 2-minute buffer to reset time",
            "daemon_behavior": "Should maintain session during sleep",
        },
    }

    # Save validation report
    report_file = Path("rate_limit_fix_validation_report.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Validation report saved to: {report_file}")

    if not overall_pass:
        print("\n🔧 Issues detected in rate limit workflow")
        print("Please review daemon logs and rate limit detection logic")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    exit(main())
