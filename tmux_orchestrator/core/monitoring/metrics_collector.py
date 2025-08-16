"""
Metrics collection and reporting system.

This module collects, aggregates, and reports monitoring metrics
for performance tracking and system health analysis.
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Deque, Dict, List, Optional

from tmux_orchestrator.core.config import Config

from .types import MonitorComponent, MonitorStatus


@dataclass
class MetricPoint:
    """A single metric data point."""

    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Summary statistics for a metric."""

    name: str
    count: int
    mean: float
    min_value: float
    max_value: float
    std_dev: float
    percentile_50: float
    percentile_90: float
    percentile_99: float
    latest_value: float
    window_duration: timedelta


class MetricsCollector(MonitorComponent):
    """Collects and aggregates monitoring metrics."""

    def __init__(
        self, config: Config, logger: logging.Logger, retention_minutes: int = 60, max_points_per_metric: int = 1000
    ):
        """Initialize the metrics collector.

        Args:
            config: Configuration instance
            logger: Logger instance
            retention_minutes: How long to retain metrics
            max_points_per_metric: Maximum data points per metric
        """
        self.config = config
        self.logger = logger
        self.retention_minutes = retention_minutes
        self.max_points_per_metric = max_points_per_metric

        # Metric storage: metric_name -> deque of MetricPoint
        self._metrics: Dict[str, Deque[MetricPoint]] = defaultdict(lambda: deque(maxlen=max_points_per_metric))

        # Counters for cumulative metrics
        self._counters: Dict[str, float] = defaultdict(float)

        # Gauges for current values
        self._gauges: Dict[str, float] = defaultdict(float)

        # Histograms for distributions
        self._histograms: Dict[str, List[float]] = defaultdict(list)

        # Timing tracking
        self._timers: Dict[str, float] = {}

    def initialize(self) -> bool:
        """Initialize the metrics collector."""
        try:
            self.logger.info("Initializing MetricsCollector")

            # Initialize standard metrics
            self.set_gauge("monitoring.enabled", 1.0)
            self.set_gauge("monitoring.start_time", time.time())

            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize MetricsCollector: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up metrics collector resources."""
        self.logger.info("Cleaning up MetricsCollector")
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a metric data point.

        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels for the metric
        """
        if labels is None:
            labels = {}

        point = MetricPoint(timestamp=datetime.now(), value=value, labels=labels)

        self._metrics[name].append(point)
        self._clean_old_metrics(name)

    def increment_counter(self, name: str, delta: float = 1.0) -> None:
        """Increment a counter metric.

        Args:
            name: Counter name
            delta: Amount to increment
        """
        self._counters[name] += delta
        self.record_metric(f"counter.{name}", self._counters[name])

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge metric.

        Args:
            name: Gauge name
            value: Current value
        """
        self._gauges[name] = value
        self.record_metric(f"gauge.{name}", value)

    def record_histogram(self, name: str, value: float) -> None:
        """Record a value in a histogram.

        Args:
            name: Histogram name
            value: Value to record
        """
        self._histograms[name].append(value)

        # Keep histogram size bounded
        if len(self._histograms[name]) > self.max_points_per_metric:
            self._histograms[name] = self._histograms[name][-self.max_points_per_metric :]

        self.record_metric(f"histogram.{name}", value)

    def start_timer(self, name: str) -> None:
        """Start a timer.

        Args:
            name: Timer name
        """
        self._timers[name] = time.time()

    def stop_timer(self, name: str) -> Optional[float]:
        """Stop a timer and record the duration.

        Args:
            name: Timer name

        Returns:
            Duration in seconds or None if timer not found
        """
        if name not in self._timers:
            self.logger.warning(f"Timer {name} not found")
            return None

        duration = time.time() - self._timers[name]
        del self._timers[name]

        self.record_histogram(f"timer.{name}", duration)
        return duration

    def record_monitor_cycle(self, status: MonitorStatus) -> None:
        """Record metrics from a monitoring cycle.

        Args:
            status: MonitorStatus from the cycle
        """
        # Record agent metrics
        self.set_gauge("agents.total", status.active_agents)
        self.set_gauge("agents.idle", status.idle_agents)

        # Record error metrics
        self.increment_counter("errors.total", status.errors_detected)

        # Record cycle metrics
        self.increment_counter("cycles.total")

        if status.end_time and status.start_time:
            duration = (status.end_time - status.start_time).total_seconds()
            self.record_histogram("cycle.duration", duration)

            # Calculate agents per second
            if duration > 0:
                agents_per_second = status.active_agents / duration
                self.set_gauge("monitoring.agents_per_second", agents_per_second)

    def get_metric_summary(self, name: str, window_minutes: Optional[int] = None) -> Optional[MetricSummary]:
        """Get summary statistics for a metric.

        Args:
            name: Metric name
            window_minutes: Time window for calculation (default: all data)

        Returns:
            MetricSummary or None if metric not found
        """
        if name not in self._metrics or not self._metrics[name]:
            return None

        # Filter by time window if specified
        points = list(self._metrics[name])
        if window_minutes:
            cutoff = datetime.now() - timedelta(minutes=window_minutes)
            points = [p for p in points if p.timestamp >= cutoff]

        if not points:
            return None

        values = [p.value for p in points]
        values.sort()

        # Calculate statistics
        count = len(values)
        mean = sum(values) / count
        min_val = values[0]
        max_val = values[-1]

        # Calculate standard deviation
        variance = sum((x - mean) ** 2 for x in values) / count
        std_dev = variance**0.5

        # Calculate percentiles
        p50_idx = int(count * 0.5)
        p90_idx = int(count * 0.9)
        p99_idx = int(count * 0.99)

        window_duration = points[-1].timestamp - points[0].timestamp

        return MetricSummary(
            name=name,
            count=count,
            mean=mean,
            min_value=min_val,
            max_value=max_val,
            std_dev=std_dev,
            percentile_50=values[p50_idx],
            percentile_90=values[p90_idx],
            percentile_99=values[p99_idx],
            latest_value=points[-1].value,
            window_duration=window_duration,
        )

    def get_all_metrics(self) -> Dict[str, List[MetricPoint]]:
        """Get all current metrics.

        Returns:
            Dictionary mapping metric names to lists of data points
        """
        return {name: list(points) for name, points in self._metrics.items()}

    def get_counters(self) -> Dict[str, float]:
        """Get all counter values."""
        return self._counters.copy()

    def get_gauges(self) -> Dict[str, float]:
        """Get all gauge values."""
        return self._gauges.copy()

    def generate_report(self) -> str:
        """Generate a human-readable metrics report.

        Returns:
            Formatted metrics report
        """
        lines = ["=== Monitoring Metrics Report ===", ""]

        # System metrics
        lines.append("System Metrics:")
        uptime = time.time() - self._gauges.get("monitoring.start_time", time.time())
        lines.append(f"  Uptime: {timedelta(seconds=int(uptime))}")
        lines.append(f"  Total Cycles: {self._counters.get('cycles.total', 0):.0f}")
        lines.append(f"  Total Errors: {self._counters.get('errors.total', 0):.0f}")
        lines.append("")

        # Agent metrics
        lines.append("Agent Metrics:")
        lines.append(f"  Total: {self._gauges.get('agents.total', 0):.0f}")
        lines.append(f"  Healthy: {self._gauges.get('agents.healthy', 0):.0f}")
        lines.append(f"  Idle: {self._gauges.get('agents.idle', 0):.0f}")
        lines.append(f"  Crashed: {self._gauges.get('agents.crashed', 0):.0f}")
        lines.append("")

        # Performance metrics
        lines.append("Performance Metrics:")

        cycle_summary = self.get_metric_summary("histogram.cycle.duration", window_minutes=10)
        if cycle_summary:
            lines.append("  Cycle Duration (last 10 min):")
            lines.append(f"    Mean: {cycle_summary.mean:.3f}s")
            lines.append(f"    P50: {cycle_summary.percentile_50:.3f}s")
            lines.append(f"    P90: {cycle_summary.percentile_90:.3f}s")
            lines.append(f"    P99: {cycle_summary.percentile_99:.3f}s")

        agents_per_sec = self._gauges.get("monitoring.agents_per_second", 0)
        lines.append(f"  Agents/Second: {agents_per_sec:.2f}")
        lines.append("")

        # Timer metrics
        timer_metrics = [m for m in self._metrics.keys() if m.startswith("histogram.timer.")]
        if timer_metrics:
            lines.append("Timer Metrics:")
            for metric in timer_metrics:
                timer_name = metric.replace("histogram.timer.", "")
                summary = self.get_metric_summary(metric, window_minutes=10)
                if summary:
                    lines.append(f"  {timer_name}:")
                    lines.append(f"    Mean: {summary.mean:.3f}s")
                    lines.append(f"    P90: {summary.percentile_90:.3f}s")
            lines.append("")

        return "\n".join(lines)

    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            Metrics in Prometheus text format
        """
        lines = []

        # Export counters
        for name, value in self._counters.items():
            metric_name = f"tmux_orchestrator_{name.replace('.', '_')}"
            lines.append(f"# TYPE {metric_name} counter")
            lines.append(f"{metric_name} {value}")

        # Export gauges
        for name, value in self._gauges.items():
            metric_name = f"tmux_orchestrator_{name.replace('.', '_')}"
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f"{metric_name} {value}")

        # Export histogram summaries
        for name in self._histograms:
            metric_name = f"tmux_orchestrator_{name.replace('.', '_')}"
            summary = self.get_metric_summary(f"histogram.{name}")
            if summary:
                lines.append(f"# TYPE {metric_name} summary")
                lines.append(f"{metric_name}_count {summary.count}")
                lines.append(f"{metric_name}_sum {summary.mean * summary.count}")
                lines.append(f'{metric_name}{{quantile="0.5"}} {summary.percentile_50}')
                lines.append(f'{metric_name}{{quantile="0.9"}} {summary.percentile_90}')
                lines.append(f'{metric_name}{{quantile="0.99"}} {summary.percentile_99}')

        return "\n".join(lines)

    def _clean_old_metrics(self, name: str) -> None:
        """Remove metrics older than retention period.

        Args:
            name: Metric name to clean
        """
        if name not in self._metrics:
            return

        cutoff = datetime.now() - timedelta(minutes=self.retention_minutes)

        # Remove old points from the left of the deque
        while self._metrics[name] and self._metrics[name][0].timestamp < cutoff:
            self._metrics[name].popleft()
