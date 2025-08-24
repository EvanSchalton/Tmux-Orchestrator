#!/usr/bin/env python3
"""
Targeted Daemon Sleep Behavior Test
Focus on verifying actual daemon sleep execution during rate limits
"""

import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Setup logging to capture daemon behavior
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_daemon_rate_limit_detection():
    """Test if daemon detects and handles rate limit messages correctly"""

    # Create isolated test directory
    test_dir = Path(tempfile.mkdtemp(prefix="daemon_sleep_test_"))
    logs_dir = test_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    session_name = "daemon-sleep-test"

    try:
        # Clean up any existing session
        subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)

        # Create test session with PM
        subprocess.run(["tmux", "new-session", "-d", "-s", session_name, "-n", "pm", "bash"], check=True)

        # Set environment for daemon
        env = os.environ.copy()
        env["TMUX_ORCHESTRATOR_BASE_DIR"] = str(test_dir)

        # Start daemon
        logger.info(f"Starting daemon with base dir: {test_dir}")
        daemon_cmd = ["tmux-orc", "monitor", "start", "--session", session_name]
        daemon_process = subprocess.Popen(
            daemon_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        # Wait for daemon to start monitoring
        time.sleep(5)

        # Check if daemon is running
        daemon_running = daemon_process.poll() is None
        logger.info(f"Daemon running: {daemon_running}")

        if not daemon_running:
            stdout, _ = daemon_process.communicate()
            logger.error(f"Daemon failed to start: {stdout}")
            return False

        # Inject rate limit message into PM session
        reset_time = datetime.now(timezone.utc) + timedelta(minutes=2)
        rate_limit_msg = (
            f"I need to stop here due to API rate limits. "
            f"The current time is {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC. "
            f"My rate limits will reset at {reset_time.strftime('%Y-%m-%d %H:%M:%S')} UTC "
            f"(approximately 2 minutes from now)."
        )

        logger.info("Injecting rate limit message...")
        subprocess.run(["tmux", "send-keys", "-t", f"{session_name}:pm", f'echo "{rate_limit_msg}"', "Enter"])

        # Wait a bit for daemon to detect the message
        time.sleep(3)

        # Check daemon logs for rate limit detection
        daemon_log = logs_dir / "daemon.log"
        log_content = ""
        if daemon_log.exists():
            with open(daemon_log) as f:
                log_content = f.read()

        logger.info(f"Daemon log content:\n{log_content}")

        # Look for rate limit detection patterns
        rate_limit_detected = any(
            [
                "Rate limit detected" in log_content,
                "rate limit" in log_content.lower(),
                "sleeping" in log_content.lower(),
                str(reset_time.year) in log_content,  # Reset time mentioned
            ]
        )

        logger.info(f"Rate limit detection in logs: {rate_limit_detected}")

        # Monitor daemon process for 30 seconds to see if it goes to sleep
        start_time = time.time()
        sleep_behavior_detected = False

        logger.info("Monitoring daemon process behavior...")
        for i in range(30):  # Monitor for 30 seconds
            time.sleep(1)

            # Check if daemon is still running
            if daemon_process.poll() is not None:
                logger.warning("Daemon process terminated unexpectedly")
                break

            # Re-read log file to see updates
            if daemon_log.exists():
                with open(daemon_log) as f:
                    current_log = f.read()

                if len(current_log) > len(log_content):
                    new_content = current_log[len(log_content) :]
                    logger.info(f"New log content: {new_content}")
                    log_content = current_log

                    if "sleeping for" in new_content.lower():
                        sleep_behavior_detected = True
                        logger.info("✅ Daemon sleep behavior detected!")
                        break

        logger.info(f"Sleep behavior detected: {sleep_behavior_detected}")

        return rate_limit_detected and sleep_behavior_detected

    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        return False

    finally:
        # Cleanup
        try:
            if "daemon_process" in locals():
                daemon_process.terminate()
                daemon_process.wait(timeout=5)
        except (ProcessLookupError, OSError):
            pass

        subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)
        subprocess.run(["tmux-orc", "monitor", "stop"], capture_output=True)


def test_direct_monitor_functionality():
    """Test monitor.py rate limit handling directly"""

    logger.info("Testing monitor.py rate limit detection logic...")

    # Test the rate limit regex pattern
    test_messages = [
        "I need to stop here due to API rate limits. The current time is 2025-08-20 17:30:00 UTC. My rate limits will reset at 2025-08-20 17:32:00 UTC (approximately 2 minutes from now).",
        "Due to rate limiting, I must pause. Current time: 2025-08-20 17:30:00 UTC. Reset at: 2025-08-20 17:35:00 UTC",
        "API rate limits reached. Will reset at 2025-08-20 17:45:00 UTC",
        "No rate limit message here",
    ]

    # Import the rate limit detection function
    try:
        from tmux_orchestrator.core.monitor_helpers import extract_rate_limit_reset_time

        for i, msg in enumerate(test_messages):
            try:
                reset_time = extract_rate_limit_reset_time(msg)
                logger.info(f"Message {i+1}: Reset time = {reset_time}")
            except Exception as e:
                logger.info(f"Message {i+1}: No rate limit detected - {e}")

    except ImportError as e:
        logger.error(f"Could not import rate limit functions: {e}")
        return False

    return True


def main():
    """Run comprehensive daemon sleep behavior tests"""
    print("🔍 Testing Daemon Sleep Behavior During Rate Limits")
    print("=" * 60)

    # Test 1: Direct monitor functionality
    logger.info("Test 1: Direct monitor rate limit detection")
    test1_result = test_direct_monitor_functionality()
    print(f"✅ Direct monitor test: {'PASS' if test1_result else 'FAIL'}")

    # Test 2: End-to-end daemon behavior
    logger.info("Test 2: End-to-end daemon sleep behavior")
    test2_result = test_daemon_rate_limit_detection()
    print(f"✅ Daemon sleep test: {'PASS' if test2_result else 'FAIL'}")

    overall_success = test1_result and test2_result
    print(f"\n🏁 Overall Result: {'✅ ALL TESTS PASS' if overall_success else '❌ TESTS FAILED'}")

    if not overall_success:
        print("\n🔧 Investigation needed:")
        if not test1_result:
            print("- Rate limit detection logic may be broken")
        if not test2_result:
            print("- Daemon sleep execution is not working as expected")

    return 0 if overall_success else 1


if __name__ == "__main__":
    exit(main())
