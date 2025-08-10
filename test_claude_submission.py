#!/usr/bin/env python3
"""Test different methods to submit messages to Claude in tmux."""

import subprocess
import sys
import time


def test_key_combination(session_window: str, test_name: str, keys: list[str], message: str = "Test message"):
    """Test a specific key combination for submitting messages."""
    print(f"\n=== Testing: {test_name} ===")

    # Clear input first
    subprocess.run(["tmux", "send-keys", "-t", session_window, "C-c"], check=False)
    time.sleep(0.5)
    subprocess.run(["tmux", "send-keys", "-t", session_window, "C-u"], check=False)
    time.sleep(0.5)

    # Send the test message
    subprocess.run(["tmux", "send-keys", "-t", session_window, message], check=True)
    time.sleep(1.0)

    # Try the key combination
    for key in keys:
        print(f"  Sending: {key}")
        subprocess.run(["tmux", "send-keys", "-t", session_window, key], check=True)
        time.sleep(0.5)

    # Wait to see if it worked
    time.sleep(3.0)

    # Capture result
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", session_window, "-p", "-S", "-20"], capture_output=True, text=True, check=True
    )

    print(f"  Result preview: {result.stdout[-200:]}")
    return result.stdout


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_claude_submission.py <session:window>")
        print("Example: python test_claude_submission.py daemon-fix-fullstack:3")
        sys.exit(1)

    target = sys.argv[1]

    # Test cases
    test_cases = [
        ("Ctrl+Enter", ["C-Enter"]),
        ("Shift+Enter", ["S-Enter"]),
        ("Meta+Enter", ["M-Enter"]),
        ("Alt+Enter", ["M-Enter"]),  # Alt is often Meta
        ("Ctrl+J", ["C-j"]),
        ("Ctrl+M then Enter", ["C-m", "Enter"]),
        ("Double Enter", ["Enter", "Enter"]),
        ("Enter with delay", ["Enter", "sleep 1", "Enter"]),
        ("Tab then Enter", ["Tab", "Enter"]),
        ("End then Enter", ["End", "Enter"]),
        ("Escape then Enter", ["Escape", "Enter"]),
        ("Space then Backspace then Enter", ["Space", "BSpace", "Enter"]),
        ("Function keys", ["F1", "Enter"]),
        ("Page Down then Enter", ["PageDown", "Enter"]),
    ]

    for test_name, keys in test_cases:
        # Handle special sleep command
        processed_keys = []
        for key in keys:
            if key.startswith("sleep"):
                time.sleep(float(key.split()[1]))
            else:
                processed_keys.append(key)

        if processed_keys:
            test_key_combination(target, test_name, processed_keys)

        # Give some time between tests
        time.sleep(2.0)


if __name__ == "__main__":
    main()
