#!/usr/bin/env python3
"""
QA Stress Test: Tmux Server Stability

This script stress tests the tmux server with rapid operations to ensure
it doesn't crash under load.

Test scenarios:
1. Rapid session creation/destruction
2. Multiple concurrent window operations
3. High-frequency pane capture operations
4. Memory usage monitoring
"""

import json
import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import psutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TmuxStressTest:
    """Stress test for tmux server stability."""

    def __init__(self):
        self.test_sessions: list[str] = []
        self.errors: list[str] = []
        self.start_time = time.time()
        self.metrics = {"operations_completed": 0, "errors_encountered": 0, "max_memory_mb": 0, "tmux_crashes": 0}

    def run_tmux_command(self, command: str, timeout: int = 5) -> dict[str, Any]:
        """Run a tmux command and track results."""
        try:
            start_time = time.time()
            result = subprocess.run(["tmux"] + command.split(), capture_output=True, text=True, timeout=timeout)
            duration = time.time() - start_time

            self.metrics["operations_completed"] += 1

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
                "command": command,
            }
        except subprocess.TimeoutExpired:
            self.errors.append(f"Command timeout: {command}")
            self.metrics["errors_encountered"] += 1
            return {"success": False, "error": "timeout", "command": command}
        except Exception as e:
            self.errors.append(f"Command error: {command} - {str(e)}")
            self.metrics["errors_encountered"] += 1
            return {"success": False, "error": str(e), "command": command}

    def check_tmux_server_alive(self) -> bool:
        """Check if tmux server is still responsive."""
        result = self.run_tmux_command("list-sessions")
        if not result["success"]:
            if "no server running" in result.get("stderr", "").lower():
                self.metrics["tmux_crashes"] += 1
                logger.error("🚨 TMUX SERVER CRASHED!")
                return False
        return True

    def monitor_memory_usage(self) -> None:
        """Monitor memory usage during stress test."""
        try:
            # Find tmux processes
            tmux_processes = []
            for proc in psutil.process_iter(["pid", "name", "memory_info"]):
                if proc.info["name"] and "tmux" in proc.info["name"].lower():
                    tmux_processes.append(proc)

            total_memory_mb = 0
            for proc in tmux_processes:
                try:
                    memory_mb = proc.info["memory_info"].rss / 1024 / 1024
                    total_memory_mb += memory_mb
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if total_memory_mb > self.metrics["max_memory_mb"]:
                self.metrics["max_memory_mb"] = total_memory_mb

        except Exception as e:
            logger.warning(f"Memory monitoring error: {e}")

    def stress_test_session_operations(self, duration_seconds: int = 60) -> dict[str, Any]:
        """Stress test rapid session creation/destruction."""
        logger.info(f"🔥 Starting session operations stress test ({duration_seconds}s)...")

        end_time = time.time() + duration_seconds
        session_counter = 0
        operations = 0

        while time.time() < end_time:
            session_name = f"stress-test-{session_counter}"
            session_counter += 1

            # Create session
            result = self.run_tmux_command(f"new-session -d -s {session_name}")
            operations += 1

            if result["success"]:
                self.test_sessions.append(session_name)

                # Add some windows
                for i in range(3):
                    self.run_tmux_command(f"new-window -t {session_name}")
                    operations += 1

                # Capture some panes rapidly
                for i in range(5):
                    self.run_tmux_command(f"capture-pane -t {session_name} -p")
                    operations += 1

                # Kill session
                self.run_tmux_command(f"kill-session -t {session_name}")
                operations += 1

                if session_name in self.test_sessions:
                    self.test_sessions.remove(session_name)

            # Check if tmux server is still alive
            if not self.check_tmux_server_alive():
                break

            # Monitor memory every 10 operations
            if operations % 10 == 0:
                self.monitor_memory_usage()

            # Brief pause to prevent overwhelming the system
            time.sleep(0.01)

        return {
            "operations_completed": operations,
            "sessions_created": session_counter,
            "duration": duration_seconds,
            "operations_per_second": operations / duration_seconds,
        }

    def stress_test_concurrent_operations(self, threads: int = 5, operations_per_thread: int = 50) -> dict[str, Any]:
        """Stress test concurrent tmux operations."""
        logger.info(f"🔥 Starting concurrent operations test ({threads} threads, {operations_per_thread} ops each)...")

        def worker_thread(thread_id: int) -> dict[str, Any]:
            """Worker thread for concurrent operations."""
            session_name = f"concurrent-{thread_id}"
            thread_operations = 0
            thread_errors = 0

            try:
                # Create session
                result = self.run_tmux_command(f"new-session -d -s {session_name}")
                if not result["success"]:
                    return {"operations": 0, "errors": 1}

                for i in range(operations_per_thread):
                    operations = [
                        f"new-window -t {session_name}",
                        f"capture-pane -t {session_name} -p",
                        f"list-windows -t {session_name}",
                        f"rename-window -t {session_name} test-{i}",
                    ]

                    for op in operations:
                        result = self.run_tmux_command(op, timeout=2)
                        thread_operations += 1
                        if not result["success"]:
                            thread_errors += 1

                # Cleanup
                self.run_tmux_command(f"kill-session -t {session_name}")

            except Exception as e:
                logger.error(f"Thread {thread_id} error: {e}")
                thread_errors += 1

            return {"operations": thread_operations, "errors": thread_errors}

        # Run concurrent threads
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(threads)]
            results = [f.result() for f in futures]

        total_ops = sum(r["operations"] for r in results)
        total_errors = sum(r["errors"] for r in results)

        return {
            "total_operations": total_ops,
            "total_errors": total_errors,
            "threads_used": threads,
            "success_rate": (total_ops - total_errors) / total_ops * 100 if total_ops > 0 else 0,
        }

    def stress_test_rapid_capture(self, duration_seconds: int = 30) -> dict[str, Any]:
        """Stress test rapid pane capture operations."""
        logger.info(f"🔥 Starting rapid capture test ({duration_seconds}s)...")

        # Create test session
        session_name = "capture-stress-test"
        result = self.run_tmux_command(f"new-session -d -s {session_name}")
        if not result["success"]:
            return {"error": "Failed to create test session"}

        self.test_sessions.append(session_name)

        end_time = time.time() + duration_seconds
        captures = 0

        while time.time() < end_time:
            # Rapid fire capture operations
            for i in range(10):
                result = self.run_tmux_command(f"capture-pane -t {session_name} -p")
                captures += 1
                if not result["success"]:
                    break

            # Check server health
            if not self.check_tmux_server_alive():
                break

            self.monitor_memory_usage()
            time.sleep(0.001)  # Very brief pause

        # Cleanup
        self.run_tmux_command(f"kill-session -t {session_name}")
        if session_name in self.test_sessions:
            self.test_sessions.remove(session_name)

        return {
            "captures_completed": captures,
            "captures_per_second": captures / duration_seconds,
            "duration": duration_seconds,
        }

    def cleanup_test_sessions(self) -> None:
        """Clean up any remaining test sessions."""
        logger.info("🧹 Cleaning up test sessions...")
        for session in self.test_sessions:
            try:
                self.run_tmux_command(f"kill-session -t {session}")
            except Exception:
                pass
        self.test_sessions.clear()

    def run_comprehensive_stress_test(self) -> dict[str, Any]:
        """Run comprehensive tmux stress test."""
        logger.info("🚀 Starting comprehensive tmux stress test...")
        logger.info("=" * 70)

        test_results = {}

        try:
            # Check initial server state
            if not self.check_tmux_server_alive():
                logger.error("❌ Tmux server not available - starting one...")
                subprocess.run(["tmux", "new-session", "-d", "-s", "temp-session"])
                subprocess.run(["tmux", "kill-session", "-t", "temp-session"])

            # Test 1: Session operations
            test_results["session_stress"] = self.stress_test_session_operations(60)

            # Check server health
            if not self.check_tmux_server_alive():
                logger.error("❌ Tmux server crashed during session stress test!")
                return test_results

            # Test 2: Concurrent operations
            test_results["concurrent_stress"] = self.stress_test_concurrent_operations(5, 50)

            # Check server health
            if not self.check_tmux_server_alive():
                logger.error("❌ Tmux server crashed during concurrent stress test!")
                return test_results

            # Test 3: Rapid capture
            test_results["capture_stress"] = self.stress_test_rapid_capture(30)

            # Final server health check
            server_alive = self.check_tmux_server_alive()
            test_results["server_survived"] = server_alive

        except Exception as e:
            logger.error(f"❌ Stress test error: {e}")
            test_results["error"] = str(e)

        finally:
            self.cleanup_test_sessions()

        # Generate summary
        test_results["summary"] = {
            "total_operations": self.metrics["operations_completed"],
            "total_errors": self.metrics["errors_encountered"],
            "max_memory_mb": self.metrics["max_memory_mb"],
            "tmux_crashes": self.metrics["tmux_crashes"],
            "test_duration": time.time() - self.start_time,
            "server_stable": self.metrics["tmux_crashes"] == 0,
        }

        logger.info("=" * 70)
        logger.info("🏁 Stress test complete:")
        logger.info(f"   Operations: {test_results['summary']['total_operations']}")
        logger.info(f"   Errors: {test_results['summary']['total_errors']}")
        logger.info(f"   Max memory: {test_results['summary']['max_memory_mb']:.1f} MB")
        logger.info(f"   Tmux crashes: {test_results['summary']['tmux_crashes']}")
        logger.info(f"   Server stable: {test_results['summary']['server_stable']}")

        return test_results


def main():
    """Run the tmux stress test."""
    tester = TmuxStressTest()
    results = tester.run_comprehensive_stress_test()

    # Save results
    results_file = "qa_tmux_stress_test_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"📄 Results saved to: {results_file}")

    # Return appropriate exit code
    if results["summary"]["tmux_crashes"] > 0:
        logger.error("🚨 TMUX SERVER CRASHES DETECTED!")
        return 1
    elif results["summary"]["total_errors"] > results["summary"]["total_operations"] * 0.1:
        logger.warning("⚠️  High error rate detected")
        return 1
    else:
        logger.info("✅ Tmux server remained stable under stress")
        return 0


if __name__ == "__main__":
    exit(main())
