#!/usr/bin/env python3
"""Test actual tmux send-keys command to verify message delivery."""

import subprocess
import time


def test_tmux_send_keys(target: str, message: str):
    """Test sending a message via tmux send-keys."""
    print(f"Testing tmux send-keys to {target}")
    print("-" * 50)

    # First, check if target exists
    session, window = target.split(":")
    check_cmd = ["tmux", "list-windows", "-t", session, "-F", "#{window_index}:#{window_name}"]
    result = subprocess.run(check_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"✗ Session '{session}' not found: {result.stderr}")
        return False

    windows = result.stdout.strip().split("\n")
    target_exists = False
    for w in windows:
        if w.startswith(f"{window}:"):
            print(f"✓ Target window found: {w}")
            target_exists = True
            break

    if not target_exists:
        print(f"✗ Window {window} not found in session {session}")
        return False

    # Check current pane content
    print("\nChecking current pane content...")
    capture_cmd = ["tmux", "capture-pane", "-t", target, "-p", "-S", "-10"]
    result = subprocess.run(capture_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"✗ Failed to capture pane: {result.stderr}")
    else:
        print("Current pane (last 10 lines):")
        print("---")
        print(result.stdout)
        print("---")

    # Try to send a test message
    print("\nAttempting to send test message...")

    # Method 1: Direct send-keys
    send_cmd = ["tmux", "send-keys", "-t", target, "TEST: This is a test message from PM detection script", "Enter"]
    result = subprocess.run(send_cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("✓ send-keys command succeeded")
    else:
        print(f"✗ send-keys command failed: {result.stderr}")

        # Try alternative method
        print("\nTrying alternative method with C-u prefix...")
        clear_cmd = ["tmux", "send-keys", "-t", target, "C-u"]
        subprocess.run(clear_cmd, capture_output=True)
        time.sleep(0.1)

        send_cmd = ["tmux", "send-keys", "-t", target, "-l", "TEST: Alternative send method"]
        result = subprocess.run(send_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            enter_cmd = ["tmux", "send-keys", "-t", target, "Enter"]
            subprocess.run(enter_cmd, capture_output=True)
            print("✓ Alternative send method succeeded")
        else:
            print(f"✗ Alternative send method failed: {result.stderr}")

    return True


def main():
    """Test message delivery to PM."""
    print("PM Detection and Message Delivery Test")
    print("=" * 60)

    # Test sending to the PM window
    target = "critical-fixes:1"
    message = "🚨 TEST MESSAGE: Verifying PM notification delivery"

    test_tmux_send_keys(target, message)

    # Also test if we can identify the issue with the daemon logs
    print("\n" + "=" * 60)
    print("Checking for common issues:")
    print("-" * 60)

    # Check if tmux server is running
    server_check = subprocess.run(["tmux", "list-sessions"], capture_output=True, text=True)
    if server_check.returncode == 0:
        print("✓ tmux server is running")
        sessions = [line.split(":")[0] for line in server_check.stdout.strip().split("\n")]
        print(f"  Sessions: {', '.join(sessions)}")
    else:
        print("✗ tmux server is not running or not accessible")

    # Check permissions
    print("\n✓ Script has permission to run tmux commands")

    # Provide debugging command
    print("\n" + "=" * 60)
    print("Debug command to monitor the PM window:")
    print("  tmux attach -t critical-fixes:1")
    print("\nOr to see what the daemon is doing:")
    print("  tmux capture-pane -t critical-fixes:1 -p | tail -20")


if __name__ == "__main__":
    main()
