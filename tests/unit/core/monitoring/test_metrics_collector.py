"""
Comprehensive tests for MetricsCollector component.

Tests metrics collection, aggregation, reporting, and export functionality.
"""

import logging
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.metrics_collector import MetricPoint, MetricsCollector
from tmux_orchestrator.core.monitoring.types import MonitorStatus


class TestMetricsCollectorInitialization:
    """Test MetricsCollector initialization and configuration."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)

    def test_initialization_default_params(self):
        """Test initialization with default parameters."""
        collector = MetricsCollector(self.config, self.logger)

        assert collector.config == self.config
        assert collector.logger == self.logger
        assert collector.retention_minutes == 60
        assert collector.max_points_per_metric == 1000
        assert isinstance(collector._metrics, dict)
        assert isinstance(collector._counters, dict)
        assert isinstance(collector._gauges, dict)
        assert isinstance(collector._histograms, dict)

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        collector = MetricsCollector(self.config, self.logger, retention_minutes=30, max_points_per_metric=500)

        assert collector.retention_minutes == 30
        assert collector.max_points_per_metric == 500

    def test_initialize_success(self):
        """Test successful initialization."""
        collector = MetricsCollector(self.config, self.logger)

        result = collector.initialize()

        assert result is True
        self.logger.info.assert_called_with("Initializing MetricsCollector")

        # Check standard metrics are set
        assert "monitoring.enabled" in collector._gauges
        assert "monitoring.start_time" in collector._gauges

    def test_initialize_failure(self):
        """Test initialization failure handling."""
        collector = MetricsCollector(self.config, self.logger)

        with patch.object(collector, "set_gauge", side_effect=Exception("Init error")):
            result = collector.initialize()

            assert result is False
            self.logger.error.assert_called()

    def test_cleanup(self):
        """Test cleanup functionality."""
        collector = MetricsCollector(self.config, self.logger)

        # Add some data
        collector._metrics["test"] = []
        collector._counters["test"] = 5
        collector._gauges["test"] = 10
        collector._histograms["test"] = [1, 2, 3]
        collector._timers["test"] = time.time()

        collector.cleanup()

        assert len(collector._metrics) == 0
        assert len(collector._counters) == 0
        assert len(collector._gauges) == 0
        assert len(collector._histograms) == 0
        assert len(collector._timers) == 0


class TestBasicMetricOperations:
    """Test basic metric recording operations."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.collector = MetricsCollector(self.config, self.logger)

    def test_record_metric_basic(self):
        """Test basic metric recording."""
        self.collector.record_metric("test_metric", 42.5)

        assert "test_metric" in self.collector._metrics
        points = list(self.collector._metrics["test_metric"])
        assert len(points) == 1
        assert points[0].value == 42.5
        assert isinstance(points[0].timestamp, datetime)

    def test_record_metric_with_labels(self):
        """Test metric recording with labels."""
        labels = {"service": "monitoring", "environment": "test"}
        self.collector.record_metric("test_metric", 100, labels)

        points = list(self.collector._metrics["test_metric"])
        assert len(points) == 1
        assert points[0].labels == labels

    def test_increment_counter(self):
        """Test counter increment."""
        self.collector.increment_counter("api_calls")
        self.collector.increment_counter("api_calls", 5)

        assert self.collector._counters["api_calls"] == 6

        # Should also create metric points
        assert "counter.api_calls" in self.collector._metrics

    def test_set_gauge(self):
        """Test gauge setting."""
        self.collector.set_gauge("memory_usage", 512.5)

        assert self.collector._gauges["memory_usage"] == 512.5

        # Should also create metric points
        assert "gauge.memory_usage" in self.collector._metrics

    def test_record_histogram(self):
        """Test histogram recording."""
        values = [1.0, 2.5, 3.2, 1.8, 4.1]

        for value in values:
            self.collector.record_histogram("response_time", value)

        assert self.collector._histograms["response_time"] == values
        assert "histogram.response_time" in self.collector._metrics

    def test_histogram_size_limit(self):
        """Test histogram size limiting."""
        collector = MetricsCollector(self.config, self.logger, max_points_per_metric=3)

        # Add more values than the limit
        for i in range(5):
            collector.record_histogram("test", float(i))

        # Should keep only the last 3 values
        assert len(collector._histograms["test"]) == 3
        assert collector._histograms["test"] == [2.0, 3.0, 4.0]


