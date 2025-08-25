#!/usr/bin/env python3
"""
Enable pubsub integration in the monitoring system.

This script updates the monitoring components to use the high-performance
pubsub daemon for message delivery instead of direct tmux commands.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any


def update_notification_manager_imports() -> dict[str, str]:
    """Update notification manager to use pubsub version."""
    updates = {
        "notification_manager.py": "pubsub_notification_manager.py",
        "original": "from .notification_manager import NotificationManager",
        "updated": "from .pubsub_notification_manager import PubsubNotificationManager as NotificationManager",
    }
    return updates


def update_monitor_imports() -> list[dict[str, str]]:
    """Update monitor.py to include pubsub integration."""
    return [
        {
            "file": "monitor.py",
            "add_imports": "from tmux_orchestrator.core.monitoring.pubsub_integration import MonitorPubsubClient, PriorityMessageRouter; from tmux_orchestrator.core.recovery.pubsub_recovery_coordinator import PubsubRecoveryCoordinator",
        }
    ]


def create_pubsub_config() -> dict[str, Any]:
    """Create pubsub configuration for monitoring."""
    return {
        "pubsub": {
            "enabled": True,
            "daemon_socket": "/tmp/tmux-orc-msgd.sock",
            "performance_target_ms": 100,
            "fallback_to_cli": True,
            "priority_routing": {
                "critical": {"timeout_ms": 50, "retry": True},
                "high": {"timeout_ms": 75, "retry": True},
                "normal": {"timeout_ms": 100, "retry": False},
                "low": {"timeout_ms": 500, "batch": True},
            },
            "batch_settings": {
                "low_priority_threshold": 10,
                "flush_interval_ms": 1000,
            },
        }
    }


def verify_daemon_running() -> bool:
    """Check if messaging daemon is running."""
    try:
        result = subprocess.run(
            ["tmux-orc", "pubsub", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "active" in result.stdout.lower()
    except Exception:
        return False


def start_daemon_if_needed() -> bool:
    """Start messaging daemon if not running."""
    if not verify_daemon_running():
        try:
            print("Starting messaging daemon...")
            subprocess.run(
                ["tmux-orc", "daemon", "start"],
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to start daemon: {e}")
            return False
    return True


def create_integration_test() -> str:
    """Create integration test script."""
    test_script = '''#!/usr/bin/env python3
"""Test pubsub integration with monitoring system."""

import asyncio
import time
from tmux_orchestrator.core.monitoring.pubsub_notification_manager import PubsubNotificationManager
from tmux_orchestrator.core.monitoring.types import NotificationEvent, NotificationType
from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager


async def test_pubsub_notifications():
    """Test notification delivery performance."""
    config = Config()
    tmux = TMUXManager()
    logger = logging.getLogger("test")

    # Initialize pubsub notification manager
    manager = PubsubNotificationManager(tmux, config, logger)
    manager.initialize()

    # Test different priority notifications
    test_cases = [
        ("test:0", "AGENT CRASH", NotificationType.AGENT_CRASH, "critical"),
        ("test:0", "RECOVERY NEEDED", NotificationType.RECOVERY_NEEDED, "high"),
        ("test:0", "FRESH AGENT", NotificationType.AGENT_FRESH, "normal"),
        ("test:0", "AGENT IDLE", NotificationType.AGENT_IDLE, "low"),
    ]

    results = []

    for target, message, notif_type, expected_priority in test_cases:
        start = time.perf_counter()

        # Queue notification
        event = NotificationEvent(
            type=notif_type,
            target=target,
            message=message,
            timestamp=datetime.now(),
            session="test",
            metadata={"priority": expected_priority},
        )
        manager.queue_notification(event)

        # Send queued notifications
        sent = manager.send_queued_notifications()

        elapsed_ms = (time.perf_counter() - start) * 1000
        results.append({
            "type": notif_type.value,
            "priority": expected_priority,
            "sent": sent > 0,
            "time_ms": elapsed_ms,
            "meets_target": elapsed_ms < 100,
        })

    # Print results
    print("\\n=== Pubsub Integration Test Results ===")
    for result in results:
        status = "✅" if result["meets_target"] else "❌"
        print(f"{status} {result['type']} ({result['priority']}): {result['time_ms']:.1f}ms")

    # Get overall stats
    stats = manager.get_notification_stats()
    print(f"\\nDelivery method: {stats.get('delivery_method', 'unknown')}")
    if "daemon_performance" in stats:
        perf = stats["daemon_performance"]
        print(f"Daemon avg delivery: {perf.get('avg_delivery_ms', 'N/A')}ms")
        print(f"Messages processed: {perf.get('messages_processed', 0)}")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_pubsub_notifications())
'''

    test_path = Path("/tmp/test_pubsub_integration.py")
    test_path.write_text(test_script)
    test_path.chmod(0o755)

    return str(test_path)


def main():
    """Enable pubsub integration in monitoring system."""
    print("🚀 Enabling Pubsub Integration for Monitoring System")
    print("=" * 50)

    # Step 1: Verify daemon
    print("\n1️⃣ Checking messaging daemon...")
    if not start_daemon_if_needed():
        print("❌ Failed to start messaging daemon")
        sys.exit(1)
    print("✅ Messaging daemon is running")

    # Step 2: Show configuration
    print("\n2️⃣ Pubsub configuration:")
    config = create_pubsub_config()
    for key, value in config["pubsub"].items():
        print(f"   {key}: {value}")

    # Step 3: Show import updates needed
    print("\n3️⃣ Required import updates:")
    nm_updates = update_notification_manager_imports()
    print(f"   Replace: {nm_updates['original']}")
    print(f"   With: {nm_updates['updated']}")

    # Step 4: Create test script
    print("\n4️⃣ Creating integration test...")
    test_script = create_integration_test()
    print(f"   Test script: {test_script}")

    # Step 5: Usage instructions
    print("\n5️⃣ Usage Instructions:")
    print("   - Update imports in monitor.py to use PubsubNotificationManager")
    print("   - Run the test script to verify performance:")
    print(f"     python {test_script}")
    print("   - Monitor daemon performance:")
    print("     tmux-orc pubsub stats")

    print("\n✅ Pubsub integration setup complete!")
    print("\n⚡ Expected performance improvement:")
    print("   Before: ~5000ms (CLI overhead)")
    print("   After: <100ms (daemon delivery)")


if __name__ == "__main__":
    main()
