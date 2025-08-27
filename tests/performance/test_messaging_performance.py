"""Performance benchmarking suite for the messaging system."""

import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import pytest

from tmux_orchestrator.core.messaging.chunk_manager import ChunkManager


@dataclass
class PerformanceMetrics:
    """Container for performance test results."""

    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    throughput_msgs_per_sec: float
    total_messages: int
    failed_messages: int
    avg_message_size_bytes: float
    max_message_size_bytes: int


class MockMessageQueue:
    """Mock message queue for testing until MessageQueue is implemented."""

    def __init__(self):
        self.messages = []
        self.processing_delay = 0.001  # 1ms simulated processing

    async def send(self, message: Dict[str, Any]) -> float:
        """Send a message and return latency."""
        start = time.perf_counter()
        await asyncio.sleep(self.processing_delay)
        self.messages.append(message)
        return (time.perf_counter() - start) * 1000  # Convert to ms


class MessagingPerformanceTester:
    """Performance testing harness for messaging system."""

    def __init__(self):
        self.chunk_manager = ChunkManager(chunk_size=180)
        self.queue = MockMessageQueue()
        self.latencies: List[float] = []
        self.message_sizes: List[int] = []

    async def benchmark_single_message(self, message: str, sender: str = "test") -> float:
        """Benchmark a single message send operation."""
        # Chunk the message
        start = time.perf_counter()
        chunks = self.chunk_manager.chunk_message(message, sender)
        chunk_time = (time.perf_counter() - start) * 1000

        # Send all chunks
        send_latencies = []
        for chunk in chunks:
            chunk_json = json.dumps(chunk)
            self.message_sizes.append(len(chunk_json.encode("utf-8")))
            latency = await self.queue.send(chunk)
            send_latencies.append(latency)

        total_latency = chunk_time + sum(send_latencies)
        self.latencies.append(total_latency)
        return total_latency

    async def run_throughput_test(self, num_messages: int = 1000, message_size: int = 500) -> PerformanceMetrics:
        """Test throughput with multiple messages."""
        self.latencies.clear()
        self.message_sizes.clear()

        # Generate test messages
        messages = ["x" * message_size + str(i) for i in range(num_messages)]

        # Run benchmark
        start_time = time.perf_counter()
        tasks = [self.benchmark_single_message(msg, f"sender_{i}") for i, msg in enumerate(messages)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

        # Calculate metrics
        return self._calculate_metrics(num_messages, total_time)

    async def run_variable_size_test(self) -> Dict[int, PerformanceMetrics]:
        """Test with various message sizes."""
        test_sizes = [50, 100, 200, 500, 1000, 2000, 5000, 10000]
        results = {}

        for size in test_sizes:
            self.latencies.clear()
            self.message_sizes.clear()

            # Generate messages of specific size
            num_messages = min(1000, 50000 // size)  # Adjust count based on size
            messages = ["x" * size for _ in range(num_messages)]

            start_time = time.perf_counter()
            for msg in messages:
                await self.benchmark_single_message(msg)
            total_time = time.perf_counter() - start_time

            results[size] = self._calculate_metrics(num_messages, total_time)

        return results

    async def run_stress_test(self, duration_seconds: int = 60, concurrent_senders: int = 10) -> PerformanceMetrics:
        """Stress test with concurrent senders."""
        self.latencies.clear()
        self.message_sizes.clear()

        async def sender_task(sender_id: str, stop_time: float):
            """Individual sender task."""
            msg_count = 0
            while time.time() < stop_time:
                size = 100 + (msg_count % 900)  # Variable sizes 100-1000
                message = "x" * size
                await self.benchmark_single_message(message, sender_id)
                msg_count += 1
                await asyncio.sleep(0.01)  # Small delay between messages
            return msg_count

        # Run concurrent senders
        stop_time = time.time() + duration_seconds
        start_time = time.perf_counter()

        tasks = [sender_task(f"sender_{i}", stop_time) for i in range(concurrent_senders)]
        message_counts = await asyncio.gather(*tasks)

        total_time = time.perf_counter() - start_time
        total_messages = sum(message_counts)

        return self._calculate_metrics(total_messages, total_time)

    def _calculate_metrics(self, num_messages: int, total_time: float) -> PerformanceMetrics:
        """Calculate performance metrics from collected data."""
        if not self.latencies:
            return PerformanceMetrics(
                avg_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                max_latency_ms=0,
                min_latency_ms=0,
                throughput_msgs_per_sec=0,
                total_messages=0,
                failed_messages=0,
                avg_message_size_bytes=0,
                max_message_size_bytes=0,
            )

        sorted_latencies = sorted(self.latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p99_index = int(len(sorted_latencies) * 0.99)

        return PerformanceMetrics(
            avg_latency_ms=statistics.mean(self.latencies),
            p95_latency_ms=sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1],
            p99_latency_ms=sorted_latencies[p99_index] if p99_index < len(sorted_latencies) else sorted_latencies[-1],
            max_latency_ms=max(self.latencies),
            min_latency_ms=min(self.latencies),
            throughput_msgs_per_sec=num_messages / total_time if total_time > 0 else 0,
            total_messages=num_messages,
            failed_messages=0,
            avg_message_size_bytes=statistics.mean(self.message_sizes) if self.message_sizes else 0,
            max_message_size_bytes=max(self.message_sizes) if self.message_sizes else 0,
        )


@pytest.mark.asyncio
async def test_baseline_performance():
    """Test baseline performance meets requirements."""
    tester = MessagingPerformanceTester()

    # Test with 1KB message
    metrics = await tester.run_throughput_test(num_messages=100, message_size=1024)

    print("\n=== Baseline Performance (1KB messages) ===")
    print(f"Average Latency: {metrics.avg_latency_ms:.2f}ms")
    print(f"P95 Latency: {metrics.p95_latency_ms:.2f}ms")
    print(f"P99 Latency: {metrics.p99_latency_ms:.2f}ms")
    print(f"Throughput: {metrics.throughput_msgs_per_sec:.2f} msgs/sec")

    # Verify <100ms requirement
    assert metrics.avg_latency_ms < 100, f"Average latency {metrics.avg_latency_ms}ms exceeds 100ms target"
    assert metrics.p99_latency_ms < 100, f"P99 latency {metrics.p99_latency_ms}ms exceeds 100ms target"


@pytest.mark.asyncio
async def test_10kb_message_support():
    """Test that system can handle 10KB messages."""
    tester = MessagingPerformanceTester()

    # Test with 10KB message
    large_message = "x" * 10240  # 10KB
    latency = await tester.benchmark_single_message(large_message)

    print("\n=== 10KB Message Test ===")
    print("Message Size: 10240 bytes")
    print(f"Total Latency: {latency:.2f}ms")
    print(f"Chunks Created: {len(tester.chunk_manager.chunk_message(large_message, 'test'))}")

    # Verify message was processed
    assert latency < 100, f"10KB message latency {latency}ms exceeds 100ms target"
    assert len(tester.queue.messages) > 0, "10KB message was not processed"


@pytest.mark.asyncio
async def test_variable_message_sizes():
    """Test performance across different message sizes."""
    tester = MessagingPerformanceTester()
    results = await tester.run_variable_size_test()

    print("\n=== Variable Size Performance ===")
    print(f"{'Size (bytes)':>12} | {'Avg Latency':>12} | {'P99 Latency':>12} | {'Throughput':>15}")
    print("-" * 65)

    for size, metrics in sorted(results.items()):
        print(
            f"{size:>12} | {metrics.avg_latency_ms:>11.2f}ms | {metrics.p99_latency_ms:>11.2f}ms | {metrics.throughput_msgs_per_sec:>10.2f} m/s"
        )

        # All sizes should meet <100ms requirement
        assert metrics.avg_latency_ms < 100, f"Size {size}: avg latency {metrics.avg_latency_ms}ms exceeds target"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_stress_performance():
    """Stress test with concurrent senders."""
    tester = MessagingPerformanceTester()

    # Run 10-second stress test with 10 concurrent senders
    metrics = await tester.run_stress_test(duration_seconds=10, concurrent_senders=10)

    print("\n=== Stress Test Results ===")
    print("Duration: 10 seconds")
    print("Concurrent Senders: 10")
    print(f"Total Messages: {metrics.total_messages}")
    print(f"Average Latency: {metrics.avg_latency_ms:.2f}ms")
    print(f"P95 Latency: {metrics.p95_latency_ms:.2f}ms")
    print(f"P99 Latency: {metrics.p99_latency_ms:.2f}ms")
    print(f"Max Latency: {metrics.max_latency_ms:.2f}ms")
    print(f"Throughput: {metrics.throughput_msgs_per_sec:.2f} msgs/sec")

    # Even under stress, should maintain reasonable performance
    assert metrics.p95_latency_ms < 100, f"P95 latency {metrics.p95_latency_ms}ms exceeds target under stress"


def test_chunk_manager_efficiency():
    """Test ChunkManager chunking efficiency."""
    manager = ChunkManager(chunk_size=180)

    test_cases = [
        (100, 1),  # Small message, no chunking
        (200, 1),  # At threshold, no chunking
        (500, 3),  # Medium message, expect ~3 chunks
        (1000, 6),  # Large message, expect ~6 chunks
        (10000, 60),  # 10KB message, expect ~60 chunks
    ]

    print("\n=== Chunk Manager Efficiency ===")
    print(f"{'Message Size':>12} | {'Chunks':>7} | {'Avg Chunk Size':>14} | {'Efficiency':>10}")
    print("-" * 55)

    for size, expected_chunks in test_cases:
        message = "x" * size
        chunks = manager.chunk_message(message, "test")

        if chunks[0]["type"] == "standard":
            avg_chunk_size = size
            num_chunks = 1
        else:
            chunk_sizes = [len(c["content"]) for c in chunks]
            avg_chunk_size = statistics.mean(chunk_sizes)
            num_chunks = len(chunks)

        efficiency = (size / (num_chunks * manager.chunk_size)) * 100 if num_chunks > 1 else 100

        print(f"{size:>12} | {num_chunks:>7} | {avg_chunk_size:>14.1f} | {efficiency:>9.1f}%")

        # Verify reasonable chunking
        assert num_chunks <= expected_chunks * 1.5, f"Too many chunks for {size} byte message"


if __name__ == "__main__":
    # Run basic tests when executed directly
    asyncio.run(test_baseline_performance())
    asyncio.run(test_10kb_message_support())
    asyncio.run(test_variable_message_sizes())
    test_chunk_manager_efficiency()
