"""Performance benchmarking utilities for Sprint 2 optimization analysis."""

import json
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List


class PerformanceBenchmarker:
    """Comprehensive performance benchmarking for CLI commands."""

    def __init__(self, iterations: int = 3):
        """Initialize benchmarker with specified iterations."""
        self.iterations = iterations
        self.results = {}

    def benchmark_command(self, command_args: List[str], name: str = None) -> Dict[str, Any]:
        """Benchmark a CLI command execution."""
        if not name:
            name = " ".join(command_args[:2])

        print(f"Benchmarking {name}...")
        times = []
        outputs = []

        for i in range(self.iterations):
            start_time = time.time()
            try:
                result = subprocess.run(command_args, capture_output=True, text=True, timeout=30)
                execution_time = (time.time() - start_time) * 1000  # Convert to ms
                times.append(execution_time)

                # Try to parse JSON output for structured data
                try:
                    parsed_output = json.loads(result.stdout) if result.stdout else {}
                    outputs.append(parsed_output)
                except json.JSONDecodeError:
                    outputs.append({"raw_output": result.stdout})

            except subprocess.TimeoutExpired:
                times.append(30000)  # 30 second timeout
                outputs.append({"error": "timeout"})
            except Exception as e:
                times.append(float("inf"))
                outputs.append({"error": str(e)})

        # Calculate statistics
        valid_times = [t for t in times if t != float("inf") and t < 30000]

        benchmark_result = {
            "command": " ".join(command_args),
            "iterations": self.iterations,
            "times_ms": times,
            "valid_runs": len(valid_times),
            "avg_time_ms": statistics.mean(valid_times) if valid_times else float("inf"),
            "min_time_ms": min(valid_times) if valid_times else float("inf"),
            "max_time_ms": max(valid_times) if valid_times else float("inf"),
            "median_time_ms": statistics.median(valid_times) if valid_times else float("inf"),
            "stdev_ms": statistics.stdev(valid_times) if len(valid_times) > 1 else 0,
            "outputs": outputs,
            "success_rate": len(valid_times) / self.iterations * 100,
        }

        self.results[name] = benchmark_result
        return benchmark_result

    def benchmark_sprint2_commands(self) -> Dict[str, Any]:
        """Benchmark all Sprint 2 optimized commands."""

        print("🚀 Sprint 2 Performance Benchmark Suite")
        print("=" * 50)

        # Core optimized commands
        commands_to_test = [
            (["python", "-m", "tmux_orchestrator.cli", "list", "--json"], "list_command"),
            (["python", "-m", "tmux_orchestrator.cli", "status", "--json"], "status_command"),
            (["python", "-m", "tmux_orchestrator.cli", "reflect", "--format", "json"], "reflect_command"),
        ]

        # Test quick-deploy validation (dry run would be ideal)
        commands_to_test.append(
            (
                [
                    "python",
                    "-m",
                    "tmux_orchestrator.cli",
                    "quick-deploy",
                    "frontend",
                    "2",
                    "--project-name",
                    "benchmark-test",
                    "--json",
                ],
                "quick_deploy_command",
            )
        )

        benchmark_results = {}

        for command_args, name in commands_to_test:
            try:
                result = self.benchmark_command(command_args, name)
                benchmark_results[name] = result

                # Print immediate results
                if result["valid_runs"] > 0:
                    print(
                        f"✅ {name}: {result['avg_time_ms']:.1f}ms avg ({result['min_time_ms']:.1f}-{result['max_time_ms']:.1f}ms)"
                    )
                else:
                    print(f"❌ {name}: Failed all runs")

            except Exception as e:
                print(f"❌ {name}: Benchmark failed - {e}")
                benchmark_results[name] = {"error": str(e)}

        # Clean up any test sessions
        try:
            subprocess.run(["tmux", "kill-session", "-t", "benchmark-test-frontend"], capture_output=True, timeout=5)
        except:
            pass

        return benchmark_results

    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report."""

        report = []
        report.append("# Sprint 2 Performance Benchmark Report")
        report.append("=" * 50)
        report.append("")

        # Performance targets
        targets = {
            "list_command": 500,
            "status_command": 500,
            "reflect_command": 1000,
            "quick_deploy_command": 2000,  # Allowing higher target due to actual deployment
        }

        report.append("## Performance Targets vs Results")
        report.append("")
        report.append("| Command | Target | Actual | Status | Improvement |")
        report.append("|---------|--------|---------|--------|-------------|")

        baseline_times = {
            "list_command": 4130,  # Original 4.13s
            "status_command": 2000,  # Estimated baseline
            "reflect_command": 1500,  # Estimated baseline
            "quick_deploy_command": 1570,  # Original 1.57s (CLI overhead only)
        }

        for name, result in self.results.items():
            if isinstance(result, dict) and "avg_time_ms" in result:
                target = targets.get(name, 1000)
                actual = result["avg_time_ms"]
                baseline = baseline_times.get(name, actual)

                # Determine status
                if actual <= target:
                    status = "✅ PASS"
                elif actual <= target * 1.5:
                    status = "⚠️ CLOSE"
                else:
                    status = "❌ MISS"

                # Calculate improvement
                improvement = ((baseline - actual) / baseline * 100) if baseline > 0 else 0
                improvement_str = f"{improvement:+.1f}%" if improvement != 0 else "NEW"

                report.append(f"| {name} | {target}ms | {actual:.1f}ms | {status} | {improvement_str} |")

        report.append("")
        report.append("## Detailed Results")
        report.append("")

        for name, result in self.results.items():
            if isinstance(result, dict) and "avg_time_ms" in result:
                report.append(f"### {name}")
                report.append(f"- Average: {result['avg_time_ms']:.1f}ms")
                report.append(f"- Range: {result['min_time_ms']:.1f}ms - {result['max_time_ms']:.1f}ms")
                report.append(f"- Success Rate: {result['success_rate']:.1f}%")
                report.append(f"- Standard Deviation: {result['stdev_ms']:.1f}ms")
                report.append("")

        # Optimization recommendations
        report.append("## Optimization Recommendations")
        report.append("")

        for name, result in self.results.items():
            if isinstance(result, dict) and "avg_time_ms" in result:
                target = targets.get(name, 1000)
                actual = result["avg_time_ms"]

                if actual > target:
                    gap = actual - target
                    report.append(f"- **{name}**: {gap:.1f}ms over target")

                    if name == "list_command":
                        report.append("  - Consider further caching optimizations")
                        report.append("  - Implement lazy loading for agent status")
                    elif name == "quick_deploy_command":
                        report.append("  - Focus on CLI overhead, not deployment time")
                        report.append("  - Consider async deployment initiation")

                    report.append("")

        return "\\n".join(report)


def run_sprint2_benchmarks() -> None:
    """Run complete Sprint 2 benchmark suite."""
    print("Starting Sprint 2 Performance Analysis...")

    benchmarker = PerformanceBenchmarker(iterations=3)
    results = benchmarker.benchmark_sprint2_commands()

    # Generate and save report
    report = benchmarker.generate_performance_report()

    # Save to file
    report_path = Path("sprint2_performance_report.md")
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\\n📊 Complete report saved to: {report_path}")
    print("\\n" + "=" * 50)
    print(benchmarker.generate_performance_report())


if __name__ == "__main__":
    run_sprint2_benchmarks()
