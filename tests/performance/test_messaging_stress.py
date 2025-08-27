"""Stress tests for messaging system under extreme conditions."""

import asyncio
import gc
import random
import time
from typing import Dict

import psutil
import pytest

from tmux_orchestrator.core.messaging.chunk_buffer import ChunkBuffer
from tmux_orchestrator.core.messaging.chunk_manager import ChunkManager
from tmux_orchestrator.core.messaging.enhanced_protocol import EnhancedMessagingProtocol
from tmux_orchestrator.core.messaging.message_queue import MessageQueue
from tmux_orchestrator.core.messaging.performance_monitor import PerformanceMonitor


class StressTester:
    """Comprehensive stress testing for messaging components."""

    def __init__(self):
        self.chunk_manager = ChunkManager(chunk_size=180)
        self.chunk_buffer = ChunkBuffer(timeout=60)
        self.message_queue = MessageQueue(max_size=10000)
        self.protocol = EnhancedMessagingProtocol()
        self.monitor = PerformanceMonitor()

    async def test_memory_stress(self, message_count: int = 1000, message_size: int = 10240) -> Dict:
        """Test memory usage with large messages.

        Args:
            message_count: Number of messages to process
            message_size: Size of each message in bytes

        Returns:
            Test results
        """
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB

        results = {
            "test": "memory_stress",
            "message_count": message_count,
            "message_size": message_size,
            "start_memory_mb": start_memory,
            "errors": [],
        }

        # Generate and process large messages
        for i in range(message_count):
            message = "X" * message_size + str(i)

            # Chunk the message
            chunks = self.chunk_manager.chunk_message(message, f"sender_{i}")

            # Process chunks through buffer
            for chunk in chunks:
                complete = self.chunk_buffer.add_chunk(chunk)
                if complete and i % 100 == 0:
                    # Force garbage collection periodically
                    gc.collect()

            # Monitor memory growth
            current_memory = process.memory_info().rss / 1024 / 1024
            if current_memory - start_memory > 100:  # Alert if >100MB growth
                results["errors"].append(
                    f"Excessive memory growth at message {i}: {current_memory - start_memory:.2f}MB"
                )

        # Final memory check
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024
        results["final_memory_mb"] = final_memory
        results["memory_growth_mb"] = final_memory - start_memory
        results["passed"] = len(results["errors"]) == 0

        return results

    async def test_concurrent_load(
        self, num_senders: int = 50, messages_per_sender: int = 100, message_size: int = 1024
    ) -> Dict:
        """Test concurrent message processing.

        Args:
            num_senders: Number of concurrent senders
            messages_per_sender: Messages each sender sends
            message_size: Size of each message

        Returns:
            Test results
        """
        results = {
            "test": "concurrent_load",
            "num_senders": num_senders,
            "messages_per_sender": messages_per_sender,
            "message_size": message_size,
            "latencies": [],
            "errors": [],
        }

        async def sender_task(sender_id: str):
            """Individual sender coroutine."""
            local_latencies = []

            for i in range(messages_per_sender):
                message = f"{sender_id}_msg_{i}_" + "X" * message_size

                start = time.perf_counter()

                # Process through protocol
                _ = self.protocol.prepare_message(content=message, sender=sender_id, priority=random.randint(1, 10))

                # Queue the message
                queued = self.message_queue.enqueue(content=message, sender=sender_id, priority=5)

                latency = (time.perf_counter() - start) * 1000
                local_latencies.append(latency)

                if not queued:
                    results["errors"].append(f"{sender_id}: Failed to queue message {i}")

                # Small delay to prevent overwhelming
                await asyncio.sleep(0.001)

            return local_latencies

        # Run concurrent senders
        start_time = time.perf_counter()

        tasks = [sender_task(f"sender_{i}") for i in range(num_senders)]

        all_latencies = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.perf_counter() - start_time

        # Aggregate results
        for sender_latencies in all_latencies:
            if isinstance(sender_latencies, list):
                results["latencies"].extend(sender_latencies)
            else:
                results["errors"].append(f"Sender task failed: {sender_latencies}")

        # Calculate metrics
        if results["latencies"]:
            results["avg_latency_ms"] = sum(results["latencies"]) / len(results["latencies"])
            results["max_latency_ms"] = max(results["latencies"])
            results["min_latency_ms"] = min(results["latencies"])
            results["p99_latency_ms"] = sorted(results["latencies"])[int(len(results["latencies"]) * 0.99)]
        else:
            results["avg_latency_ms"] = 0
            results["max_latency_ms"] = 0
            results["min_latency_ms"] = 0
            results["p99_latency_ms"] = 0

        results["total_time_seconds"] = total_time
        results["throughput_msgs_per_sec"] = (num_senders * messages_per_sender) / total_time
        results["passed"] = len(results["errors"]) == 0 and results["p99_latency_ms"] < 100

        return results

    async def test_queue_overflow(self) -> Dict:
        """Test queue overflow behavior."""
        results = {
            "test": "queue_overflow",
            "queue_size": self.message_queue.max_size,
            "messages_sent": 0,
            "messages_dropped": 0,
            "overflow_behavior": "verified",
        }

        # Fill queue beyond capacity
        overflow_count = int(self.message_queue.max_size * 1.5)

        for i in range(overflow_count):
            message = f"overflow_test_{i}"
            success = self.message_queue.enqueue(content=message, sender="overflow_tester", priority=5)

            if success:
                results["messages_sent"] += 1
            else:
                results["messages_dropped"] += 1

        # Verify queue behavior
        queue_stats = self.message_queue.get_stats()
        results["final_queue_size"] = queue_stats["current_size"]
        results["peak_size"] = queue_stats["peak_size"]
        results["drop_rate"] = queue_stats.get("dropped", 0) / overflow_count * 100

        # Test should pass if queue properly handles overflow
        results["passed"] = (
            results["messages_dropped"] > 0 and results["final_queue_size"] <= self.message_queue.max_size
        )

        return results

    async def test_chunk_reassembly_stress(self) -> Dict:
        """Test chunk reassembly under stress conditions."""
        results = {"test": "chunk_reassembly_stress", "messages_tested": 0, "reassembly_times": [], "errors": []}

        # Test with various message sizes and out-of-order delivery
        test_messages = [
            ("small_" * 10, 100),
            ("medium_" * 50, 500),
            ("large_" * 200, 2000),
            ("xlarge_" * 1000, 10000),
        ]

        for base_content, size in test_messages:
            message = base_content[:size]

            # Chunk the message
            chunks = self.chunk_manager.chunk_message(message, "stress_sender")

            # Simulate out-of-order delivery
            if len(chunks) > 1:
                random.shuffle(chunks)

            # Process chunks
            start = time.perf_counter()
            complete_message = None

            for chunk in chunks:
                complete = self.chunk_buffer.add_chunk(chunk)
                if complete:
                    complete_message = complete

            reassembly_time = (time.perf_counter() - start) * 1000
            results["reassembly_times"].append(reassembly_time)

            # Verify reassembly
            if complete_message != message.strip():
                results["errors"].append(f"Reassembly failed for {size} byte message")

            results["messages_tested"] += 1

        # Calculate metrics
        if results["reassembly_times"]:
            results["avg_reassembly_ms"] = sum(results["reassembly_times"]) / len(results["reassembly_times"])
            results["max_reassembly_ms"] = max(results["reassembly_times"])

        results["passed"] = len(results["errors"]) == 0

        return results

    async def test_sustained_load(self, duration_seconds: int = 60) -> Dict:
        """Test sustained high load over time.

        Args:
            duration_seconds: Duration of sustained load test

        Returns:
            Test results
        """
        results = {
            "test": "sustained_load",
            "duration_seconds": duration_seconds,
            "messages_processed": 0,
            "errors": [],
            "performance_samples": [],
        }

        start_time = time.time()
        end_time = start_time + duration_seconds
        sample_interval = 5  # Sample every 5 seconds
        next_sample = start_time + sample_interval

        message_count = 0
        error_count = 0

        while time.time() < end_time:
            # Generate variable-sized message
            size = random.randint(100, 5000)
            message = "S" * size + str(message_count)

            # Process message
            try:
                # Through protocol
                _ = self.protocol.prepare_message(content=message, sender="sustained_tester")

                # Through queue
                self.message_queue.enqueue(content=message, sender="sustained_tester")

                message_count += 1

            except Exception as e:
                error_count += 1
                if error_count <= 10:  # Limit error logging
                    results["errors"].append(str(e))

            # Periodic sampling
            if time.time() >= next_sample:
                # Get current metrics
                queue_stats = self.message_queue.get_stats()
                buffer_stats = self.chunk_buffer.get_stats()

                sample = {
                    "timestamp": time.time() - start_time,
                    "messages_total": message_count,
                    "errors_total": error_count,
                    "queue_size": queue_stats["current_size"],
                    "buffer_count": buffer_stats["active_buffers"],
                    "throughput": message_count / (time.time() - start_time),
                }

                results["performance_samples"].append(sample)
                next_sample = time.time() + sample_interval

            # Small delay to prevent CPU saturation
            await asyncio.sleep(0.001)

        # Final metrics
        total_time = time.time() - start_time
        results["messages_processed"] = message_count
        results["total_errors"] = error_count
        results["avg_throughput"] = message_count / total_time
        results["error_rate"] = (error_count / message_count * 100) if message_count > 0 else 0

        # Check if performance degraded over time
        if len(results["performance_samples"]) >= 2:
            first_throughput = results["performance_samples"][0]["throughput"]
            last_throughput = results["performance_samples"][-1]["throughput"]
            degradation = (first_throughput - last_throughput) / first_throughput * 100
            results["performance_degradation"] = degradation

        results["passed"] = error_count == 0 and results.get("performance_degradation", 0) < 20

        return results


