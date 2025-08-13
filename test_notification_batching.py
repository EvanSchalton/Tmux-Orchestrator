#!/usr/bin/env python3
"""Test script to verify notification batching functionality.

This script simulates the notification collection and batching process
to demonstrate that multiple notifications are properly consolidated
into a single report per PM.
"""

import logging
from unittest.mock import Mock

from tmux_orchestrator.core.monitor import IdleMonitor


def create_mock_tmux():
    """Create a mock TMUXManager with necessary methods."""
    mock_tmux = Mock()

    # Mock PM discovery - return PM at test-session:1
    mock_tmux.list_windows.return_value = [
        {"index": "1", "name": "Claude-pm"},
        {"index": "2", "name": "Claude-backend"},
        {"index": "3", "name": "Claude-qa"},
    ]

    # Mock successful message sending
    mock_tmux.send_message.return_value = True

    return mock_tmux


def create_mock_logger():
    """Create a mock logger."""
    return Mock(spec=logging.Logger)


def test_notification_collection():
    """Test that notifications are properly collected."""
    print("🧪 Testing notification collection...")

    # Setup
    mock_tmux = create_mock_tmux()
    logger = create_mock_logger()
    monitor = IdleMonitor(mock_tmux)

    # Create notification collection dict
    pm_notifications = {}

    # Simulate collecting different types of notifications
    session = "test-session"

    # Crash notification
    crash_msg = """🚨 AGENT CRASH ALERT:

Claude Code has crashed for agent at test-session:2

**RECOVERY ACTIONS NEEDED**:
1. Restart Claude Code in the crashed window
2. Provide system prompt from agent-prompts.yaml
3. Re-assign current tasks
4. Verify agent is responsive

Use this command:
• tmux send-keys -t test-session:2 'claude --dangerously-skip-permissions' Enter"""

    # Idle notification
    idle_msg = """🚨 IDLE AGENT ALERT:

Agent test-session:3 (QA) is currently idle and available for work.

Please review their status and assign tasks as needed.

This is an automated notification from the monitoring system."""

    # Missing agent notification
    missing_msg = """🚨 TEAM MEMBER ALERT:

Missing agents detected in session test-session:
Claude-frontend[test-session:4]

Current team members:
Claude-pm[test-session:1]
Claude-backend[test-session:2]
Claude-qa[test-session:3]

Please review your team plan to determine if these agents are still needed.
If they are needed, restart them with their appropriate briefing.
If they are no longer needed, no action is required.

Use 'tmux list-windows -t test-session' to check window status."""

    # Collect notifications
    monitor._collect_notification(pm_notifications, session, crash_msg, mock_tmux)
    monitor._collect_notification(pm_notifications, session, idle_msg, mock_tmux)
    monitor._collect_notification(pm_notifications, session, missing_msg, mock_tmux)

    # Verify collection
    assert len(pm_notifications) == 1, f"Expected 1 PM, got {len(pm_notifications)}"
    pm_target = list(pm_notifications.keys())[0]
    messages = pm_notifications[pm_target]
    assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"

    print(f"✅ Successfully collected {len(messages)} notifications for PM {pm_target}")
    return pm_notifications, mock_tmux, logger, monitor


def test_notification_consolidation():
    """Test that notifications are properly consolidated."""
    print("\n🧪 Testing notification consolidation...")

    pm_notifications, mock_tmux, logger, monitor = test_notification_collection()

    # Send consolidated notifications
    monitor._send_collected_notifications(pm_notifications, mock_tmux, logger)

    # Verify send_message was called once (consolidated)
    assert mock_tmux.send_message.call_count == 1, f"Expected 1 call, got {mock_tmux.send_message.call_count}"

    # Get the consolidated message
    call_args = mock_tmux.send_message.call_args
    pm_target, consolidated_message = call_args[0]

    print(f"✅ Sent 1 consolidated message to {pm_target}")

    # Verify the consolidated message contains all notification types
    assert "🔔 MONITORING REPORT" in consolidated_message
    assert "🚨 CRASHED AGENTS:" in consolidated_message
    assert "⚠️ IDLE AGENTS:" in consolidated_message
    assert "📍 MISSING AGENTS:" in consolidated_message

    print("✅ Consolidated message contains all notification types")

    return consolidated_message


def test_consolidated_message_format():
    """Test the format of the consolidated message."""
    print("\n🧪 Testing consolidated message format...")

    consolidated_message = test_notification_consolidation()

    print("\n📋 CONSOLIDATED MESSAGE OUTPUT:")
    print("=" * 60)
    print(consolidated_message)
    print("=" * 60)

    # Verify structure
    lines = consolidated_message.split("\n")

    # Check header
    assert any("🔔 MONITORING REPORT" in line for line in lines), "Missing report header"

    # Check sections
    assert any("🚨 CRASHED AGENTS:" in line for line in lines), "Missing crashed agents section"
    assert any("⚠️ IDLE AGENTS:" in line for line in lines), "Missing idle agents section"
    assert any("📍 MISSING AGENTS:" in line for line in lines), "Missing missing agents section"

    # Check footer
    assert any("Please review and take appropriate action" in line for line in lines), "Missing action footer"

    print("✅ Consolidated message format is correct")


def test_multiple_pms():
    """Test notifications for multiple PMs in different sessions."""
    print("\n🧪 Testing multiple PM sessions...")

    mock_tmux = Mock()
    logger = create_mock_logger()
    monitor = IdleMonitor(mock_tmux)

    # Mock different PMs in different sessions
    def mock_list_windows(session):
        if session == "frontend-session":
            return [{"index": "1", "name": "Claude-pm"}, {"index": "2", "name": "Claude-frontend"}]
        elif session == "backend-session":
            return [{"index": "1", "name": "Claude-pm"}, {"index": "2", "name": "Claude-backend"}]
        return []

    mock_tmux.list_windows.side_effect = mock_list_windows
    mock_tmux.send_message.return_value = True

    pm_notifications = {}

    # Collect notifications for different sessions
    monitor._collect_notification(pm_notifications, "frontend-session", "Frontend agent crashed", mock_tmux)
    monitor._collect_notification(pm_notifications, "backend-session", "Backend agent idle", mock_tmux)

    # Should have 2 different PMs
    assert len(pm_notifications) == 2, f"Expected 2 PMs, got {len(pm_notifications)}"

    # Send notifications
    monitor._send_collected_notifications(pm_notifications, mock_tmux, logger)

    # Should send 2 separate messages
    assert mock_tmux.send_message.call_count == 2, f"Expected 2 calls, got {mock_tmux.send_message.call_count}"

    print(f"✅ Successfully handled {len(pm_notifications)} different PMs")


def main():
    """Run all notification batching tests."""
    print("🚀 Starting Notification Batching Test Suite")
    print("=" * 50)

    try:
        # Run tests
        test_notification_collection()
        test_notification_consolidation()
        test_consolidated_message_format()
        test_multiple_pms()

        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("✅ Notification batching is working correctly")
        print("✅ Multiple notifications are collected and consolidated")
        print("✅ Consolidated reports are properly formatted")
        print("✅ Multiple PMs are handled correctly")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    main()
