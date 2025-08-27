"""Performance monitoring for the messaging system."""

import gc
import time
import tracemalloc
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Tuple

import psutil


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    timestamp: float = field(default_factory=time.time)
    latency_ms: float = 0.0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    throughput_msgs_per_sec: float = 0.0
    queue_depth: int = 0
    chunk_buffer_size: int = 0
    reassembly_time_ms: float = 0.0
    error_count: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "latency_ms": round(self.latency_ms, 2),
            "memory_mb": round(self.memory_mb, 2),
            "cpu_percent": round(self.cpu_percent, 2),
            "throughput_msgs_per_sec": round(self.throughput_msgs_per_sec, 2),
            "queue_depth": self.queue_depth,
            "chunk_buffer_size": self.chunk_buffer_size,
            "reassembly_time_ms": round(self.reassembly_time_ms, 2),
            "error_count": self.error_count,
        }


class PerformanceMonitor:
    """Monitor messaging system performance metrics."""

    def __init__(self, window_size: int = 1000, alert_threshold_ms: float = 100.0, memory_threshold_mb: float = 100.0):
        """Initialize performance monitor.

        Args:
            window_size: Number of samples to keep in rolling window
            alert_threshold_ms: Latency threshold for alerts (default 100ms)
            memory_threshold_mb: Memory threshold for alerts (default 100MB)
        """
        self.window_size = window_size
        self.alert_threshold_ms = alert_threshold_ms
        self.memory_threshold_mb = memory_threshold_mb

        # Metrics storage
        self.latencies: Deque[float] = deque(maxlen=window_size)
        self.memory_usage: Deque[float] = deque(maxlen=window_size)
        self.reassembly_times: Deque[float] = deque(maxlen=window_size)
        self.throughput_samples: Deque[Tuple[float, int]] = deque(maxlen=100)

        # Tracking counters
        self.message_count = 0
        self.error_count = 0
        self.alert_count = 0
        self.start_time = time.time()

        # Current state
        self.current_queue_depth = 0
        self.current_buffer_size = 0
        self.max_latency_ms = 0.0
        self.max_memory_mb = 0.0

        # Process monitoring
        self.process = psutil.Process()
        tracemalloc.start()

    def record_message_sent(self, latency_ms: float, message_size_bytes: int):
        """Record metrics for a sent message.

        Args:
            latency_ms: Processing latency in milliseconds
            message_size_bytes: Size of message in bytes
        """
        self.latencies.append(latency_ms)
        self.message_count += 1

        # Update max latency
        if latency_ms > self.max_latency_ms:
            self.max_latency_ms = latency_ms

        # Check for latency alert
        if latency_ms > self.alert_threshold_ms:
            self.alert_count += 1

        # Record throughput sample
        current_time = time.time()
        self.throughput_samples.append((current_time, 1))

    def record_reassembly(self, reassembly_time_ms: float):
        """Record chunk reassembly time.

        Args:
            reassembly_time_ms: Time to reassemble chunks in milliseconds
        """
        self.reassembly_times.append(reassembly_time_ms)

    def record_error(self):
        """Record a message processing error."""
        self.error_count += 1

    def update_queue_depth(self, depth: int):
        """Update current queue depth.

        Args:
            depth: Current number of messages in queue
        """
        self.current_queue_depth = depth

    def update_buffer_size(self, size: int):
        """Update current chunk buffer size.

        Args:
            size: Number of messages in chunk buffer
        """
        self.current_buffer_size = size

    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics snapshot."""
        # Calculate memory usage
        current_memory = self.process.memory_info().rss / 1024 / 1024  # Convert to MB
        self.memory_usage.append(current_memory)

        if current_memory > self.max_memory_mb:
            self.max_memory_mb = current_memory

        # Calculate CPU usage
        cpu_percent = self.process.cpu_percent(interval=0.01)

        # Calculate average latency
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0

        # Calculate throughput
        throughput = self._calculate_throughput()

        # Calculate average reassembly time
        avg_reassembly = sum(self.reassembly_times) / len(self.reassembly_times) if self.reassembly_times else 0

        return PerformanceMetrics(
            latency_ms=avg_latency,
            memory_mb=current_memory,
            cpu_percent=cpu_percent,
            throughput_msgs_per_sec=throughput,
            queue_depth=self.current_queue_depth,
            chunk_buffer_size=self.current_buffer_size,
            reassembly_time_ms=avg_reassembly,
            error_count=self.error_count,
        )

    def _calculate_throughput(self) -> float:
        """Calculate current throughput in messages per second."""
        if len(self.throughput_samples) < 2:
            return 0.0

        # Get samples from last 5 seconds
        current_time = time.time()
        recent_samples = [count for timestamp, count in self.throughput_samples if current_time - timestamp <= 5.0]

        if not recent_samples:
            return 0.0

        # Calculate messages per second
        time_window = min(5.0, current_time - self.throughput_samples[0][0])
        if time_window > 0:
            return sum(recent_samples) / time_window
        return 0.0

    def get_percentiles(self) -> Dict[str, float]:
        """Get latency percentiles."""
        if not self.latencies:
            return {"p50": 0, "p95": 0, "p99": 0, "p999": 0}

        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)

        return {
            "p50": sorted_latencies[int(n * 0.5)],
            "p95": sorted_latencies[int(n * 0.95)] if n > 20 else sorted_latencies[-1],
            "p99": sorted_latencies[int(n * 0.99)] if n > 100 else sorted_latencies[-1],
            "p999": sorted_latencies[int(n * 0.999)] if n > 1000 else sorted_latencies[-1],
        }

    def get_summary(self) -> Dict:
        """Get comprehensive performance summary."""
        uptime = time.time() - self.start_time
        current = self.get_current_metrics()
        percentiles = self.get_percentiles()

        # Get memory statistics
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")
        memory_top = [
            {"file": stat.traceback.format()[0], "size_mb": stat.size / 1024 / 1024} for stat in top_stats[:3]
        ]

        return {
            "uptime_seconds": round(uptime, 2),
            "total_messages": self.message_count,
            "total_errors": self.error_count,
            "error_rate": round(self.error_count / max(1, self.message_count) * 100, 2),
            "alerts_triggered": self.alert_count,
            "current_metrics": current.to_dict(),
            "latency_percentiles": {k: round(v, 2) for k, v in percentiles.items()},
            "max_observed": {"latency_ms": round(self.max_latency_ms, 2), "memory_mb": round(self.max_memory_mb, 2)},
            "thresholds": {"latency_ms": self.alert_threshold_ms, "memory_mb": self.memory_threshold_mb},
            "memory_top_consumers": memory_top,
        }

    def check_health(self) -> Tuple[bool, List[str]]:
        """Check system health against thresholds.

        Returns:
            Tuple of (is_healthy, list_of_issues)
        """
        issues = []
        current = self.get_current_metrics()

        # Check latency
        if current.latency_ms > self.alert_threshold_ms:
            issues.append(f"High latency: {current.latency_ms:.2f}ms > {self.alert_threshold_ms}ms")

        # Check memory
        if current.memory_mb > self.memory_threshold_mb:
            issues.append(f"High memory usage: {current.memory_mb:.2f}MB > {self.memory_threshold_mb}MB")

        # Check error rate
        error_rate = self.error_count / max(1, self.message_count) * 100
        if error_rate > 5.0:
            issues.append(f"High error rate: {error_rate:.2f}%")

        # Check queue depth
        if self.current_queue_depth > 1000:
            issues.append(f"Queue backlog: {self.current_queue_depth} messages")

        return len(issues) == 0, issues

    def reset(self):
        """Reset all metrics."""
        self.latencies.clear()
        self.memory_usage.clear()
        self.reassembly_times.clear()
        self.throughput_samples.clear()
        self.message_count = 0
        self.error_count = 0
        self.alert_count = 0
        self.start_time = time.time()
        self.max_latency_ms = 0.0
        self.max_memory_mb = 0.0
        gc.collect()
