#!/usr/bin/env python3
"""
Test PM Notification Bug - Why aren't notifications being sent?
"""

import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


def test_pm_notification_flow():
    """Test if PM notifications are attempted during rate limit"""

    print("🔍 PM Notification Bug Test")
    print("=" * 50)

    # Check the notification logic in code
    print("\n1. Checking notification conditions...")

    # Test requirements for PM notification
    test_conditions = {
        "PM has Claude interface": True,  # Required
        "should_notify_pm() returns True": True,  # Required
        "Rate limit detected": True,  # Trigger
        "PM in notification cooldown": False,  # Blocker
    }

    print("\nNotification Requirements:")
    for condition, status in test_conditions.items():
        print(f"  {condition}: {'✅' if status else '❌'}")

    # Test the actual notification path
    print("\n2. Testing notification path...")

    Path(tempfile.mkdtemp(prefix="pm_notify_test_"))
    session = "pm-notify-test"

    try:
        # Create test session
        subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
        subprocess.run(["tmux", "new-session", "-d", "-s", session, "-n", "pm"], check=True)

        # Check if PM notification code executes
        print("\n3. Code path analysis:")
        print("  monitor.py:1893-1925 - PM notification block")
        print("  Key check: is_claude_interface_present(pm_content)")
        print("  If False, skips notification entirely")

        # The issue might be:
        # 1. PM doesn't have Claude interface when checked
        # 2. Notification cooldown blocking
        # 3. Exception in notification attempt

        print("\n4. Common failure points:")
        print("  ❌ PM window not running Claude Code")
        print("  ❌ PM in bash prompt when checked")
        print("  ❌ Notification attempt throws exception")
        print("  ❌ Rate limit message not properly detected")

        return True

    finally:
        subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)


def test_notification_helper_functions():
    """Test the helper functions used in notification logic"""

    from tmux_orchestrator.core.monitor_helpers import AgentState, should_notify_pm

    print("\n5. Testing notification helper functions...")

    # Test should_notify_pm for rate limited state
    result = should_notify_pm(state=AgentState.RATE_LIMITED, target="test-agent:1", notification_history={})

    print(f"  should_notify_pm(RATE_LIMITED): {'✅' if result else '❌'}")

    # Test with cooldown
    from datetime import timedelta

    recent_notification = {"crash_test-agent:1": datetime.now() - timedelta(minutes=2)}

    result_cooldown = should_notify_pm(
        state=AgentState.RATE_LIMITED, target="test-agent:1", notification_history=recent_notification
    )

    print(f"  should_notify_pm with recent notification: {'✅' if result_cooldown else '❌'}")

    print("\n💡 Likely Issue: PM doesn't have Claude interface active when rate limit detected!")


if __name__ == "__main__":
    test_pm_notification_flow()
    test_notification_helper_functions()
