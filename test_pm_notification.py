#!/usr/bin/env python3
"""Test PM notification system directly."""

from tmux_orchestrator.utils.tmux import TMUXManager
from datetime import datetime, timedelta

def test_pm_notification():
    """Test the PM notification system directly."""
    tmux = TMUXManager()
    
    # Simulate the notification logic
    target = "monitor-fixes:4"  # QA engineer
    pm_target = "monitor-fixes:2"  # PM
    
    print(f"Testing notification from {target} to PM at {pm_target}")
    
    # Create a test message
    idle_duration = timedelta(minutes=5)
    message = (
        f"🚨 IDLE AGENT ALERT:\n\n"
        f"The following agent appears to be idle and needs tasks:\n"
        f"{target} (QA Engineer)\n\n"
        f"Agent has been idle for {int(idle_duration.total_seconds()/60)} minutes.\n"
        f"Please check their status and assign work as needed.\n\n"
        f"This is an automated notification from the idle monitor."
    )
    
    print(f"Sending message: {message[:100]}...")
    
    # Test direct message sending
    try:
        success = tmux.send_message(pm_target, message)
        if success:
            print("✅ Message sent successfully!")
        else:
            print("❌ Message send failed!")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Check if PM actually received it
    print("\nChecking PM terminal content...")
    try:
        content = tmux.capture_pane(pm_target, lines=20)
        if "IDLE AGENT ALERT" in content:
            print("✅ PM received the notification!")
        else:
            print("❌ PM did not receive the notification")
            print("PM terminal content:")
            print(content[-200:])
    except Exception as e:
        print(f"Error checking PM: {e}")

if __name__ == "__main__":
    test_pm_notification()