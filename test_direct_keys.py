#!/usr/bin/env python3
"""Test direct key sequences to submit queued messages."""

import subprocess
import sys
import time


def test_submission(target: str, method_name: str, key_sequence: list):
    """Test a specific key sequence to submit queued messages."""
    print(f"\n=== Testing {method_name} ===")

    # Send the key sequence
    for key in key_sequence:
        print(f"Sending: {key}")
        if key.startswith("sleep:"):
            time.sleep(float(key.split(":")[1]))
        else:
            subprocess.run(["tmux", "send-keys", "-t", target, key], check=False)
            time.sleep(0.2)

    # Wait to see result
    time.sleep(2)

    # Capture result
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", target, "-p", "-S", "-20"], capture_output=True, text=True, check=True
    )

    print(f"Result: {result.stdout.split()[-10:]}")
    return "Press up to edit queued messages" not in result.stdout


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_direct_keys.py <session:window>")
        sys.exit(1)

    target = sys.argv[1]

    # First add a message to queue
    print("Adding test message to queue...")
    subprocess.run(["tmux", "send-keys", "-t", target, "Test message for submission"], check=False)
    time.sleep(1)

    # Test different submission methods
    methods = [
        ("Ctrl+Enter", ["C-Enter"]),
        ("Shift+Enter", ["S-Enter"]),
        ("Meta+Enter", ["M-Enter"]),
        ("Alt+Enter", ["M-Enter"]),
        ("Tab then Enter", ["Tab", "Enter"]),
        ("Down Arrow then Enter", ["Down", "Enter"]),
        ("Space then Enter", ["Space", "Enter"]),
        ("Escape then Enter", ["Escape", "Enter"]),
        ("Function key F1", ["F1"]),
        ("Function key F2", ["F2"]),
        ("Page Down", ["PageDown"]),
        ("Insert key", ["IC"]),
        ("Home then Enter", ["Home", "Enter"]),
        ("Ctrl+J", ["C-j"]),
        ("Ctrl+D", ["C-d"]),
        ("Double Enter with delay", ["Enter", "sleep:0.5", "Enter"]),
    ]

    for method_name, keys in methods:
        if test_submission(target, method_name, keys):
            print(f"✅ SUCCESS: {method_name} worked!")
            break
        else:
            print(f"❌ FAILED: {method_name}")
            # Re-add message for next test
            subprocess.run(["tmux", "send-keys", "-t", target, "Test message for submission"], check=False)
            time.sleep(0.5)


if __name__ == "__main__":
    main()
