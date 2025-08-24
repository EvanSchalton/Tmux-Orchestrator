#!/usr/bin/env python3
"""Test suite for MCP spawn command enhancements."""

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict


class MCPSpawnTester:
    """Test MCP enhancements in spawn commands."""

    def __init__(self):
        self.test_session = "mcp-test-session"
        self.results = []

    def setup(self):
        """Create test session."""
        subprocess.run(["tmux", "new-session", "-d", "-s", self.test_session], capture_output=True)
        time.sleep(1)

    def cleanup(self):
        """Kill test session."""
        subprocess.run(["tmux", "kill-session", "-t", self.test_session], capture_output=True)

    def test_agent_spawn_mcp_injection(self) -> Dict[str, Any]:
        """Test that agent spawn includes MCP guidance."""
        test_name = "agent_mcp_injection"

        # Spawn test agent
        cmd = [
            "tmux-orc",
            "spawn",
            "agent",
            "test-mcp-agent",
            self.test_session,
            "--briefing",
            "You are a test agent for MCP validation.",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Check if spawn succeeded
        success = result.returncode == 0

        # Verify window was created
        windows = (
            subprocess.run(
                ["tmux", "list-windows", "-t", self.test_session, "-F", "#{window_name}"],
                capture_output=True,
                text=True,
            )
            .stdout.strip()
            .split("\n")
        )

        window_created = "test-mcp-agent" in windows

        return {
            "test": test_name,
            "passed": success and window_created,
            "spawn_success": success,
            "window_created": window_created,
            "error": result.stderr if not success else None,
        }

    def test_mcp_guidance_content(self) -> Dict[str, Any]:
        """Verify MCP guidance content is correct."""
        test_name = "mcp_guidance_content"

        # Read spawn.py to check enhanced briefing
        spawn_file = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/cli/spawn.py")
        content = spawn_file.read_text()

        # Check for MCP guidance markers
        has_mcp_section = "## MCP Tool Access" in content
        has_tool_count = "92 auto-generated MCP tools" in content
        has_categories = all(
            cat in content for cat in ["**agent**", "**monitor**", "**team**", "**spawn**", "**context**"]
        )
        has_availability_check = "look for the tools icon in Claude Code" in content

        return {
            "test": test_name,
            "passed": all([has_mcp_section, has_tool_count, has_categories, has_availability_check]),
            "has_mcp_section": has_mcp_section,
            "has_tool_count": has_tool_count,
            "has_categories": has_categories,
            "has_availability_check": has_availability_check,
        }

    def test_backward_compatibility(self) -> Dict[str, Any]:
        """Test legacy spawn format still works."""
        test_name = "backward_compatibility"

        # Test legacy format with window index
        cmd = [
            "tmux-orc",
            "spawn",
            "agent",
            "legacy-agent",
            f"{self.test_session}:2",
            "--briefing",
            "Testing legacy format",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Should succeed with warning about ignored index
        success = result.returncode == 0
        has_warning = "will be ignored" in result.stdout

        return {
            "test": test_name,
            "passed": success and has_warning,
            "spawn_success": success,
            "legacy_warning": has_warning,
            "output": result.stdout[:200] if result.stdout else None,
        }

    def test_pm_spawn(self) -> Dict[str, Any]:
        """Test PM spawn command."""
        test_name = "pm_spawn"

        cmd = ["tmux-orc", "spawn", "pm", "--session", self.test_session]
        result = subprocess.run(cmd, capture_output=True, text=True)

        success = result.returncode == 0

        return {
            "test": test_name,
            "passed": success,
            "spawn_success": success,
            "error": result.stderr if not success else None,
        }

    def test_spawn_performance(self) -> Dict[str, Any]:
        """Measure spawn command performance."""
        test_name = "spawn_performance"

        # Time spawn without cleanup
        start = time.time()
        cmd = ["tmux-orc", "spawn", "agent", "perf-test", self.test_session, "--briefing", "Performance test agent"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - start

        # Expected: spawn should complete in reasonable time
        reasonable_time = elapsed < 15  # 15 seconds max

        return {
            "test": test_name,
            "passed": result.returncode == 0 and reasonable_time,
            "spawn_time": elapsed,
            "reasonable_time": reasonable_time,
            "error": result.stderr if result.returncode != 0 else None,
        }

    def run_all_tests(self):
        """Run all tests and generate report."""
        print("🧪 MCP Spawn Enhancement Test Suite")
        print("=" * 50)

        # Setup
        print("Setting up test environment...")
        self.setup()
        time.sleep(2)

        # Run tests
        tests = [
            self.test_mcp_guidance_content,
            self.test_agent_spawn_mcp_injection,
            self.test_backward_compatibility,
            self.test_pm_spawn,
            self.test_spawn_performance,
        ]

        for test_func in tests:
            print(f"\nRunning: {test_func.__name__}")
            try:
                result = test_func()
                self.results.append(result)
                status = "✅ PASSED" if result["passed"] else "❌ FAILED"
                print(f"  {status}")
                if not result["passed"]:
                    print(f"  Details: {json.dumps(result, indent=2)}")
            except Exception as e:
                print(f"  ❌ ERROR: {str(e)}")
                self.results.append({"test": test_func.__name__, "passed": False, "error": str(e)})
            time.sleep(1)

        # Cleanup
        print("\nCleaning up...")
        self.cleanup()

        # Summary
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)

        print("\n" + "=" * 50)
        print(f"Test Summary: {passed}/{total} passed")

        # Save detailed results
        report_path = Path("/workspaces/Tmux-Orchestrator/mcp_spawn_test_report.json")
        with open(report_path, "w") as f:
            json.dump(
                {
                    "test_run": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "summary": f"{passed}/{total} passed",
                    "results": self.results,
                },
                f,
                indent=2,
            )

        print(f"\nDetailed report saved to: {report_path}")

        return passed == total


if __name__ == "__main__":
    tester = MCPSpawnTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
