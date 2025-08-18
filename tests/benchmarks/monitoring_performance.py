#!/usr/bin/env python3
"""
Continuous performance benchmarking for monitoring system.

This script runs performance benchmarks and tracks results over time,
allowing detection of performance regressions.
"""

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tmux_orchestrator.core.config import Config  # noqa: E402
from tmux_orchestrator.core.monitoring.component_manager import ComponentManager  # noqa: E402
from tmux_orchestrator.core.monitoring.types import AgentInfo, IdleAnalysis, IdleType  # noqa: E402
from tmux_orchestrator.utils.tmux import TMUXManager  # noqa: E402


class PerformanceBenchmark:
    """Performance benchmark runner for monitoring system."""

    def __init__(self, results_dir: str = "tests/benchmarks/results"):
        """Initialize benchmark runner.

        Args:
            results_dir: Directory to store benchmark results
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Configuration
        self.agent_counts = [10, 25, 50, 75, 100, 150, 200]
        self.iterations = 5  # Number of iterations per test

    def create_mock_agents(self, count: int) -> list[AgentInfo]:
        """Create mock agents for testing.

        Args:
            count: Number of agents to create

        Returns:
            List of mock AgentInfo objects
        """
        agents = []
        sessions = max(5, count // 20)  # Distribute across sessions

        for i in range(count):
            session_num = i % sessions
            window_num = i // sessions
            agent = AgentInfo(
                target=f"session-{session_num}:{window_num}",
                session=f"session-{session_num}",
                window=str(window_num),
                name=f"agent-{i}",
                type="developer" if i % 3 == 0 else "qa" if i % 3 == 1 else "pm",
                status="active",
            )
            agents.append(agent)
        return agents

    def create_mock_analysis(self, agent_num: int) -> IdleAnalysis:
        """Create mock analysis result based on agent number.

        Args:
            agent_num: Agent number for determining state

        Returns:
            Mock IdleAnalysis object
        """
        # Create varied states: 20% error, 30% idle, 50% active
        if agent_num % 5 == 0:  # Error state
            return Mock(
                spec=IdleAnalysis,
                is_idle=True,
                idle_type=IdleType.ERROR_STATE,
                error_detected=True,
                error_type="rate_limit",
                content_hash=f"hash_{time.time()}",
                confidence=0.9,
            )
        elif agent_num % 3 == 0:  # Idle state
            return Mock(
                spec=IdleAnalysis,
                is_idle=True,
                idle_type=IdleType.NEWLY_IDLE,
                error_detected=False,
                error_type=None,
                content_hash=f"hash_{time.time()}",
                confidence=0.85,
            )
        else:  # Active state
            return Mock(
                spec=IdleAnalysis,
                is_idle=False,
                idle_type=IdleType.UNKNOWN,
                error_detected=False,
                error_type=None,
                content_hash=f"hash_{time.time()}",
                confidence=0.95,
            )

    def run_benchmark(self, agent_count: int) -> dict[str, float]:
        """Run performance benchmark for specific agent count.

        Args:
            agent_count: Number of agents to test

        Returns:
            Benchmark results
        """
        # Setup
        tmux = Mock(spec=TMUXManager)
        config = Mock(spec=Config)
        component_manager = ComponentManager(tmux, config)

        agents = self.create_mock_agents(agent_count)
        cycle_times = []

        # Mock analysis function
        def mock_analyze(target):
            agent_num = int(target.split(":")[1])
            return self.create_mock_analysis(agent_num)

        # Run iterations
        for _ in range(self.iterations):
            with (
                patch.object(component_manager.agent_monitor, "discover_agents", return_value=agents),
                patch.object(component_manager.agent_monitor, "analyze_agent_content", side_effect=mock_analyze),
                patch.object(component_manager.state_tracker, "track_session_agent"),
                patch.object(component_manager.state_tracker, "update_agent_state"),
                patch.object(component_manager.notification_manager, "notify_agent_idle"),
                patch.object(component_manager.notification_manager, "notify_agent_crash"),
                patch.object(component_manager.notification_manager, "notify_recovery_needed"),
                patch.object(
                    component_manager.notification_manager, "send_queued_notifications", return_value=agent_count // 5
                ),
                patch.object(component_manager, "_check_team_idle_status"),
            ):
                start_time = time.perf_counter()
                result = component_manager.execute_monitoring_cycle()
                end_time = time.perf_counter()

                if result.success:
                    cycle_times.append(end_time - start_time)

        # Calculate statistics
        return {
            "agent_count": agent_count,
            "avg_time": statistics.mean(cycle_times),
            "min_time": min(cycle_times),
            "max_time": max(cycle_times),
            "std_dev": statistics.stdev(cycle_times) if len(cycle_times) > 1 else 0,
            "p95_time": sorted(cycle_times)[int(len(cycle_times) * 0.95)],
            "iterations": len(cycle_times),
        }

    def run_all_benchmarks(self) -> list[dict[str, float]]:
        """Run all performance benchmarks.

        Returns:
            List of benchmark results
        """
        results = []

        print("Running performance benchmarks...")
        print(f"Iterations per test: {self.iterations}")
        print("-" * 60)

        for count in self.agent_counts:
            print(f"Testing with {count} agents...", end="", flush=True)
            result = self.run_benchmark(count)
            results.append(result)
            print(f" avg: {result['avg_time']:.4f}s, p95: {result['p95_time']:.4f}s")

        print("-" * 60)
        return results

    def save_results(self, results: list[dict[str, float]], commit_sha: str = None) -> str:
        """Save benchmark results to file.

        Args:
            results: Benchmark results
            commit_sha: Git commit SHA for tracking

        Returns:
            Path to results file
        """
        timestamp = datetime.now().isoformat()

        # Get git info if not provided
        if not commit_sha:
            try:
                import subprocess

                commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()[:8]
            except Exception:
                commit_sha = "unknown"

        # Create results document
        document = {
            "timestamp": timestamp,
            "commit": commit_sha,
            "iterations": self.iterations,
            "results": results,
            "summary": {"total_tests": len(results), "avg_scaling_factor": self._calculate_scaling_factor(results)},
        }

        # Save to timestamped file
        filename = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.results_dir / filename

        with open(filepath, "w") as f:
            json.dump(document, f, indent=2)

        # Also update latest.json
        latest_path = self.results_dir / "latest.json"
        with open(latest_path, "w") as f:
            json.dump(document, f, indent=2)

        return str(filepath)

    def _calculate_scaling_factor(self, results: list[dict[str, float]]) -> float:
        """Calculate scaling factor from 10 to 100 agents.

        Args:
            results: Benchmark results

        Returns:
            Scaling factor
        """
        time_10 = next((r["avg_time"] for r in results if r["agent_count"] == 10), None)
        time_100 = next((r["avg_time"] for r in results if r["agent_count"] == 100), None)

        if time_10 and time_100:
            return time_100 / time_10
        return 0

    def compare_with_baseline(self, results: list[dict[str, float]], baseline_file: str = None) -> dict[str, Any]:
        """Compare results with baseline.

        Args:
            results: Current benchmark results
            baseline_file: Path to baseline results file

        Returns:
            Comparison results
        """
        if not baseline_file:
            baseline_file = self.results_dir / "baseline.json"

        if not Path(baseline_file).exists():
            print(f"No baseline found at {baseline_file}")
            return {"status": "no_baseline"}

        with open(baseline_file) as f:
            baseline = json.load(f)

        comparison = {
            "status": "compared",
            "baseline_commit": baseline.get("commit", "unknown"),
            "baseline_date": baseline.get("timestamp", "unknown"),
            "regressions": [],
            "improvements": [],
        }

        # Compare each agent count
        for current in results:
            agent_count = current["agent_count"]
            baseline_result = next((r for r in baseline["results"] if r["agent_count"] == agent_count), None)

            if baseline_result:
                diff_pct = (current["avg_time"] - baseline_result["avg_time"]) / baseline_result["avg_time"] * 100

                if diff_pct > 10:  # >10% slower is regression
                    comparison["regressions"].append(
                        {
                            "agent_count": agent_count,
                            "baseline": baseline_result["avg_time"],
                            "current": current["avg_time"],
                            "diff_pct": diff_pct,
                        }
                    )
                elif diff_pct < -10:  # >10% faster is improvement
                    comparison["improvements"].append(
                        {
                            "agent_count": agent_count,
                            "baseline": baseline_result["avg_time"],
                            "current": current["avg_time"],
                            "diff_pct": abs(diff_pct),
                        }
                    )

        return comparison

    def update_baseline(self, results_file: str) -> None:
        """Update baseline with specified results.

        Args:
            results_file: Path to results file to use as baseline
        """
        with open(results_file) as f:
            results = json.load(f)

        baseline_path = self.results_dir / "baseline.json"
        with open(baseline_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"Baseline updated from {results_file}")

    def generate_report(self, results: list[dict[str, float]], comparison: dict[str, Any] = None) -> str:
        """Generate performance report.

        Args:
            results: Benchmark results
            comparison: Comparison with baseline

        Returns:
            Report text
        """
        report = ["# Performance Benchmark Report", ""]
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Iterations per test: {self.iterations}")
        report.append("")

        # Results table
        report.append("## Results")
        report.append("| Agents | Avg Time | Min Time | Max Time | P95 Time | Std Dev |")
        report.append("|--------|----------|----------|----------|----------|---------|")

        for r in results:
            report.append(
                f"| {r['agent_count']:6d} | "
                f"{r['avg_time']:8.4f} | "
                f"{r['min_time']:8.4f} | "
                f"{r['max_time']:8.4f} | "
                f"{r['p95_time']:8.4f} | "
                f"{r['std_dev']:7.4f} |"
            )

        report.append("")

        # Scaling analysis
        scaling_factor = self._calculate_scaling_factor(results)
        report.append("## Scaling Analysis")
        report.append(f"Scaling factor (10 to 100 agents): {scaling_factor:.2f}x")

        if scaling_factor < 10:
            report.append("✅ Scaling is better than linear!")
        elif scaling_factor < 15:
            report.append("⚠️ Scaling is approximately linear")
        else:
            report.append("❌ Scaling needs improvement")

        # Comparison with baseline
        if comparison and comparison["status"] == "compared":
            report.append("")
            report.append("## Baseline Comparison")
            report.append(f"Baseline: {comparison['baseline_commit']} ({comparison['baseline_date']})")

            if comparison["regressions"]:
                report.append("")
                report.append("### ❌ Performance Regressions")
                for reg in comparison["regressions"]:
                    report.append(
                        f"- {reg['agent_count']} agents: "
                        f"{reg['baseline']:.4f}s → {reg['current']:.4f}s "
                        f"(+{reg['diff_pct']:.1f}%)"
                    )

            if comparison["improvements"]:
                report.append("")
                report.append("### ✅ Performance Improvements")
                for imp in comparison["improvements"]:
                    report.append(
                        f"- {imp['agent_count']} agents: "
                        f"{imp['baseline']:.4f}s → {imp['current']:.4f}s "
                        f"(-{imp['diff_pct']:.1f}%)"
                    )

            if not comparison["regressions"] and not comparison["improvements"]:
                report.append("")
                report.append("✅ Performance is stable compared to baseline")

        return "\n".join(report)


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(description="Run monitoring performance benchmarks")
    parser.add_argument("--update-baseline", action="store_true", help="Update baseline with current results")
    parser.add_argument("--baseline", type=str, help="Path to baseline file for comparison")
    parser.add_argument("--output", type=str, help="Output directory for results")
    parser.add_argument("--commit", type=str, help="Git commit SHA for tracking")

    args = parser.parse_args()

    # Run benchmarks
    benchmark = PerformanceBenchmark(args.output or "tests/benchmarks/results")
    results = benchmark.run_all_benchmarks()

    # Save results
    results_file = benchmark.save_results(results, args.commit)
    print(f"\nResults saved to: {results_file}")

    # Compare with baseline
    comparison = benchmark.compare_with_baseline(results, args.baseline)

    # Generate report
    report = benchmark.generate_report(results, comparison)
    print("\n" + report)

    # Update baseline if requested
    if args.update_baseline:
        benchmark.update_baseline(results_file)

    # Exit with error if regressions found
    if comparison.get("regressions"):
        print("\n⚠️ Performance regressions detected!")
        sys.exit(1)
    else:
        print("\n✅ All performance checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