class TestTimerOperations:
    """Test timer functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.collector = MetricsCollector(self.config, self.logger)

    def test_timer_basic_operation(self):
        """Test basic timer start/stop operation."""
        self.collector.start_timer("operation")

        # Simulate some work
        time.sleep(0.01)

        duration = self.collector.stop_timer("operation")

        assert duration is not None
        assert duration > 0
        assert "timer.operation" not in self.collector._timers
        assert "histogram.timer.operation" in self.collector._metrics

    def test_stop_nonexistent_timer(self):
        """Test stopping a timer that doesn't exist."""
        duration = self.collector.stop_timer("nonexistent")

        assert duration is None
        self.logger.warning.assert_called_with("Timer nonexistent not found")

    def test_multiple_timers(self):
        """Test multiple concurrent timers."""
        self.collector.start_timer("timer1")
        self.collector.start_timer("timer2")

        time.sleep(0.01)

        duration1 = self.collector.stop_timer("timer1")
        duration2 = self.collector.stop_timer("timer2")

        assert duration1 is not None
        assert duration2 is not None
        assert len(self.collector._timers) == 0


class TestMonitorCycleRecording:
    """Test monitor cycle metrics recording."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.collector = MetricsCollector(self.config, self.logger)

    def test_record_monitor_cycle(self):
        """Test recording monitor cycle metrics."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=0.05)

        status = MonitorStatus(
            is_running=True,
            active_agents=10,
            idle_agents=3,
            last_cycle_time=0.05,
            uptime=timedelta(hours=2),
            cycle_count=100,
            errors_detected=2,
            start_time=start_time,
            end_time=end_time,
        )

        self.collector.record_monitor_cycle(status)

        # Check gauge metrics (based on actual MonitorStatus fields)
        assert self.collector._gauges["agents.total"] == 10  # active_agents
        assert self.collector._gauges["agents.idle"] == 3

        # Check counter metrics
        assert self.collector._counters["errors.total"] == 2
        assert self.collector._counters["cycles.total"] == 1

        # Check histogram metrics
        assert "histogram.cycle.duration" in self.collector._metrics

        # Check calculated metrics
        agents_per_second = self.collector._gauges.get("monitoring.agents_per_second", 0)
        assert agents_per_second == 200  # 10 / 0.05

    def test_record_monitor_cycle_no_timing(self):
        """Test recording cycle without timing information."""
        status = MonitorStatus(
            is_running=True,
            active_agents=5,
            idle_agents=2,
            last_cycle_time=0.0,
            uptime=timedelta(minutes=30),
            cycle_count=50,
            errors_detected=0,
        )

        self.collector.record_monitor_cycle(status)

        # Should still record agent and counter metrics
        assert self.collector._gauges["agents.total"] == 5  # active_agents
        assert self.collector._counters["cycles.total"] == 1


