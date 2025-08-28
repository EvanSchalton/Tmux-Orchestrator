#!/usr/bin/env python3
"""
MCP Server Performance Monitoring for QA Testing Phase
Real-time performance tracking and analysis during comprehensive testing
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import psutil


@dataclass
class MCPPerformanceMetrics:
    """MCP Server performance metrics snapshot"""

    timestamp: float
    tool_response_time: float
    memory_usage_mb: float
    cpu_percent: float
    active_processes: int
    tool_success_rate: float
    error_count: int
    tools_tested: int
    concurrent_requests: int


class MCPPerformanceMonitor:
    """Real-time MCP server performance monitoring during QA testing"""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or Path(".tmux_orchestrator/logs/mcp_performance.log")
        self.metrics_history: List[MCPPerformanceMetrics] = []
        self.start_time = time.time()
        self.tool_timings: Dict[str, List[float]] = {}
        self.error_log: List[Dict] = []

        # Performance thresholds for QA validation
        self.thresholds = {
            "max_response_time": 1.0,  # 1 second max
            "max_memory_mb": 500,  # 500MB max
            "max_cpu_percent": 80,  # 80% CPU max
            "min_success_rate": 0.90,  # 90% success rate min
        }

        self.setup_logging()

    def setup_logging(self):
        """Setup performance logging"""
        self.log_path.parent.mkdir(exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(self.log_path), logging.StreamHandler()],
        )
        self.logger = logging.getLogger("mcp_performance")

    async def get_mcp_processes(self) -> List[psutil.Process]:
        """Find all MCP server processes"""
        mcp_processes = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["cmdline"] and "tmux-orc server start" in " ".join(proc.info["cmdline"]):
                    mcp_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return mcp_processes

    async def collect_metrics(self) -> MCPPerformanceMetrics:
        """Collect current performance metrics"""
        try:
            mcp_processes = await self.get_mcp_processes()

            # Aggregate process metrics
            total_memory = 0
            total_cpu = 0
            active_processes = len(mcp_processes)

            for proc in mcp_processes:
                try:
                    memory_info = proc.memory_info()
                    total_memory += memory_info.rss / 1024 / 1024  # Convert to MB
                    total_cpu += proc.cpu_percent()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Calculate tool response time (average of recent timings)
            recent_timings = []
            for tool_times in self.tool_timings.values():
                if tool_times:
                    recent_timings.extend(tool_times[-5:])  # Last 5 calls per tool

            avg_response_time = sum(recent_timings) / len(recent_timings) if recent_timings else 0.0

            # Calculate success rate
            total_tests = sum(len(times) for times in self.tool_timings.values())
            success_rate = max(0, (total_tests - len(self.error_log)) / total_tests) if total_tests > 0 else 1.0

            metrics = MCPPerformanceMetrics(
                timestamp=time.time(),
                tool_response_time=avg_response_time,
                memory_usage_mb=total_memory,
                cpu_percent=total_cpu,
                active_processes=active_processes,
                tool_success_rate=success_rate,
                error_count=len(self.error_log),
                tools_tested=len(self.tool_timings),
                concurrent_requests=0,  # TODO: Track concurrent requests
            )

            self.metrics_history.append(metrics)

            # Keep only last 1000 metrics for memory efficiency
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]

            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return MCPPerformanceMetrics(
                timestamp=time.time(),
                tool_response_time=0.0,
                memory_usage_mb=0.0,
                cpu_percent=0.0,
                active_processes=0,
                tool_success_rate=0.0,
                error_count=len(self.error_log),
                tools_tested=len(self.tool_timings),
                concurrent_requests=0,
            )

    def record_tool_timing(self, tool_name: str, response_time: float, success: bool = True):
        """Record timing for a specific tool call"""
        if tool_name not in self.tool_timings:
            self.tool_timings[tool_name] = []

        self.tool_timings[tool_name].append(response_time)

        # Keep only last 100 timings per tool
        if len(self.tool_timings[tool_name]) > 100:
            self.tool_timings[tool_name] = self.tool_timings[tool_name][-100:]

        if not success:
            self.error_log.append(
                {"timestamp": time.time(), "tool": tool_name, "response_time": response_time, "error": True}
            )

        # Log performance warnings
        if response_time > self.thresholds["max_response_time"]:
            self.logger.warning(f"Tool {tool_name} exceeded response time threshold: {response_time:.2f}s")

    async def analyze_performance(self) -> Dict:
        """Analyze current performance against QA criteria"""
        if not self.metrics_history:
            return {"status": "no_data", "analysis": "No metrics available"}

        current = self.metrics_history[-1]

        # Check against thresholds
        issues = []
        if current.tool_response_time > self.thresholds["max_response_time"]:
            issues.append(f"Response time too high: {current.tool_response_time:.2f}s")

        if current.memory_usage_mb > self.thresholds["max_memory_mb"]:
            issues.append(f"Memory usage too high: {current.memory_usage_mb:.1f}MB")

        if current.cpu_percent > self.thresholds["max_cpu_percent"]:
            issues.append(f"CPU usage too high: {current.cpu_percent:.1f}%")

        if current.tool_success_rate < self.thresholds["min_success_rate"]:
            issues.append(f"Success rate too low: {current.tool_success_rate:.1%}")

        # Performance summary
        total_runtime = time.time() - self.start_time

        analysis = {
            "status": "pass" if not issues else "fail",
            "issues": issues,
            "summary": {
                "runtime_minutes": total_runtime / 60,
                "tools_tested": current.tools_tested,
                "total_tests": sum(len(times) for times in self.tool_timings.values()),
                "success_rate": current.tool_success_rate,
                "avg_response_time": current.tool_response_time,
                "current_memory_mb": current.memory_usage_mb,
                "current_cpu_percent": current.cpu_percent,
                "active_processes": current.active_processes,
            },
            "tool_performance": {
                tool: {
                    "avg_time": sum(times) / len(times),
                    "max_time": max(times),
                    "min_time": min(times),
                    "call_count": len(times),
                }
                for tool, times in self.tool_timings.items()
                if times
            },
        }

        return analysis

    async def generate_qa_report(self) -> str:
        """Generate comprehensive QA performance report"""
        analysis = await self.analyze_performance()

        if analysis["status"] == "no_data":
            return "# MCP Server Performance Report - Phase 2 QA Testing\n\n❌ No performance data available. Start monitoring first."

        summary = analysis.get("summary", {})

        report = f"""
