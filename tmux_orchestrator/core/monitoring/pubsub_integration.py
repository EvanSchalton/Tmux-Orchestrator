"""
Pubsub integration utilities for monitoring system.

Provides high-performance messaging capabilities to replace direct tmux commands
with daemon-based pubsub for sub-100ms delivery.
"""

import asyncio
import logging
import subprocess
from typing import Dict, List, Optional, Tuple

from tmux_orchestrator.core.messaging_daemon import DaemonClient


class MonitorPubsubClient:
    """High-performance pubsub client for monitoring system."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the pubsub client."""
        self.logger = logger or logging.getLogger(__name__)
        self._daemon_client = DaemonClient()
        self._cli_fallback = True  # Use CLI as fallback if daemon fails
        self._performance_metrics: Dict[str, List[float]] = {
            "daemon_times": [],
            "cli_times": [],
        }

    async def publish_notification(
        self,
        target: str,
        message: str,
        priority: str = "normal",
        tags: Optional[List[str]] = None,
    ) -> Tuple[bool, float]:
        """
        Publish notification with performance tracking.
        
        Args:
            target: Target session:window
            message: Message content
            priority: Message priority (low, normal, high, critical)
            tags: Optional message tags
            
        Returns:
            Tuple of (success, delivery_time_ms)
        """
        if tags is None:
            tags = ["monitoring"]

        start_time = asyncio.get_event_loop().time()
        success = False

        try:
            # Try daemon first for performance
            response = await self._daemon_client.publish(target, message, priority, tags)
            success = response.get("status") == "queued"
            
            if not success and self._cli_fallback:
                # Fallback to CLI if daemon fails
                success = await self._publish_via_cli(target, message, priority, tags)
                
        except Exception as e:
            self.logger.warning(f"Daemon publish failed: {e}")
            if self._cli_fallback:
                success = await self._publish_via_cli(target, message, priority, tags)

        end_time = asyncio.get_event_loop().time()
        delivery_time_ms = (end_time - start_time) * 1000

        # Track performance
        if success:
            metric_key = "daemon_times" if not self._cli_fallback else "cli_times"
            self._performance_metrics[metric_key].append(delivery_time_ms)

        # Log performance warning if exceeding target
        if delivery_time_ms > 100:
            self.logger.warning(
                f"Message delivery exceeded 100ms target: {delivery_time_ms:.1f}ms "
                f"(method: {'daemon' if not self._cli_fallback else 'cli'})"
            )

        return success, delivery_time_ms

    async def _publish_via_cli(
        self,
        target: str,
        message: str,
        priority: str,
        tags: List[str],
    ) -> bool:
        """Fallback to CLI-based publish."""
        try:
            cmd = [
                "tmux-orc",
                "pubsub",
                "publish",
                "--target",
                target,
                "--priority",
                priority,
            ]
            
            # Add tags
            for tag in tags:
                cmd.extend(["--tag", tag])
                
            cmd.append(message)

            # Run command
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            await result.wait()
            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"CLI publish failed: {e}")
            return False

    async def batch_publish(
        self,
        notifications: List[Dict[str, any]],
    ) -> Dict[str, any]:
        """
        Publish multiple notifications in batch for efficiency.
        
        Args:
            notifications: List of notification dicts with keys:
                - target: Target session:window
                - message: Message content
                - priority: Message priority (optional)
                - tags: Message tags (optional)
                
        Returns:
            Dict with batch statistics
        """
        results = {
            "total": len(notifications),
            "success": 0,
            "failed": 0,
            "total_time_ms": 0,
            "avg_time_ms": 0,
        }

        start_time = asyncio.get_event_loop().time()

        # Process notifications concurrently for performance
        tasks = []
        for notif in notifications:
            task = self.publish_notification(
                target=notif["target"],
                message=notif["message"],
                priority=notif.get("priority", "normal"),
                tags=notif.get("tags"),
            )
            tasks.append(task)

        # Execute all tasks concurrently
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in task_results:
            if isinstance(result, Exception):
                results["failed"] += 1
                self.logger.error(f"Batch publish error: {result}")
            else:
                success, _ = result
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1

        end_time = asyncio.get_event_loop().time()
        results["total_time_ms"] = (end_time - start_time) * 1000
        results["avg_time_ms"] = results["total_time_ms"] / len(notifications) if notifications else 0

        return results

    def get_performance_stats(self) -> Dict[str, any]:
        """Get performance statistics for monitoring."""
        stats = {
            "daemon": self._calculate_stats(self._performance_metrics["daemon_times"]),
            "cli": self._calculate_stats(self._performance_metrics["cli_times"]),
        }

        # Overall performance
        all_times = (
            self._performance_metrics["daemon_times"] +
            self._performance_metrics["cli_times"]
        )
        stats["overall"] = self._calculate_stats(all_times)
        stats["meeting_target"] = all(t < 100 for t in all_times[-100:])  # Last 100 messages

        return stats

    def _calculate_stats(self, times: List[float]) -> Dict[str, float]:
        """Calculate performance statistics."""
        if not times:
            return {
                "count": 0,
                "min": 0,
                "max": 0,
                "avg": 0,
                "p95": 0,
            }

        sorted_times = sorted(times)
        count = len(sorted_times)
        
        return {
            "count": count,
            "min": sorted_times[0],
            "max": sorted_times[-1],
            "avg": sum(sorted_times) / count,
            "p95": sorted_times[int(count * 0.95)] if count > 1 else sorted_times[0],
        }


class PriorityMessageRouter:
    """Routes messages based on priority for optimal delivery."""

    # Priority to delivery method mapping
    PRIORITY_ROUTES = {
        "critical": {"method": "daemon", "retry": True, "timeout": 50},
        "high": {"method": "daemon", "retry": True, "timeout": 75},
        "normal": {"method": "daemon", "retry": False, "timeout": 100},
        "low": {"method": "batch", "retry": False, "timeout": 500},
    }

    def __init__(self, pubsub_client: MonitorPubsubClient):
        """Initialize the priority router."""
        self.client = pubsub_client
        self.logger = logging.getLogger(__name__)
        self._batch_queue: Dict[str, List[Dict]] = {
            "low": [],
        }

    async def route_message(
        self,
        target: str,
        message: str,
        priority: str = "normal",
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Route message based on priority."""
        route = self.PRIORITY_ROUTES.get(priority, self.PRIORITY_ROUTES["normal"])

        if route["method"] == "batch" and priority == "low":
            # Queue low priority for batch processing
            self._batch_queue["low"].append({
                "target": target,
                "message": message,
                "priority": priority,
                "tags": tags or [],
            })
            
            # Process batch if queue is large enough
            if len(self._batch_queue["low"]) >= 10:
                await self.flush_batch_queue()
                
            return True

        else:
            # Direct send for higher priorities
            success, delivery_time = await self.client.publish_notification(
                target, message, priority, tags
            )

            # Retry critical/high priority if failed and under timeout
            if not success and route["retry"] and delivery_time < route["timeout"]:
                self.logger.info(f"Retrying {priority} priority message")
                success, _ = await self.client.publish_notification(
                    target, message, priority, tags
                )

            return success

    async def flush_batch_queue(self) -> Dict[str, int]:
        """Flush all batched messages."""
        flushed = {"low": 0}

        if self._batch_queue["low"]:
            batch_result = await self.client.batch_publish(self._batch_queue["low"])
            flushed["low"] = batch_result["success"]
            self._batch_queue["low"].clear()

        return flushed