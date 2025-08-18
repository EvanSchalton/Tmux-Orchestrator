"""Asynchronous monitoring implementation for improved scalability.

This module provides async versions of the monitoring functions to address
the critical scalability bottlenecks in the sequential monitoring approach.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from tmux_orchestrator.core.monitor_helpers import (
    AgentState,
    detect_claude_state,
    is_claude_interface_present,
)
from tmux_orchestrator.utils.tmux import TMUXManager


class AsyncAgentMonitor:
    """Asynchronous agent monitoring for improved scalability."""

    def __init__(self, tmux: TMUXManager, max_concurrent_checks: int = 10):
        self.tmux = tmux
        self.max_concurrent_checks = max_concurrent_checks
        self.logger = logging.getLogger("async_agent_monitor")

        # Use semaphore to limit concurrent tmux operations
        self.tmux_semaphore = asyncio.Semaphore(max_concurrent_checks)

    async def capture_pane_async(self, target: str, lines: int = 50) -> str:
        """Async wrapper for tmux pane capture with concurrency control."""
        async with self.tmux_semaphore:
            # Run tmux command in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.tmux.capture_pane, target, lines)

    async def take_snapshots_async(self, target: str, count: int = 4, interval: float = 0.3) -> list[str]:
        """Take multiple snapshots concurrently for activity detection."""
        snapshots = []

        # Take snapshots with async delays
        for i in range(count):
            content = await self.capture_pane_async(target, lines=50)
            snapshots.append(content)

            # Non-blocking sleep between snapshots
            if i < count - 1:
                await asyncio.sleep(interval)

        return snapshots

    async def detect_agent_activity_async(self, target: str) -> tuple[bool, str]:
        """Detect if agent is active using async snapshot comparison."""
        try:
            # Take snapshots asynchronously
            snapshots = await self.take_snapshots_async(target)

            # Use last snapshot for state detection
            current_content = snapshots[-1]

            # Detect changes between snapshots
            is_active = False
            for i in range(1, len(snapshots)):
                if snapshots[i - 1] != snapshots[i]:
                    # Check if change is meaningful (not just cursor blink)
                    changes = sum(1 for a, b in zip(snapshots[i - 1], snapshots[i]) if a != b)
                    if changes > 1:
                        is_active = True
                        break

            # Additional activity checks
            if not is_active:
                content_lower = current_content.lower()

                # Check for compaction or processing indicators
                if "compacting conversation" in content_lower:
                    is_active = True
                elif "…" in current_content and any(
                    word in content_lower for word in ["thinking", "pondering", "divining", "musing", "elucidating"]
                ):
                    is_active = True

            return is_active, current_content

        except Exception as e:
            self.logger.error(f"Error detecting activity for {target}: {e}")
            return False, ""

    async def check_agent_status_async(self, target: str) -> dict[str, Any]:
        """Asynchronously check agent status and return structured result."""
        try:
            # Get activity status and content
            is_active, content = await self.detect_agent_activity_async(target)

            # Check Claude interface presence
            has_claude_interface = is_claude_interface_present(content)

            # Determine agent state
            if not has_claude_interface:
                # Check for crash indicators
                lines = content.strip().split("\n")
                last_few_lines = [line for line in lines[-5:] if line.strip()]

                # Check for bash prompt (crashed)
                for line in last_few_lines:
                    if line.strip().endswith(("$", "#", ">", "%")):
                        return {
                            "target": target,
                            "state": AgentState.CRASHED,
                            "is_active": False,
                            "content": content,
                            "needs_restart": True,
                            "timestamp": datetime.now(),
                        }

                # Otherwise error state
                return {
                    "target": target,
                    "state": AgentState.ERROR,
                    "is_active": False,
                    "content": content,
                    "needs_recovery": True,
                    "timestamp": datetime.now(),
                }

            # Check Claude state
            claude_state = detect_claude_state(content)

            if claude_state == "fresh":
                return {
                    "target": target,
                    "state": AgentState.FRESH,
                    "is_active": False,
                    "content": content,
                    "needs_briefing": True,
                    "timestamp": datetime.now(),
                }
            elif claude_state == "unsubmitted":
                return {
                    "target": target,
                    "state": AgentState.MESSAGE_QUEUED,
                    "is_active": False,
                    "content": content,
                    "needs_submission": True,
                    "timestamp": datetime.now(),
                }

            # Determine if idle or active
            if is_active:
                return {
                    "target": target,
                    "state": AgentState.ACTIVE,
                    "is_active": True,
                    "content": content,
                    "timestamp": datetime.now(),
                }
            else:
                return {
                    "target": target,
                    "state": AgentState.IDLE,
                    "is_active": False,
                    "content": content,
                    "needs_task": True,
                    "timestamp": datetime.now(),
                }

        except Exception as e:
            self.logger.error(f"Error checking status for {target}: {e}")
            return {
                "target": target,
                "state": AgentState.ERROR,
                "is_active": False,
                "content": "",
                "error": str(e),
                "timestamp": datetime.now(),
            }

    async def monitor_agents_batch(self, agents: list[str]) -> dict[str, dict[str, Any]]:
        """Monitor multiple agents concurrently."""
        if not agents:
            return {}

        self.logger.info(f"Starting async monitoring of {len(agents)} agents")
        start_time = time.time()

        try:
            # Create tasks for concurrent execution
            tasks = [self.check_agent_status_async(agent) for agent in agents]

            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            agent_statuses: dict[str, dict[str, Any]] = {}
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Error monitoring agent {agents[i]}: {result}")
                    agent_statuses[agents[i]] = {
                        "target": agents[i],
                        "state": AgentState.ERROR,
                        "is_active": False,
                        "content": "",
                        "error": str(result),
                        "timestamp": datetime.now(),
                    }
                elif isinstance(result, dict):
                    agent_statuses[agents[i]] = result

            elapsed = time.time() - start_time
            self.logger.info(
                f"Completed async monitoring of {len(agents)} agents in {elapsed:.2f}s "
                f"(avg {elapsed/len(agents):.2f}s per agent)"
            )

            return agent_statuses

        except Exception as e:
            self.logger.error(f"Error in batch monitoring: {e}")
            return {}

    async def get_agent_notifications(self, agent_statuses: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
        """Generate notifications based on agent statuses."""
        notifications: dict[str, list[str]] = {}

        for target, status in agent_statuses.items():
            session_name = target.split(":")[0]

            # Initialize session notifications if needed
            if session_name not in notifications:
                notifications[session_name] = []

            # Generate appropriate notifications
            state = status.get("state")
            timestamp_obj = status.get("timestamp", datetime.now())
            timestamp = timestamp_obj.strftime("%H:%M:%S") if hasattr(timestamp_obj, "strftime") else str(timestamp_obj)

            if state == AgentState.CRASHED:
                notifications[session_name].append(f"🚨 CRASHED: {target} needs restart [{timestamp}]")
            elif state == AgentState.FRESH:
                notifications[session_name].append(f"🆕 FRESH: {target} needs briefing [{timestamp}]")
            elif state == AgentState.IDLE:
                notifications[session_name].append(f"⚠️ IDLE: {target} needs task assignment [{timestamp}]")
            elif state == AgentState.MESSAGE_QUEUED:
                notifications[session_name].append(f"📝 QUEUED: {target} has unsubmitted message [{timestamp}]")
            elif state == AgentState.ERROR:
                notifications[session_name].append(f"🔴 ERROR: {target} needs recovery [{timestamp}]")

        return notifications


# Performance comparison function
async def compare_monitoring_performance(agents: list[str], tmux: TMUXManager) -> dict[str, float]:
    """Compare performance between sync and async monitoring approaches."""

    # Test async monitoring
    async_monitor = AsyncAgentMonitor(tmux)

    start_time = time.time()
    await async_monitor.monitor_agents_batch(agents)
    async_duration = time.time() - start_time

    # Calculate theoretical sync duration
    # Based on analysis: 1.2s per agent + notification overhead
    sync_duration_estimate = len(agents) * 1.2

    return {
        "agents_monitored": len(agents),
        "async_duration": async_duration,
        "sync_duration_estimate": sync_duration_estimate,
        "performance_improvement": sync_duration_estimate / async_duration if async_duration > 0 else 0,
        "avg_per_agent_async": async_duration / len(agents) if agents else 0,
        "avg_per_agent_sync_estimate": 1.2,
    }
