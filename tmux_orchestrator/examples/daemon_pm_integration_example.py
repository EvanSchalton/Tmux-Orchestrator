#!/usr/bin/env python3
"""
Complete Integration Example: Daemon-PM Pubsub Coordination

This example demonstrates the full flow of:
1. Daemon detecting a critical agent crash
2. Publishing structured notification via pubsub
3. PM receiving and automatically handling the issue
4. Acknowledgment flowing back to daemon

Usage:
    python daemon_pm_integration_example.py
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tmux_orchestrator.core.monitoring.daemon_pubsub_integration import (
    DaemonPubsubIntegration, MessagePriority
)
from tmux_orchestrator.core.communication.pm_pubsub_integration import PMPubsubIntegration


# ============================================================================
# DAEMON SIDE: Detecting and Publishing Critical Notifications
# ============================================================================

async def daemon_detect_and_notify():
    """Simulates daemon detecting agent crash and sending notification."""
    print("🔍 DAEMON: Checking agent health...")
    
    # Initialize daemon pubsub integration
    daemon_pubsub = DaemonPubsubIntegration()
    
    # Simulate detecting a crashed agent
    agent_target = "backend-dev:2"
    print(f"❌ DAEMON: Detected crash - {agent_target} not responding!")
    
    # Send critical health alert
    success = await daemon_pubsub.send_health_alert(
        agent_target=agent_target,
        issue_type="crashed",
        details={
            "crash_detected_at": datetime.now().isoformat(),
            "last_known_state": "processing_api_endpoint_handler",
            "error_pattern": "Claude interface not responding",
            "last_heartbeat": "300_seconds_ago",
            "memory_usage": "85%",
            "cpu_usage": "2%"
        },
        priority=MessagePriority.CRITICAL
    )
    
    if success:
        print("✅ DAEMON: Critical notification published to pubsub")
        return True
    else:
        print("❌ DAEMON: Failed to publish notification")
        return False


# ============================================================================
# PM SIDE: Receiving and Handling Notifications
# ============================================================================

async def pm_monitor_and_respond():
    """Simulates PM monitoring for daemon notifications and taking action."""
    print("\n📊 PM: Monitoring daemon notifications...")
    
    # Initialize PM pubsub integration
    pm_pubsub = PMPubsubIntegration("backend-dev:1")
    
    # Process recent messages (last 1 minute for demo)
    messages = await pm_pubsub.process_structured_messages(since_minutes=1)
    
    print(f"📬 PM: Found {len(messages['health'])} health notifications")
    
    # Handle each health notification
    for msg in messages["health"]:
        priority = msg["message"]["priority"]
        subject = msg["message"]["content"]["subject"]
        
        print(f"\n{'🚨' if priority == 'critical' else '⚠️'} PM: Received {priority.upper()} notification")
        print(f"   Subject: {subject}")
        print(f"   Context: {json.dumps(msg['message']['content']['context'], indent=4)}")
        
        # Automatically handle the notification
        print(f"\n🔧 PM: Taking action...")
        result = await pm_pubsub.handle_health_notification(msg)
        
        # Display results
        print(f"\n✅ PM: Action completed!")
        print(f"   Message ID: {result['message_id']}")
        print(f"   Agent: {result['agent']}")
        print(f"   Issue: {result['issue']}")
        print(f"   Action Taken: {result['action_taken']}")
        print(f"   Result: {result['result']}")
        
        # Show acknowledgment that was sent
        if msg["metadata"].get("requires_ack"):
            print(f"\n📮 PM: Acknowledgment sent to daemon")
            print(f"   Correlation ID: {msg['id']}")


# ============================================================================
# COMPLETE FLOW: Daemon → Pubsub → PM → Action → Acknowledgment
# ============================================================================

async def demonstrate_complete_flow():
    """Demonstrates the complete integration flow."""
    print("=" * 70)
    print("DAEMON-PM PUBSUB INTEGRATION EXAMPLE")
    print("Critical Agent-Down Notification Flow")
    print("=" * 70)
    
    # Step 1: Daemon detects and publishes
    print("\n[STEP 1: DAEMON DETECTION]")
    daemon_success = await daemon_detect_and_notify()
    
    if not daemon_success:
        print("\n❌ Demo failed: Could not publish notification")
        return
    
    # Small delay to simulate message propagation
    print("\n⏳ Simulating message propagation...")
    await asyncio.sleep(1)
    
    # Step 2: PM receives and handles
    print("\n[STEP 2: PM HANDLING]")
    await pm_monitor_and_respond()
    
    # Summary
    print("\n" + "=" * 70)
    print("FLOW SUMMARY:")
    print("1. ✅ Daemon detected crashed agent")
    print("2. ✅ Published critical notification via pubsub")
    print("3. ✅ PM received structured message")
    print("4. ✅ PM automatically took corrective action")
    print("5. ✅ PM sent acknowledgment back to daemon")
    print("=" * 70)


# ============================================================================
# ADDITIONAL EXAMPLES: Different Notification Types
# ============================================================================

async def example_idle_agent_notification():
    """Example of high-priority idle agent notification."""
    daemon_pubsub = DaemonPubsubIntegration()
    
    await daemon_pubsub.send_health_alert(
        agent_target="frontend-dev:3",
        issue_type="idle",
        details={
            "idle_duration": 1800,  # 30 minutes
            "last_activity": "2025-08-17T10:00:00Z",
            "assigned_tasks": 3,
            "completion_rate": "0%"
        },
        priority=MessagePriority.HIGH
    )
    print("📤 Sent idle agent notification")


async def example_recovery_notification():
    """Example of PM crash recovery notification."""
    daemon_pubsub = DaemonPubsubIntegration()
    
    await daemon_pubsub.send_recovery_notification(
        target="project-x:1",
        recovery_type="pm_crash",
        recovery_details={
            "crashed_at": "2025-08-17T10:25:00Z",
            "new_pm_spawned": "project-x:1",
            "team_size": 4,
            "agents_notified": ["backend:2", "frontend:3", "qa:4", "devops:5"]
        }
    )
    print("📤 Sent PM recovery notification")


async def example_status_update():
    """Example of routine status update."""
    daemon_pubsub = DaemonPubsubIntegration()
    
    await daemon_pubsub.send_status_update(
        session="project-x",
        status_type="team_health",
        status_data={
            "active_agents": 3,
            "idle_agents": 1,
            "total_agents": 4,
            "monitoring_cycles": 150,
            "issues_detected": 2,
            "issues_resolved": 2
        }
    )
    print("📤 Sent team status update")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function."""
    # Run the complete flow demonstration
    await demonstrate_complete_flow()
    
    # Uncomment to test other notification types
    # print("\n\n[ADDITIONAL EXAMPLES]")
    # await example_idle_agent_notification()
    # await example_recovery_notification()
    # await example_status_update()


if __name__ == "__main__":
    # Note: In production, the daemon and PM would run in separate processes
    # This example combines them for demonstration purposes
    asyncio.run(main())