# Test fixtures
@pytest.fixture
async def stress_tester():
    """Create a stress tester instance."""
    return StressTester()


# Actual test cases
@pytest.mark.asyncio
@pytest.mark.stress
async def test_memory_10kb_messages(stress_tester):
    """Test memory handling with 10KB messages."""
    results = await stress_tester.test_memory_stress(message_count=100, message_size=10240)

    print("\n=== Memory Stress Test (10KB messages) ===")
    print(f"Messages: {results['message_count']}")
    print(f"Message Size: {results['message_size']} bytes")
    print(f"Memory Growth: {results['memory_growth_mb']:.2f}MB")
    print(f"Passed: {results['passed']}")

    assert results["passed"], f"Memory test failed: {results['errors']}"
    assert results["memory_growth_mb"] < 100, f"Excessive memory usage: {results['memory_growth_mb']}MB"


@pytest.mark.asyncio
@pytest.mark.stress
async def test_concurrent_100_senders(stress_tester):
    """Test with 100 concurrent senders."""
    results = await stress_tester.test_concurrent_load(num_senders=100, messages_per_sender=50, message_size=1024)

    print("\n=== Concurrent Load Test (100 senders) ===")
    print(f"Senders: {results['num_senders']}")
    print(f"Messages per Sender: {results['messages_per_sender']}")
    print(f"Avg Latency: {results['avg_latency_ms']:.2f}ms")
    print(f"P99 Latency: {results['p99_latency_ms']:.2f}ms")
    print(f"Throughput: {results['throughput_msgs_per_sec']:.2f} msgs/sec")
    print(f"Passed: {results['passed']}")

    assert results["passed"], f"Concurrent test failed: {results['errors'][:5]}"
    assert results["p99_latency_ms"] < 100, f"P99 latency {results['p99_latency_ms']}ms exceeds target"


