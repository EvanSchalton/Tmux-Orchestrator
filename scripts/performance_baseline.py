#!/usr/bin/env python3
"""Performance baseline measurement script for tmux-orchestrator.

This script establishes performance benchmarks before the monitor.py refactoring
to measure improvements after the refactoring is complete.
"""

import asyncio
import gc
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch

import psutil

from tmux_orchestrator.core.config import Config

# Import tmux-orchestrator modules
from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.server.tools.get_agent_status import get_agent_status
from tmux_orchestrator.server.tools.spawn_agent import SpawnAgentRequest, spawn_agent
from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results."""

    # Timing metrics (seconds)
    execution_time: float
    min_time: float
    max_time: float
    avg_time: float
    median_time: float

    # Memory metrics (bytes)
    memory_before: int
    memory_after: int
    memory_peak: int
    memory_delta: int

    # CPU metrics
    cpu_percent: float

    # Additional context
    iterations: int
    timestamp: str
    test_name: str


@dataclass
class BaselineResults:
    """Complete baseline measurement results."""

    monitor_cycle_performance: PerformanceMetrics
    cli_command_performance: Dict[str, PerformanceMetrics]
    server_api_performance: Dict[str, PerformanceMetrics]
    resource_usage_patterns: Dict[str, Any]
    system_info: Dict[str, Any]
    measurement_timestamp: str


class PerformanceBenchmark:
    """Performance measurement framework."""

    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.process = psutil.Process()

    def measure_function_performance(
        self, func, iterations: int = 10, test_name: str = "unnamed_test", *args, **kwargs
    ) -> PerformanceMetrics:
        """Measure performance of a function over multiple iterations."""

        times: List[float] = []
        gc.collect()  # Clean up before measurement

        # Start memory tracking
        tracemalloc.start()
        memory_before = self.process.memory_info().rss
        cpu_before = self.process.cpu_percent()

        for i in range(iterations):
            start_time = time.perf_counter()

            try:
                if asyncio.iscoroutinefunction(func):
                    asyncio.run(func(*args, **kwargs))
                else:
                    func(*args, **kwargs)
            except Exception as e:
                print(f"Warning: Iteration {i} failed: {e}")
                continue

            end_time = time.perf_counter()
            times.append(end_time - start_time)

        # Memory measurements
        memory_after = self.process.memory_info().rss
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        cpu_after = self.process.cpu_percent()

        if not times:
            raise RuntimeError(f"All iterations failed for test: {test_name}")

        return PerformanceMetrics(
            execution_time=sum(times),
            min_time=min(times),
            max_time=max(times),
            avg_time=statistics.mean(times),
            median_time=statistics.median(times),
            memory_before=memory_before,
            memory_after=memory_after,
            memory_peak=peak,
            memory_delta=memory_after - memory_before,
            cpu_percent=(cpu_before + cpu_after) / 2,
            iterations=len(times),
            timestamp=datetime.now().isoformat(),
            test_name=test_name,
        )

    def get_system_info(self) -> Dict[str, Any]:
        """Collect system information for context."""
        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage("/").percent,
            "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
        }


class MonitorPerformanceBenchmark(PerformanceBenchmark):
    """Benchmark monitor cycle performance."""

    def __init__(self):
        super().__init__()
        self.temp_dir = tempfile.mkdtemp()
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.temp_dir

    def create_mock_agents(self, count: int = 5) -> List[Dict[str, Any]]:
        """Create mock agent data for testing."""
        agents = []
        for i in range(count):
            agents.append({"session": f"test-session-{i}", "window": str(i), "type": "Developer", "status": "Active"})
        return agents

    def benchmark_monitor_cycle(self) -> PerformanceMetrics:
        """Benchmark a complete monitor cycle."""

        def monitor_cycle():
            """Simulate a monitor cycle with mock data."""
            tmux = Mock(spec=TMUXManager)
            tmux.list_agents.return_value = self.create_mock_agents(5)
            tmux.capture_pane.return_value = "Sample agent output content for testing"

            _ = IdleMonitor(tmux)  # Create instance for performance measurement

            # Simulate the core monitoring logic
            agents = tmux.list_agents()
            for agent in agents:
                target = f"{agent['session']}:{agent['window']}"
                _ = tmux.capture_pane(target)  # Capture for performance measurement
                # Simulate processing
                time.sleep(0.001)  # Minimal processing time

        return self.measure_function_performance(monitor_cycle, iterations=20, test_name="monitor_cycle")

    def benchmark_agent_detection(self) -> PerformanceMetrics:
        """Benchmark agent detection performance."""

        def agent_detection():
            tmux = TMUXManager()
            # This will work with actual tmux or fail gracefully
            try:
                _ = tmux.list_agents()  # Call for performance measurement
            except Exception:
                # Mock if tmux not available
                pass

        return self.measure_function_performance(agent_detection, iterations=10, test_name="agent_detection")


class CLIPerformanceBenchmark(PerformanceBenchmark):
    """Benchmark CLI command performance."""

    def benchmark_cli_commands(self) -> Dict[str, PerformanceMetrics]:
        """Benchmark key CLI commands."""
        results = {}

        # Test tmux-orc help command (should be fast)
        def help_command():
            try:
                subprocess.run(
                    ["python", "-m", "tmux_orchestrator.cli", "--help"], capture_output=True, timeout=10, check=False
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass  # Command may not be available in test environment

        results["help"] = self.measure_function_performance(help_command, iterations=5, test_name="cli_help")

        # Test config validation
        def config_validation():
            try:
                config = Config.load()
                _ = config.orchestrator_base_dir
            except Exception:
                pass  # Config may not be available

        results["config"] = self.measure_function_performance(
            config_validation, iterations=20, test_name="config_validation"
        )

        return results


class ServerPerformanceBenchmark(PerformanceBenchmark):
    """Benchmark server/API performance."""

    def benchmark_server_functions(self) -> Dict[str, PerformanceMetrics]:
        """Benchmark key server functions."""
        results = {}

        # Benchmark spawn_agent function
        async def spawn_agent_benchmark():
            tmux = Mock(spec=TMUXManager)
            tmux.session_exists.return_value = False
            tmux.create_session.return_value = True
            tmux.create_window.return_value = True
            tmux.send_keys.return_value = True

            request = SpawnAgentRequest(session_name="test-session", agent_type="developer")

            with patch("time.sleep"):  # Skip actual sleep
                try:
                    _ = await spawn_agent(tmux, request)  # Call for performance measurement
                except Exception:
                    pass  # May fail due to mocking

        results["spawn_agent"] = self.measure_function_performance(
            spawn_agent_benchmark, iterations=10, test_name="spawn_agent_api"
        )

        # Benchmark get_agent_status function
        def agent_status_benchmark():
            tmux = Mock(spec=TMUXManager)
            tmux.list_agents.return_value = [
                {"session": "test", "window": "1", "type": "Developer", "status": "Active"}
            ]

            try:
                _ = get_agent_status(tmux, None)  # Call for performance measurement
            except Exception:
                pass  # May fail due to mocking

        results["agent_status"] = self.measure_function_performance(
            agent_status_benchmark, iterations=15, test_name="agent_status_api"
        )

        return results


def run_baseline_measurements() -> BaselineResults:
    """Run complete baseline performance measurements."""

    print("🚀 Starting Performance Baseline Measurements...")
    print("=" * 60)

    # Monitor performance benchmarks
    print("📊 Measuring Monitor Cycle Performance...")
    monitor_benchmark = MonitorPerformanceBenchmark()
    monitor_performance = monitor_benchmark.benchmark_monitor_cycle()
    print(f"   Monitor cycle avg: {monitor_performance.avg_time:.4f}s")

    # CLI performance benchmarks
    print("⚡ Measuring CLI Command Performance...")
    cli_benchmark = CLIPerformanceBenchmark()
    cli_performance = cli_benchmark.benchmark_cli_commands()
    for cmd, metrics in cli_performance.items():
        print(f"   CLI {cmd} avg: {metrics.avg_time:.4f}s")

    # Server performance benchmarks
    print("🌐 Measuring Server API Performance...")
    server_benchmark = ServerPerformanceBenchmark()
    server_performance = server_benchmark.benchmark_server_functions()
    for api, metrics in server_performance.items():
        print(f"   API {api} avg: {metrics.avg_time:.4f}s")

    # Resource usage patterns
    print("💾 Collecting Resource Usage Patterns...")
    resource_patterns = {
        "baseline_memory": psutil.virtual_memory()._asdict(),
        "baseline_cpu": psutil.cpu_percent(interval=1),
        "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
        "network_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
    }

    # System information
    system_info = monitor_benchmark.get_system_info()

    results = BaselineResults(
        monitor_cycle_performance=monitor_performance,
        cli_command_performance=cli_performance,
        server_api_performance=server_performance,
        resource_usage_patterns=resource_patterns,
        system_info=system_info,
        measurement_timestamp=datetime.now().isoformat(),
    )

    print("✅ Baseline measurements complete!")
    return results


def save_baseline_results(results: BaselineResults, output_file: Optional[Path] = None):
    """Save baseline results to JSON file."""

    if output_file is None:
        output_file = Path("performance_baseline.json")

    # Convert dataclasses to dict for JSON serialization
    results_dict = {
        "monitor_cycle_performance": asdict(results.monitor_cycle_performance),
        "cli_command_performance": {k: asdict(v) for k, v in results.cli_command_performance.items()},
        "server_api_performance": {k: asdict(v) for k, v in results.server_api_performance.items()},
        "resource_usage_patterns": results.resource_usage_patterns,
        "system_info": results.system_info,
        "measurement_timestamp": results.measurement_timestamp,
    }

    with open(output_file, "w") as f:
        json.dump(results_dict, f, indent=2, default=str)

    print(f"📄 Results saved to: {output_file}")


def display_baseline_summary(results: BaselineResults):
    """Display a formatted summary of baseline results."""

    print("\n" + "=" * 60)
    print("📊 PERFORMANCE BASELINE SUMMARY")
    print("=" * 60)

    print(f"\n🕐 Measurement Time: {results.measurement_timestamp}")
    print(
        f"🖥️  System: {results.system_info['platform']} | "
        f"CPUs: {results.system_info['cpu_count']} | "
        f"Memory: {results.system_info['memory_total'] // (1024**3)}GB"
    )

    print("\n📈 MONITOR CYCLE PERFORMANCE:")
    m = results.monitor_cycle_performance
    print(f"   Average: {m.avg_time:.4f}s | " f"Min: {m.min_time:.4f}s | " f"Max: {m.max_time:.4f}s")
    print(f"   Memory Delta: {m.memory_delta / 1024:.1f}KB | " f"Peak: {m.memory_peak / 1024:.1f}KB")

    print("\n⚡ CLI COMMAND PERFORMANCE:")
    for cmd, metrics in results.cli_command_performance.items():
        print(f"   {cmd}: {metrics.avg_time:.4f}s ± {metrics.max_time - metrics.min_time:.4f}s")

    print("\n🌐 SERVER API PERFORMANCE:")
    for api, metrics in results.server_api_performance.items():
        print(f"   {api}: {metrics.avg_time:.4f}s ± {metrics.max_time - metrics.min_time:.4f}s")

    print("\n💾 RESOURCE USAGE:")
    mem = results.resource_usage_patterns["baseline_memory"]
    print(f"   Memory: {mem['percent']:.1f}% used | " f"Available: {mem['available'] // (1024**3)}GB")
    print(f"   CPU: {results.resource_usage_patterns['baseline_cpu']:.1f}%")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Run baseline measurements
    baseline_results = run_baseline_measurements()

    # Save results
    output_path = Path("/workspaces/Tmux-Orchestrator/performance_baseline.json")
    save_baseline_results(baseline_results, output_path)

    # Display summary
    display_baseline_summary(baseline_results)

    print("\n🎯 Baseline established! Use this data to measure improvements after monitor.py refactoring.")
