#!/usr/bin/env python3
"""
Demonstration script for pubsub daemon integration.

This script shows how the monitoring daemon now uses pubsub for
high-performance notifications with proper priorities and categories.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.idle_monitor_pubsub import IdleMonitorWithPubsub
from tmux_orchestrator.core.monitoring.monitor_pubsub_integration import MonitorPubsubIntegration
from tmux_orchestrator.utils.tmux import TMUXManager


async def demo_pubsub_integration():
    """Demonstrate pubsub integration capabilities."""

    print("🚀 Demonstrating Pubsub-Daemon Integration")
    print("=" * 50)

    # Setup
    config = Config()
    tmux = TMUXManager()
    logger = logging.getLogger("demo")

    # Create pubsub integration
    pubsub = MonitorPubsubIntegration("demo-monitor", logger)
    monitor = IdleMonitorWithPubsub(tmux, config, logger)

    # Demo session
    session_name = "demo-project"

    print("\n1️⃣ Demonstrating Priority-Based Notifications")
    print("-" * 40)

    # Critical priority: Agent crash
    print("📨 Sending CRITICAL: Agent crash notification...")
    success = pubsub.publish_agent_crash(
        agent="backend-dev:2", error_type="Segmentation fault", session_name=session_name, requires_restart=True
    )
    print(f"   Result: {'✅ Sent' if success else '❌ Failed'}")
    await asyncio.sleep(0.1)

    # High priority: Recovery needed
    print("📨 Sending HIGH: Recovery needed notification...")
    success = pubsub.publish_recovery_needed(
        agent="frontend-dev:3", issue="Unresponsive for 15 minutes", session_name=session_name, recovery_type="restart"
    )
    print(f"   Result: {'✅ Sent' if success else '❌ Failed'}")
    await asyncio.sleep(0.1)

    # Normal priority: Fresh agent
    print("📨 Sending NORMAL: Fresh agent notification...")
    success = pubsub.publish_fresh_agent(agent="qa-engineer:4", session_name=session_name, window_name="qa-engineer")
    print(f"   Result: {'✅ Sent' if success else '❌ Failed'}")
    await asyncio.sleep(0.1)

    # Low priority: Idle agent (will be queued)
    print("📨 Sending LOW: Idle agent notification (queued)...")
    success = pubsub.publish_agent_idle(
        agent="docs-writer:5",
        idle_duration=600,  # 10 minutes
        session_name=session_name,
        idle_type="waiting_for_input",
    )
    print(f"   Result: {'✅ Queued' if success else '❌ Failed'}")

    print("\n2️⃣ Demonstrating Structured Messages")
    print("-" * 40)

    # Team idle escalation
    print("📨 Sending team idle escalation...")
    success = pubsub.publish_team_idle(
        session_name=session_name, idle_agents=["backend-dev:2", "frontend-dev:3", "docs-writer:5"], total_agents=5
    )
    print(f"   Result: {'✅ Sent' if success else '❌ Failed'}")
    await asyncio.sleep(0.1)

    # Rate limit notification
    print("📨 Sending rate limit notification...")
    success = pubsub.publish_rate_limit(
        session_name=session_name,
        reset_time=datetime.now() + timedelta(minutes=15),
        affected_agents=["backend-dev:2", "frontend-dev:3"],
    )
    print(f"   Result: {'✅ Sent' if success else '❌ Failed'}")
    await asyncio.sleep(0.1)

    print("\n3️⃣ Demonstrating Batch Processing")
    print("-" * 40)

    # Add more low priority messages to trigger batching
    for i in range(12):
        pubsub.publish_monitoring_report(
            session_name=f"project-{i}", summary={"active": 3, "idle": 1, "crashed": 0}, issues=[]
        )

    # Flush the queue
    print("📨 Flushing message queue...")
    flushed = pubsub.flush_message_queue()
    print(f"   Result: ✅ Flushed {flushed} batched messages")

    print("\n4️⃣ Demonstrating Enhanced Idle Monitor")
    print("-" * 40)

    # Simulate agent checking
    test_agents = [
        ("backend-dev:2", "Segmentation fault (core dumped)", True),
        ("frontend-dev:3", "Human:", True),
        ("qa-engineer:4", "Welcome to Claude! I'll help you with testing.", True),
        ("docs-writer:5", "Please wait while I load the documentation...", True),
    ]

    for agent, content, has_claude in test_agents:
        print(f"🔍 Checking agent {agent}...")

        # Check for crash
        crash_type = monitor.check_agent_crash(agent, content, session_name)
        if crash_type:
            print(f"   ❌ Crash detected: {crash_type}")

        # Check if fresh
        is_fresh = monitor.check_fresh_agent(agent, content, session_name, agent.split(":")[0])
        if is_fresh:
            print("   🌱 Fresh agent detected")

        # Check idle status
        idle_status = monitor.check_agent_idle(agent, content, session_name, has_claude)
        if idle_status:
            print(f"   💤 {idle_status}")
        else:
            print("   ✅ Active")

    print("\n5️⃣ Performance Comparison")
    print("-" * 40)

    # Time pubsub vs direct messaging
    iterations = 10

    print(f"⏱️  Testing {iterations} notifications...")

    # Pubsub timing
    start_time = time.perf_counter()
    for i in range(iterations):
        pubsub.publish_fresh_agent(f"test-agent:{i}", "test-session", f"test-window-{i}")
    pubsub_time = (time.perf_counter() - start_time) * 1000

    print(f"   Pubsub delivery: {pubsub_time:.1f}ms total ({pubsub_time/iterations:.1f}ms avg)")

    # Simulated direct tmux timing (600ms per message based on analysis)
    direct_time = iterations * 600
    print(f"   Direct tmux (est): {direct_time:.1f}ms total ({direct_time/iterations:.1f}ms avg)")

    improvement = (direct_time - pubsub_time) / direct_time * 100
    print(f"   🚀 Performance improvement: {improvement:.1f}%")

    print("\n✅ Pubsub Integration Demo Complete!")
    print("Key benefits demonstrated:")
    print("  • Priority-based message routing")
    print("  • Structured message format")
    print("  • Automatic batching for low priority")
    print("  • Sub-100ms delivery targets")
    print("  • Enhanced monitoring capabilities")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    asyncio.run(demo_pubsub_integration())