class TestMetricSummaries:
    """Test metric summary generation."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.collector = MetricsCollector(self.config, self.logger)

    def test_get_metric_summary_nonexistent(self):
        """Test getting summary for non-existent metric."""
        summary = self.collector.get_metric_summary("nonexistent")
        assert summary is None

    def test_get_metric_summary_empty(self):
        """Test getting summary for empty metric."""
        self.collector._metrics["empty"] = []
        summary = self.collector.get_metric_summary("empty")
        assert summary is None

    def test_get_metric_summary_basic(self):
        """Test basic metric summary calculation."""
        # Add test data
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        base_time = datetime.now()

        for i, value in enumerate(values):
            point = MetricPoint(timestamp=base_time + timedelta(seconds=i), value=value)
            self.collector._metrics["test_metric"].append(point)

        summary = self.collector.get_metric_summary("test_metric")

        assert summary is not None
        assert summary.name == "test_metric"
        assert summary.count == 5
        assert summary.mean == 3.0
        assert summary.min_value == 1.0
        assert summary.max_value == 5.0
        assert summary.percentile_50 == 3.0
        assert summary.latest_value == 5.0

    def test_get_metric_summary_with_window(self):
        """Test metric summary with time window."""
        base_time = datetime.now()

        # Add old data (outside window)
        old_point = MetricPoint(timestamp=base_time - timedelta(minutes=30), value=100.0)
        self.collector._metrics["test_metric"].append(old_point)

        # Add recent data (inside window)
        for i in range(3):
            point = MetricPoint(timestamp=base_time - timedelta(minutes=i), value=float(i + 1))
            self.collector._metrics["test_metric"].append(point)

        # Get summary for last 10 minutes
        summary = self.collector.get_metric_summary("test_metric", window_minutes=10)

        assert summary is not None
        assert summary.count == 3  # Should exclude the old point
        assert summary.min_value == 1.0
        assert summary.max_value == 3.0

    def test_metric_summary_statistics(self):
        """Test statistical calculations in summary."""
        # Use known values for testing statistics
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        base_time = datetime.now()

        for i, value in enumerate(values):
            point = MetricPoint(timestamp=base_time + timedelta(seconds=i), value=value)
            self.collector._metrics["stats_test"].append(point)

        summary = self.collector.get_metric_summary("stats_test")

        assert summary.count == 10
        assert summary.mean == 5.5
        assert summary.min_value == 1.0
        assert summary.max_value == 10.0
        assert summary.percentile_50 == 6.0  # int(10 * 0.5) = 5, values[5] = 6.0
        assert summary.percentile_90 == 10.0  # int(10 * 0.9) = 9, values[9] = 10.0
        assert summary.percentile_99 == 10.0  # With only 10 points, P99 is the max
        assert summary.std_dev > 0  # Should have some deviation


class TestMetricRetention:
    """Test metric retention and cleanup."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.collector = MetricsCollector(self.config, self.logger, retention_minutes=1)

    @patch("tmux_orchestrator.core.monitoring.metrics_collector.datetime")
    def test_metric_cleanup(self, mock_datetime):
        """Test automatic cleanup of old metrics."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = base_time + timedelta(minutes=5)

        # Add old metric (should be cleaned)
        old_point = MetricPoint(
            timestamp=base_time,  # 5 minutes ago
            value=1.0,
        )

        # Add recent metric (should be kept)
        recent_point = MetricPoint(
            timestamp=base_time + timedelta(minutes=4, seconds=30),  # 30 seconds ago
            value=2.0,
        )

        self.collector._metrics["test"].append(old_point)
        self.collector._metrics["test"].append(recent_point)

        # Trigger cleanup
        self.collector._clean_old_metrics("test")

        # Only recent point should remain
        remaining_points = list(self.collector._metrics["test"])
        assert len(remaining_points) == 1
        assert remaining_points[0].value == 2.0

    def test_record_metric_triggers_cleanup(self):
        """Test that recording a metric triggers cleanup."""
        with patch.object(self.collector, "_clean_old_metrics") as mock_cleanup:
            self.collector.record_metric("test", 42.0)
            mock_cleanup.assert_called_once_with("test")


class TestReportGeneration:
    """Test metrics report generation."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.collector = MetricsCollector(self.config, self.logger)

        # Set up some test data
        self.collector.set_gauge("monitoring.start_time", time.time() - 3600)  # 1 hour ago
        self.collector.increment_counter("cycles.total", 100)
        self.collector.increment_counter("errors.total", 5)
        self.collector.set_gauge("agents.total", 25)
        self.collector.set_gauge("agents.healthy", 20)
        self.collector.set_gauge("agents.idle", 3)
        self.collector.set_gauge("agents.crashed", 2)
        self.collector.set_gauge("monitoring.agents_per_second", 500)

    def test_generate_report_basic(self):
        """Test basic report generation."""
        report = self.collector.generate_report()

        assert "=== Monitoring Metrics Report ===" in report
        assert "System Metrics:" in report
        assert "Agent Metrics:" in report
        assert "Performance Metrics:" in report
        assert "Total Cycles: 100" in report
        assert "Total Errors: 5" in report
        assert "Total: 25" in report
        assert "Healthy: 20" in report

    def test_generate_report_with_cycle_data(self):
        """Test report generation with cycle duration data."""
        # Add some cycle duration data
        for duration in [0.01, 0.02, 0.015, 0.025, 0.03]:
            self.collector.record_histogram("cycle.duration", duration)

        report = self.collector.generate_report()

        assert "Cycle Duration (last 10 min):" in report
        assert "Mean:" in report
        assert "P50:" in report
        assert "P90:" in report
        assert "P99:" in report

    def test_generate_report_with_timers(self):
        """Test report generation with timer metrics."""
        # Add some timer data
        for duration in [0.001, 0.002, 0.0015]:
            self.collector.record_histogram("timer.database_query", duration)

        report = self.collector.generate_report()

        assert "Timer Metrics:" in report
        assert "database_query:" in report


