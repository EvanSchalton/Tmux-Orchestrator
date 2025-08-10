#!/usr/bin/env python3
"""Test the updated TMUXManager send_message method."""

import sys
import time

from tmux_orchestrator.utils.tmux import TMUXManager


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_message_send.py <session:window> [message]")
        print("Example: python test_message_send.py daemon-fix-fullstack:2 'Test message from updated method'")
        sys.exit(1)

    target = sys.argv[1]
    message = sys.argv[2] if len(sys.argv) > 2 else "Test message from updated TMUXManager method"

    print(f"Testing message send to {target}")
    print(f"Message: {message}")

    # Get before state
    tm = TMUXManager()
    before_content = tm.capture_pane(target, 50)
    print("\nBefore state (last few lines):")
    print(before_content.split("\n")[-5:])

    # Send message
    print("\nSending message...")
    success = tm.send_message(target, message)
    print(f"Send result: {success}")

    # Wait and check after state
    time.sleep(5)
    after_content = tm.capture_pane(target, 50)
    print("\nAfter state (last few lines):")
    print(after_content.split("\n")[-5:])

    # Check if message was submitted
    if message not in after_content or len(after_content.split("\n")) > len(before_content.split("\n")):
        print("\n✅ SUCCESS: Message appears to have been submitted!")
    else:
        print("\n❌ FAILURE: Message still visible, likely not submitted")


if __name__ == "__main__":
    main()