@pytest.mark.asyncio
@pytest.mark.stress
async def test_queue_overflow_handling(stress_tester):
    """Test queue overflow behavior."""
    results = await stress_tester.test_queue_overflow()

    print("\n=== Queue Overflow Test ===")
    print(f"Queue Size: {results['queue_size']}")
    print(f"Messages Sent: {results['messages_sent']}")
    print(f"Messages Dropped: {results['messages_dropped']}")
    print(f"Drop Rate: {results['drop_rate']:.2f}%")
    print(f"Passed: {results['passed']}")

    assert results["passed"], "Queue overflow handling failed"


@pytest.mark.asyncio
@pytest.mark.stress
async def test_chunk_reassembly_under_stress(stress_tester):
    """Test chunk reassembly with out-of-order delivery."""
    results = await stress_tester.test_chunk_reassembly_stress()

    print("\n=== Chunk Reassembly Stress Test ===")
    print(f"Messages Tested: {results['messages_tested']}")
    print(f"Avg Reassembly Time: {results.get('avg_reassembly_ms', 0):.2f}ms")
    print(f"Max Reassembly Time: {results.get('max_reassembly_ms', 0):.2f}ms")
    print(f"Errors: {len(results['errors'])}")
    print(f"Passed: {results['passed']}")

    assert results["passed"], f"Reassembly failed: {results['errors']}"


@pytest.mark.asyncio
@pytest.mark.stress
@pytest.mark.slow
async def test_sustained_high_load(stress_tester):
    """Test sustained load for 30 seconds."""
    results = await stress_tester.test_sustained_load(duration_seconds=30)

    print("\n=== Sustained Load Test (30s) ===")
    print(f"Duration: {results['duration_seconds']}s")
    print(f"Messages Processed: {results['messages_processed']}")
    print(f"Total Errors: {results['total_errors']}")
    print(f"Avg Throughput: {results['avg_throughput']:.2f} msgs/sec")
    print(f"Error Rate: {results['error_rate']:.2f}%")
    if "performance_degradation" in results:
        print(f"Performance Degradation: {results['performance_degradation']:.2f}%")
    print(f"Passed: {results['passed']}")

    assert results["passed"], f"Sustained load test failed: {results.get('errors', [])[:3]}"


if __name__ == "__main__":
    # Run stress tests when executed directly
    async def run_all_tests():
        tester = StressTester()

        print("Starting Messaging System Stress Tests...")
        print("=" * 60)

        # Run each test
        tests = [
            ("Memory Stress", tester.test_memory_stress(100, 10240)),
            ("Concurrent Load", tester.test_concurrent_load(50, 50, 1024)),
            ("Queue Overflow", tester.test_queue_overflow()),
            ("Chunk Reassembly", tester.test_chunk_reassembly_stress()),
            ("Sustained Load", tester.test_sustained_load(10)),
        ]

        passed = 0
        failed = 0

        for name, test_coro in tests:
            try:
                results = await test_coro
                if results.get("passed"):
                    print(f"✓ {name}: PASSED")
                    passed += 1
                else:
                    print(f"✗ {name}: FAILED")
                    failed += 1
            except Exception as e:
                print(f"✗ {name}: ERROR - {e}")
                failed += 1

        print("\n" + "=" * 60)
        print(f"Results: {passed} passed, {failed} failed")

        return passed, failed

    passed, failed = asyncio.run(run_all_tests())