class TestPrometheusExport:
    """Test Prometheus format export."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.collector = MetricsCollector(self.config, self.logger)

    def test_export_prometheus_counters(self):
        """Test Prometheus export of counters."""
        self.collector.increment_counter("http_requests", 100)
        self.collector.increment_counter("errors_total", 5)

        output = self.collector.export_prometheus_format()

        assert "# TYPE tmux_orchestrator_http_requests counter" in output
        assert "tmux_orchestrator_http_requests 100" in output
        assert "# TYPE tmux_orchestrator_errors_total counter" in output
        assert "tmux_orchestrator_errors_total 5" in output

    def test_export_prometheus_gauges(self):
        """Test Prometheus export of gauges."""
        self.collector.set_gauge("memory_usage", 512.5)
        self.collector.set_gauge("cpu_usage", 75.2)

        output = self.collector.export_prometheus_format()

        assert "# TYPE tmux_orchestrator_memory_usage gauge" in output
        assert "tmux_orchestrator_memory_usage 512.5" in output
        assert "# TYPE tmux_orchestrator_cpu_usage gauge" in output
        assert "tmux_orchestrator_cpu_usage 75.2" in output

    def test_export_prometheus_histograms(self):
        """Test Prometheus export of histograms."""
        values = [0.1, 0.2, 0.15, 0.25, 0.3]
        for value in values:
            self.collector.record_histogram("response_time", value)

        output = self.collector.export_prometheus_format()

        assert "# TYPE tmux_orchestrator_response_time summary" in output
        assert "tmux_orchestrator_response_time_count 5" in output
        assert "tmux_orchestrator_response_time_sum" in output
        assert 'tmux_orchestrator_response_time{quantile="0.5"}' in output
        assert 'tmux_orchestrator_response_time{quantile="0.9"}' in output
        assert 'tmux_orchestrator_response_time{quantile="0.99"}' in output


class TestDataAccess:
    """Test data access methods."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.collector = MetricsCollector(self.config, self.logger)

    def test_get_all_metrics(self):
        """Test getting all metrics."""
        self.collector.record_metric("metric1", 10)
        self.collector.record_metric("metric2", 20)

        all_metrics = self.collector.get_all_metrics()

        assert "metric1" in all_metrics
        assert "metric2" in all_metrics
        assert len(all_metrics["metric1"]) == 1
        assert all_metrics["metric1"][0].value == 10

    def test_get_counters(self):
        """Test getting all counters."""
        self.collector.increment_counter("counter1", 5)
        self.collector.increment_counter("counter2", 10)

        counters = self.collector.get_counters()

        assert counters["counter1"] == 5
        assert counters["counter2"] == 10

        # Should be a copy
        assert counters is not self.collector._counters

    def test_get_gauges(self):
        """Test getting all gauges."""
        self.collector.set_gauge("gauge1", 100)
        self.collector.set_gauge("gauge2", 200)

        gauges = self.collector.get_gauges()

        assert gauges["gauge1"] == 100
        assert gauges["gauge2"] == 200

        # Should be a copy
        assert gauges is not self.collector._gauges


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Mock(spec=Config)
        self.logger = Mock(spec=logging.Logger)
        self.collector = MetricsCollector(self.config, self.logger)

    def test_deque_maxlen_enforcement(self):
        """Test that deque maxlen is enforced."""
        collector = MetricsCollector(self.config, self.logger, max_points_per_metric=3)

        # Add more points than the limit
        for i in range(5):
            collector.record_metric("test", float(i))

        # Should only keep the last 3 points
        points = list(collector._metrics["test"])
        assert len(points) == 3
        assert [p.value for p in points] == [2.0, 3.0, 4.0]

    def test_large_values(self):
        """Test handling of large numeric values."""
        large_value = 1e15
        self.collector.record_metric("large_metric", large_value)

        points = list(self.collector._metrics["large_metric"])
        assert points[0].value == large_value

    def test_negative_values(self):
        """Test handling of negative values."""
        self.collector.record_metric("negative", -100.5)
        self.collector.increment_counter("negative_counter", -5)
        self.collector.set_gauge("negative_gauge", -50)

        assert list(self.collector._metrics["negative"])[0].value == -100.5
        assert self.collector._counters["negative_counter"] == -5
        assert self.collector._gauges["negative_gauge"] == -50

    def test_zero_values(self):
        """Test handling of zero values."""
        self.collector.record_metric("zero", 0.0)
        self.collector.increment_counter("zero_counter", 0)
        self.collector.set_gauge("zero_gauge", 0)

        assert list(self.collector._metrics["zero"])[0].value == 0.0
        assert self.collector._counters["zero_counter"] == 0
        assert self.collector._gauges["zero_gauge"] == 0

    def test_concurrent_metric_updates(self):
        """Test concurrent updates to the same metric."""
        # This is a basic test - real concurrency would need threading
        metric_name = "concurrent_test"

        # Simulate rapid updates
        for i in range(100):
            self.collector.record_metric(metric_name, float(i))

        points = list(self.collector._metrics[metric_name])
        assert len(points) == 100
        assert points[-1].value == 99.0
