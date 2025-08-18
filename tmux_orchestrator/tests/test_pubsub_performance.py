"""
Performance tests for pubsub daemon integration.

Validates that message delivery meets the <100ms requirement.
"""

import asyncio
import statistics
import time

from tmux_orchestrator.core.messaging_daemon import DaemonClient
from tmux_orchestrator.core.monitoring.pubsub_integration import MonitorPubsubClient, PriorityMessageRouter
from tmux_orchestrator.utils.tmux import TMUXManager


class PubsubPerformanceTester:
    """Test harness for validating pubsub performance requirements."""

    def __init__(self):
        """Initialize the performance tester."""
        self.pubsub_client = MonitorPubsubClient()
        self.priority_router = PriorityMessageRouter(self.pubsub_client)
        self.tmux = TMUXManager()
        self.results: dict[str, list[float]] = {
            "direct_daemon": [],
            "pubsub_client": [],
            "priority_router": [],
            "batch_delivery": [],
        }

    async def run_performance_tests(self, target: str = "test:0", iterations: int = 100) -> dict[str, any]:
        """
        Run comprehensive performance tests.

        Args:
            target: Target window for testing
            iterations: Number of test iterations

        Returns:
            Performance test results
        """
        print(f"🚀 Running performance tests ({iterations} iterations)...")

        # Test 1: Direct daemon performance
        print("\n1️⃣ Testing direct daemon performance...")
        await self._test_direct_daemon(target, iterations)

        # Test 2: Pubsub client performance
        print("\n2️⃣ Testing pubsub client performance...")
        await self._test_pubsub_client(target, iterations)

        # Test 3: Priority router performance
        print("\n3️⃣ Testing priority router performance...")
        await self._test_priority_router(target, iterations)

        # Test 4: Batch delivery performance
        print("\n4️⃣ Testing batch delivery performance...")
        await self._test_batch_delivery(target, min(iterations, 50))

        # Analyze results
        return self._analyze_results()

    async def _test_direct_daemon(self, target: str, iterations: int) -> None:
        """Test direct daemon client performance."""
        client = DaemonClient()

        for i in range(iterations):
            message = f"Performance test {i} - direct daemon"
            start = time.perf_counter()

            try:
                await client.publish(target, message, "normal", ["test"])
            except Exception as e:
                print(f"❌ Direct daemon error: {e}")
                continue

            elapsed_ms = (time.perf_counter() - start) * 1000
            self.results["direct_daemon"].append(elapsed_ms)

            if i % 10 == 0:
                print(f"  Progress: {i}/{iterations} (last: {elapsed_ms:.1f}ms)")

    async def _test_pubsub_client(self, target: str, iterations: int) -> None:
        """Test pubsub client with fallback performance."""
        for i in range(iterations):
            message = f"Performance test {i} - pubsub client"

            success, elapsed_ms = await self.pubsub_client.publish_notification(target, message, "normal", ["test"])

            if success:
                self.results["pubsub_client"].append(elapsed_ms)

            if i % 10 == 0:
                print(f"  Progress: {i}/{iterations} (last: {elapsed_ms:.1f}ms)")

    async def _test_priority_router(self, target: str, iterations: int) -> None:
        """Test priority-based routing performance."""
        priorities = ["critical", "high", "normal", "low"]

        for i in range(iterations):
            priority = priorities[i % len(priorities)]
            message = f"Performance test {i} - priority {priority}"

            start = time.perf_counter()
            success = await self.priority_router.route_message(target, message, priority, ["test"])
            elapsed_ms = (time.perf_counter() - start) * 1000

            if success:
                self.results["priority_router"].append(elapsed_ms)

            if i % 10 == 0:
                print(f"  Progress: {i}/{iterations} (last: {elapsed_ms:.1f}ms, priority: {priority})")

    async def _test_batch_delivery(self, target: str, batch_count: int) -> None:
        """Test batch delivery performance."""
        batch_sizes = [5, 10, 20, 50]

        for size in batch_sizes:
            if batch_count < size:
                continue

            # Prepare batch
            notifications = [
                {
                    "target": target,
                    "message": f"Batch test {i} of {size}",
                    "priority": "normal",
                    "tags": ["test", "batch"],
                }
                for i in range(size)
            ]

            # Test batch delivery
            start = time.perf_counter()
            result = await self.pubsub_client.batch_publish(notifications)
            elapsed_ms = (time.perf_counter() - start) * 1000

            # Calculate per-message time
            per_msg_ms = elapsed_ms / size if size > 0 else 0
            self.results["batch_delivery"].extend([per_msg_ms] * result["success"])

            print(f"  Batch size {size}: {elapsed_ms:.1f}ms total, {per_msg_ms:.1f}ms per message")

    def _analyze_results(self) -> dict[str, any]:
        """Analyze performance test results."""
        analysis = {
            "summary": {},
            "target_compliance": {},
            "recommendations": [],
        }

        # Analyze each test type
        for test_name, times in self.results.items():
            if not times:
                continue

            sorted_times = sorted(times)
            count = len(sorted_times)

            stats = {
                "count": count,
                "min": sorted_times[0],
                "max": sorted_times[-1],
                "mean": statistics.mean(sorted_times),
                "median": statistics.median(sorted_times),
                "p95": sorted_times[int(count * 0.95)] if count > 1 else sorted_times[0],
                "p99": sorted_times[int(count * 0.99)] if count > 1 else sorted_times[0],
            }

            # Check target compliance
            under_100ms = sum(1 for t in sorted_times if t < 100)
            compliance_pct = (under_100ms / count) * 100

            analysis["summary"][test_name] = stats
            analysis["target_compliance"][test_name] = {
                "under_100ms_count": under_100ms,
                "compliance_percentage": compliance_pct,
                "meets_target": compliance_pct >= 95,  # 95% should be under 100ms
            }

        # Generate recommendations
        self._generate_recommendations(analysis)

        return analysis

    def _generate_recommendations(self, analysis: dict[str, any]) -> None:
        """Generate performance recommendations based on results."""
        recommendations = []

        for test_name, compliance in analysis["target_compliance"].items():
            if not compliance["meets_target"]:
                pct = compliance["compliance_percentage"]
                recommendations.append(f"⚠️  {test_name}: Only {pct:.1f}% of messages meet <100ms target")

                # Specific recommendations
                if test_name == "direct_daemon":
                    recommendations.append("   → Check daemon socket performance")
                    recommendations.append("   → Verify no blocking operations in daemon")
                elif test_name == "pubsub_client":
                    recommendations.append("   → Consider reducing fallback timeout")
                    recommendations.append("   → Optimize daemon connection pooling")
                elif test_name == "priority_router":
                    recommendations.append("   → Review priority queue processing")
                    recommendations.append("   → Consider separate queues per priority")
                elif test_name == "batch_delivery":
                    recommendations.append("   → Reduce batch sizes for better latency")
                    recommendations.append("   → Implement streaming batch processing")

        if not recommendations:
            recommendations.append("✅ All performance targets met!")

        analysis["recommendations"] = recommendations

    def print_results(self, analysis: dict[str, any]) -> None:
        """Print formatted performance analysis."""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE TEST RESULTS")
        print("=" * 60)

        # Summary stats
        print("\n📈 Performance Summary:")
        for test_name, stats in analysis["summary"].items():
            print(f"\n{test_name}:")
            print(f"  Messages: {stats['count']}")
            print(f"  Min: {stats['min']:.1f}ms")
            print(f"  Median: {stats['median']:.1f}ms")
            print(f"  Mean: {stats['mean']:.1f}ms")
            print(f"  P95: {stats['p95']:.1f}ms")
            print(f"  P99: {stats['p99']:.1f}ms")
            print(f"  Max: {stats['max']:.1f}ms")

        # Target compliance
        print("\n🎯 Target Compliance (<100ms):")
        for test_name, compliance in analysis["target_compliance"].items():
            status = "✅" if compliance["meets_target"] else "❌"
            print(f"{status} {test_name}: {compliance['compliance_percentage']:.1f}%")

        # Recommendations
        print("\n💡 Recommendations:")
        for rec in analysis["recommendations"]:
            print(rec)


async def main():
    """Run performance tests."""
    tester = PubsubPerformanceTester()

    # Create test window if needed
    tmux = TMUXManager()
    try:
        tmux.create_session("test")
    except Exception:
        pass  # Session might already exist

    # Run tests
    results = await tester.run_performance_tests("test:0", iterations=100)

    # Print results
    tester.print_results(results)


if __name__ == "__main__":
    asyncio.run(main())
