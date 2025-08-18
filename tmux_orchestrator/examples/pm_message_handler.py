#!/usr/bin/env python3
"""Example PM message handler using the new structured messaging protocol.

This script demonstrates how a PM can consume and respond to daemon notifications
through the enhanced pubsub system.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tmux_orchestrator.core.communication.pm_pubsub_integration import PMPubsubIntegration


async def main():
    """Main PM message handling loop."""
    # Initialize PM pubsub integration
    # In real usage, PM would get its session ID from tmux
    pm_session = "example-project:1"  # Example PM session
    pm_integration = PMPubsubIntegration(pm_session)

    print(f"PM Message Handler Started for session: {pm_session}")
    print("=" * 60)

    while True:
        try:
            # Process structured messages from the last 5 minutes
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking for new messages...")

            messages = await pm_integration.process_structured_messages(since_minutes=5)

            # Handle health notifications
            if messages["health"]:
                print(f"\n📋 Health Notifications: {len(messages['health'])}")
                for msg in messages["health"]:
                    print(f"  - Processing: {msg['message']['content']['subject']}")
                    result = await pm_integration.handle_health_notification(msg)
                    print(f"    Action: {result['action_taken']} - {result['result']['status']}")

            # Handle recovery notifications
            if messages["recovery"]:
                print(f"\n🔧 Recovery Notifications: {len(messages['recovery'])}")
                for msg in messages["recovery"]:
                    print(f"  - Processing: {msg['message']['content']['subject']}")
                    result = await pm_integration.handle_recovery_notification(msg)
                    print(f"    Verification: {result['verification']['status']}")

            # Handle action requests
            if messages["requests"]:
                print(f"\n📢 Action Requests: {len(messages['requests'])}")
                for msg in messages["requests"]:
                    print(f"  - Processing: {msg['message']['content']['subject']}")
                    result = await pm_integration.handle_action_request(msg)
                    print(f"    Result: {result['result']['status']}")

            # Show unacknowledged messages
            if messages["unacknowledged"]:
                print(f"\n⚠️  Unacknowledged Messages: {len(messages['unacknowledged'])}")
                for msg in messages["unacknowledged"]:
                    print(f"  - {msg['message']['content']['subject']} (ID: {msg['id']})")

            # Show status updates
            if messages["status"]:
                print(f"\n📊 Status Updates: {len(messages['status'])}")
                for msg in messages["status"]:
                    print(f"  - {msg['message']['content']['subject']}")

            # Sleep for 30 seconds before next check
            await asyncio.sleep(30)

        except KeyboardInterrupt:
            print("\n\nShutting down PM message handler...")
            break
        except Exception as e:
            print(f"\n❌ Error processing messages: {e}")
            await asyncio.sleep(10)  # Brief pause before retry


if __name__ == "__main__":
    asyncio.run(main())
