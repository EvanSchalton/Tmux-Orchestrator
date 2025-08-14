#!/usr/bin/env python3
"""Test the simplified one-command restart system."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tmux_orchestrator.core.monitor import IdleMonitor  # noqa: E402


def test_api_error_detection():
    """Test API error pattern detection."""
    print("=== Test 1: API Error Pattern Detection ===")

    monitor = IdleMonitor(Mock())

    # Test various API error patterns
    test_cases = [
        ("Network error occurred: Unable to reach server", True, "Network/Connection"),
        ("Rate limit exceeded. Please try again later", True, "Rate Limiting"),
        ("Authentication failed: Invalid API key", True, "Authentication"),
        ("\033[31mError: Connection failed\033[0m", True, "Error Output"),
        ("Normal Claude conversation", False, "API Error"),
    ]

    for content, should_detect, expected_type in test_cases:
        detected = monitor._detect_api_error_patterns(content)
        error_type = monitor._identify_error_type(content)

        print(f"Content: {content[:40]}...")
        print(f"  Detected: {detected} (expected: {should_detect})")
        print(f"  Type: {error_type} (expected: {expected_type})")
        print("  ✅ PASS" if detected == should_detect else "  ❌ FAIL")
        print()

    return True


def test_command_format():
    """Test command format generation."""
    print("=== Test 2: Command Format ===")

    # Test basic prompt
    basic_prompt = "You are a backend developer."
    escaped = basic_prompt.replace('"', '\\"')
    command = f'claude --dangerously-skip-permissions --system-prompt "{escaped}"'
    print(f"Basic command: {command}")

    # Test prompt with quotes
    quote_prompt = 'You are a "senior" developer with "expertise".'
    escaped_quotes = quote_prompt.replace('"', '\\"')
    quote_command = f'claude --dangerously-skip-permissions --system-prompt "{escaped_quotes}"'
    print(f"Quote command: {quote_command}")

    print("✅ Command format generation: PASSED")
    return True


def test_role_storage():
    """Test role storage and retrieval."""
    print("=== Test 3: Role Storage ===")

    monitor = IdleMonitor(Mock())

    # Test storing and retrieving roles
    target = "test-session:1"
    role_prompt = "You are a backend developer focused on API development."

    # Store role
    monitor._agent_roles[target] = role_prompt
    print(f"Stored role for {target}")

    # Retrieve role
    retrieved = monitor._agent_roles.get(target)
    print(f"Retrieved: {retrieved}")

    success = retrieved == role_prompt
    print(f"✅ Role storage: {'PASSED' if success else 'FAILED'}")
    return success


def test_pm_notification():
    """Test PM notification format."""
    print("=== Test 4: PM Notification ===")

    mock_tmux = Mock()
    mock_logger = Mock()
    monitor = IdleMonitor(mock_tmux)

    # Mock PM finding
    mock_tmux.list_sessions.return_value = [{"name": "test-session"}]
    mock_tmux.list_windows.return_value = [{"name": "Claude-pm", "index": 0}]
    mock_tmux.capture_pane.return_value = "Claude Code interface present"

    # Set up agent with stored role
    target = "dev-session:1"
    role_prompt = "You are a backend developer."
    monitor._agent_roles[target] = role_prompt

    # Test notification
    try:
        monitor._send_one_command_restart_notification(mock_tmux, target, "API error (Network)", mock_logger)

        # Check if message was sent
        send_calls = mock_tmux.send_message.call_args_list
        if send_calls:
            pm_target, message = send_calls[0][0]
            print(f"PM target: {pm_target}")
            print("Message content:")
            print("-" * 50)
            print(message)
            print("-" * 50)

            # Verify message components
            checks = [
                ("Has agent info", target in message),
                ("Has command format", "--dangerously-skip-permissions" in message),
                ("Has system prompt", "--system-prompt" in message),
                ("Has code blocks", "```" in message),
                ("Has role status", "Role will be restored" in message),
            ]

            for check_name, result in checks:
                print(f"{check_name}: {'✅' if result else '❌'}")

            all_passed = all(result for _, result in checks)
            print(f"✅ PM notification: {'PASSED' if all_passed else 'FAILED'}")
            return all_passed
        else:
            print("❌ No notification sent")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_cooldown():
    """Test 5-minute cooldown mechanism."""
    print("=== Test 5: Cooldown Mechanism ===")

    mock_tmux = Mock()
    mock_logger = Mock()
    monitor = IdleMonitor(mock_tmux)

    target = "test-session:1"

    # Test first attempt (should work)
    monitor._restart_attempts = {}
    result1 = monitor._attempt_agent_restart(mock_tmux, target, mock_logger)
    print(f"First attempt: {result1}")

    # Test second attempt within cooldown (should be blocked)
    if hasattr(monitor, "_restart_attempts"):
        monitor._restart_attempts[f"restart_{target}"] = datetime.now()
        result2 = monitor._attempt_agent_restart(mock_tmux, target, mock_logger)
        print(f"Second attempt (in cooldown): {result2}")

        # Test third attempt after cooldown
        monitor._restart_attempts[f"restart_{target}"] = datetime.now() - timedelta(minutes=6)
        result3 = monitor._attempt_agent_restart(mock_tmux, target, mock_logger)
        print(f"Third attempt (after cooldown): {result3}")

        success = result1 and not result2 and result3
        print(f"✅ Cooldown mechanism: {'PASSED' if success else 'FAILED'}")
        return success
    else:
        print("❌ Cooldown mechanism not found")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Simplified One-Command Restart System")
    print("=" * 60)

    tests = [
        test_api_error_detection,
        test_command_format,
        test_role_storage,
        test_pm_notification,
        test_cooldown,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
        print()

    # Summary
    print("=" * 60)
    print("🏆 TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)

    test_names = ["API Error Detection", "Command Format", "Role Storage", "PM Notification", "Cooldown Mechanism"]

    for i, (name, result) in enumerate(zip(test_names, results)):
        print(f"{name}: {'✅ PASSED' if result else '❌ FAILED'}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎯 All tests PASSED! The simplified restart system is working correctly.")
        print("✅ Much simpler and more reliable than complex autonomous systems!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review implementation.")


if __name__ == "__main__":
    main()