# MCP Server Performance Report - Phase 2 QA Testing

## Executive Summary
- **Status**: {analysis["status"].upper()}
- **Runtime**: {summary.get("runtime_minutes", 0):.1f} minutes
- **Tools Tested**: {summary.get("tools_tested", 0)}
- **Total Tests**: {summary.get("total_tests", 0)}
- **Success Rate**: {summary.get("success_rate", 0):.1%}

## Performance Metrics
- **Average Response Time**: {summary.get("avg_response_time", 0):.3f}s (Target: <1.0s)
- **Memory Usage**: {summary.get("current_memory_mb", 0):.1f}MB (Target: <500MB)
- **CPU Usage**: {summary.get("current_cpu_percent", 0):.1f}% (Target: <80%)
- **Active Processes**: {summary.get("active_processes", 0)}

## Issues Detected
"""

        if analysis["issues"]:
            for issue in analysis["issues"]:
                report += f"- ❌ {issue}\n"
        else:
            report += "- ✅ No performance issues detected\n"

        report += "\n## Tool Performance Breakdown\n"

        tool_performance = analysis.get("tool_performance", {})
        if tool_performance:
            for tool, perf in tool_performance.items():
                status = "✅" if perf["avg_time"] < 1.0 else "⚠️"
                report += f"- {status} **{tool}**: {perf['avg_time']:.3f}s avg, {perf['call_count']} calls\n"
        else:
            report += "- ℹ️ No tool performance data available yet\n"

        report += "\n## QA Criteria Assessment\n"
        report += f"- **Response Time**: {'✅' if summary.get('avg_response_time', 0) < 1.0 else '❌'} Target <1.0s\n"
        report += f"- **Memory Usage**: {'✅' if summary.get('current_memory_mb', 0) < 500 else '❌'} Target <500MB\n"
        report += f"- **Success Rate**: {'✅' if summary.get('success_rate', 0) >= 0.90 else '❌'} Target ≥90%\n"

        return report

    async def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous performance monitoring"""
        self.logger.info("Starting MCP performance monitoring for Phase 2 QA testing")

        while True:
            try:
                metrics = await self.collect_metrics()

                # Log key metrics
                self.logger.info(
                    f"Performance: {metrics.tool_response_time:.3f}s response, "
                    f"{metrics.memory_usage_mb:.1f}MB memory, "
                    f"{metrics.cpu_percent:.1f}% CPU, "
                    f"{metrics.tool_success_rate:.1%} success rate"
                )

                # Write metrics to JSON file for dashboard
                metrics_file = self.log_path.parent / "mcp_metrics_current.json"
                with open(metrics_file, "w") as f:
                    json.dump(asdict(metrics), f, indent=2)

                await asyncio.sleep(interval_seconds)

            except KeyboardInterrupt:
                self.logger.info("Performance monitoring stopped")
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval_seconds)


# CLI interface for QA team
async def main():
    """Main entry point for performance monitoring"""
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        # Generate and print QA report
        monitor = MCPPerformanceMonitor()
        report = await monitor.generate_qa_report()
        print(report)
    else:
        # Start continuous monitoring
        monitor = MCPPerformanceMonitor()
        await monitor.start_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
