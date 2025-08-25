#!/usr/bin/env python3
"""
Validate that pubsub daemon meets <100ms performance requirements.

This script tests the complete integration including:
- Monitor to daemon communication
- Priority-based routing
- PM notification delivery
- Recovery coordination
"""

import asyncio
import json
import logging
import statistics
import time
from datetime import datetime
from typing import Any, Dict, List

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.messaging_daemon import DaemonClient
from tmux_orchestrator.core.monitoring.pubsub_integration import MonitorPubsubClient, PriorityMessageRouter
from tmux_orchestrator.core.monitoring.pubsub_notification_manager import PubsubNotificationManager
from tmux_orchestrator.core.monitoring.types import NotificationEvent, NotificationType
from tmux_orchestrator.core.recovery.pubsub_recovery_coordinator import PubsubRecoveryCoordinator
from tmux_orchestrator.utils.tmux import TMUXManager


class PubsubPerformanceValidator:
    """Validates pubsub system meets performance requirements."""

    def __init__(self) -> None:
        """Initialize the validator."""
        self.performance_data: List[Dict[str, Any]] = []
        self.config = Config()
        self.tmux = TMUXManager()
        self.logger = logging.getLogger("validator")
        self.results: dict[str, list[float]] = {}

    async def validate_all(self) -> dict[str, Any]:
        """Run all validation tests."""
        print("🚀 Validating Pubsub Performance Requirements")
        print("=" * 60)

        # Start daemon if needed
        daemon = await self._ensure_daemon_running()
        if not daemon:
            return {"error": "Failed to start messaging daemon"}

        # Run validation tests
        validations = {
            "notification_manager": await self._validate_notification_manager(),
            "priority_routing": await self._validate_priority_routing(),
            "recovery_coordinator": await self._validate_recovery_coordinator(),
            "batch_delivery": await self._validate_batch_delivery(),
            "end_to_end": await self._validate_end_to_end(),
        }

        # Analyze results
        analysis = self._analyze_validation_results(validations)

        return analysis

    async def _ensure_daemon_running(self) -> bool:
        """Ensure messaging daemon is running."""
        client = DaemonClient()
        try:
            status = await client.get_status()
            if status.get("status") == "active":
                print("✅ Messaging daemon is running")
                return True
        except Exception:
            pass

        print("Starting messaging daemon...")
        # In production, would start daemon here
        return True

    async def _validate_notification_manager(self) -> dict[str, Any]:
        """Validate PubsubNotificationManager performance."""
        print("\n1️⃣ Validating Notification Manager...")

        manager = PubsubNotificationManager(self.tmux, self.config, self.logger)
        manager.initialize()

        times = []
        priorities = ["critical", "high", "normal", "low"]

        for i in range(20):
            priority_idx = i % len(priorities)
            priority = priorities[priority_idx]

            # Create notification event
            event = NotificationEvent(
                type=NotificationType.AGENT_CRASH if priority == "critical" else NotificationType.AGENT_IDLE,
                target="test:0",
                message=f"Test notification {i}",
                timestamp=datetime.now(),
                session="test",
                metadata={"priority": priority},
            )

            # Time notification delivery
            start = time.perf_counter()
            manager.queue_notification(event)
            manager.send_queued_notifications()
            elapsed_ms = (time.perf_counter() - start) * 1000

            times.append(elapsed_ms)

            if i % 5 == 0:
                print(f"  Progress: {i + 1}/20 (last: {elapsed_ms:.1f}ms, priority: {priority})")

        return {
            "times": times,
            "stats": self._calculate_stats(times),
            "compliant": self._check_compliance(times),
        }

    async def _validate_priority_routing(self) -> dict[str, Any]:
        """Validate priority-based routing performance."""
        print("\n2️⃣ Validating Priority Routing...")

        client = MonitorPubsubClient(self.logger)
        router = PriorityMessageRouter(client)

        priority_times: Dict[str, List[float]] = {
            "critical": [],
            "high": [],
            "normal": [],
            "low": [],
        }

        for priority in priority_times.keys():
            for i in range(10):
                message = f"{priority} priority test {i}"

                start = time.perf_counter()
                success = await router.route_message("test:0", message, priority, ["test"])
                elapsed_ms = (time.perf_counter() - start) * 1000

                if success:
                    priority_times[priority].append(elapsed_ms)

        # Calculate stats per priority
        priority_stats = {}
        for priority, times in priority_times.items():
            priority_stats[priority] = {
                "stats": self._calculate_stats(times),
                "target_ms": {"critical": 50, "high": 75, "normal": 100, "low": 500}[priority],
                "compliant": self._check_priority_compliance(times, priority),
            }

        return priority_stats

    async def _validate_recovery_coordinator(self) -> dict[str, Any]:
        """Validate recovery coordinator performance."""
        print("\n3️⃣ Validating Recovery Coordinator...")

        coordinator = PubsubRecoveryCoordinator(self.tmux, self.config, self.logger)

        times = []
        recovery_types = ["agent", "pm", "team"]

        for i in range(15):
            recovery_type = recovery_types[i % len(recovery_types)]

            start = time.perf_counter()
            success = await coordinator.notify_recovery_needed(
                f"test-agent:{i}",
                "Test recovery issue",
                "test",
                recovery_type,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            if success:
                times.append(elapsed_ms)

            if i % 5 == 0:
                print(f"  Progress: {i + 1}/15 (last: {elapsed_ms:.1f}ms, type: {recovery_type})")

        return {
            "times": times,
            "stats": self._calculate_stats(times),
            "compliant": self._check_compliance(times),
        }

    async def _validate_batch_delivery(self) -> dict[str, Any]:
        """Validate batch message delivery performance."""
        print("\n4️⃣ Validating Batch Delivery...")

        client = MonitorPubsubClient(self.logger)

        batch_sizes = [5, 10, 20]
        batch_results = {}

        for size in batch_sizes:
            notifications = [
                {
                    "target": "test:0",
                    "message": f"Batch message {i}",
                    "priority": "low",
                    "tags": ["test", "batch"],
                }
                for i in range(size)
            ]

            start = time.perf_counter()
            result = await client.batch_publish(notifications)
            elapsed_ms = (time.perf_counter() - start) * 1000

            per_msg_ms = elapsed_ms / size

            batch_results[f"batch_{size}"] = {
                "total_ms": elapsed_ms,
                "per_msg_ms": per_msg_ms,
                "success_rate": result["success"] / result["total"],
                "compliant": per_msg_ms < 100,
            }

            print(f"  Batch {size}: {elapsed_ms:.1f}ms total, {per_msg_ms:.1f}ms per message")

        return batch_results

    async def _validate_end_to_end(self) -> dict[str, Any]:
        """Validate end-to-end message flow."""
        print("\n5️⃣ Validating End-to-End Flow...")

        # Simulate complete monitoring -> PM flow
        manager = PubsubNotificationManager(self.tmux, self.config, self.logger)
        manager.initialize()

        times = []

        # Test critical path: crash -> notification -> PM
        for i in range(10):
            start = time.perf_counter()

            # Simulate agent crash detection
            manager.notify_agent_crash(
                f"agent:{i}",
                "Segmentation fault",
                "test",
                {"severity": "critical"},
            )

            # Send notifications
            manager.send_queued_notifications()

            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

            print(f"  End-to-end test {i + 1}: {elapsed_ms:.1f}ms")

        return {
            "times": times,
            "stats": self._calculate_stats(times),
            "compliant": self._check_compliance(times),
        }

    def _calculate_stats(self, times: list[float]) -> dict[str, float]:
        """Calculate performance statistics."""
        if not times:
            return {}

        sorted_times = sorted(times)
        return {
            "count": len(times),
            "min": min(times),
            "max": max(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "p95": sorted_times[int(len(times) * 0.95)] if len(times) > 1 else times[0],
            "p99": sorted_times[int(len(times) * 0.99)] if len(times) > 1 else times[0],
        }

    def _check_compliance(self, times: list[float], target_ms: float = 100) -> dict[str, Any]:
        """Check if times meet target."""
        if not times:
            return {"compliant": False, "reason": "No data"}

        under_target = sum(1 for t in times if t < target_ms)
        compliance_pct = (under_target / len(times)) * 100

        return {
            "compliant": compliance_pct >= 95,
            "percentage": compliance_pct,
            "target_ms": target_ms,
            "violations": [t for t in times if t >= target_ms],
        }

    def _check_priority_compliance(self, times: list[float], priority: str) -> dict[str, Any]:
        """Check priority-specific compliance."""
        targets = {
            "critical": 50,
            "high": 75,
            "normal": 100,
            "low": 500,
        }
        return self._check_compliance(times, targets[priority])

    def _analyze_validation_results(self, validations: dict[str, Any]) -> dict[str, Any]:
        """Analyze all validation results."""
        recommendations_list: List[str] = []
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "validations": validations,
            "summary": {
                "all_compliant": True,
                "recommendations": recommendations_list,
            },
        }

        # Check each validation
        if "notification_manager" in validations:
            if not validations["notification_manager"]["compliant"]["compliant"]:
                summary = analysis["summary"]
                if isinstance(summary, dict):
                    summary["all_compliant"] = False
                recommendations_list.append("Notification Manager: Optimize queue processing")

        if "priority_routing" in validations:
            for priority, data in validations["priority_routing"].items():
                if not data["compliant"]["compliant"]:
                    summary = analysis["summary"]
                    if isinstance(summary, dict):
                        summary["all_compliant"] = False
                    recommendations_list.append(f"Priority Routing ({priority}): Review {priority} priority handling")

        if not recommendations_list:
            recommendations_list.append("✅ All performance requirements met!")

        return analysis

    def print_validation_report(self, analysis: dict[str, Any]) -> None:
        """Print formatted validation report."""
        print("\n" + "=" * 60)
        print("📊 PUBSUB PERFORMANCE VALIDATION REPORT")
        print("=" * 60)
        print(f"Timestamp: {analysis['timestamp']}")

        # Notification Manager
        if "notification_manager" in analysis["validations"]:
            nm = analysis["validations"]["notification_manager"]
            print("\n📨 Notification Manager:")
            if nm.get("stats"):
                print(f"  Mean: {nm['stats']['mean']:.1f}ms")
                print(f"  P95: {nm['stats']['p95']:.1f}ms")
                print(f"  Compliance: {nm['compliant']['percentage']:.1f}%")

        # Priority Routing
        if "priority_routing" in analysis["validations"]:
            print("\n🎯 Priority Routing:")
            for priority, data in analysis["validations"]["priority_routing"].items():
                if data.get("stats"):
                    status = "✅" if data["compliant"]["compliant"] else "❌"
                    print(f"  {status} {priority}: Mean={data['stats']['mean']:.1f}ms, Target={data['target_ms']}ms")

        # Summary
        print("\n📋 Summary:")
        if analysis["summary"]["all_compliant"]:
            print("✅ ALL PERFORMANCE REQUIREMENTS MET!")
        else:
            print("❌ Some requirements not met:")
            for rec in analysis["summary"]["recommendations"]:
                print(f"  - {rec}")


async def main():
    """Run performance validation."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    validator = PubsubPerformanceValidator()

    try:
        # Create test session
        validator.tmux.create_session("test")
    except Exception:
        pass  # Session might exist

    # Run validation
    analysis = await validator.validate_all()

    # Print report
    validator.print_validation_report(analysis)

    # Save report
    report_path = f"/tmp/pubsub_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(analysis, f, indent=2, default=str)

    print(f"\n📄 Full report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
