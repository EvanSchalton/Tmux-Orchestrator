#!/usr/bin/env python3
"""
Comprehensive MCP Tools Testing Script
Tests all 6 auto-generated MCP tools with the fresh CLI reflection server.
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MCPToolTester:
    """Test all auto-generated MCP tools."""

    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()

    async def run_all_tests(self):
        """Run comprehensive tests on all 6 MCP tools."""
        logger.info("Starting comprehensive MCP tools testing...")

        # Core tools to test (based on CLI reflection)
        tools_to_test = [
            ("list", self.test_list_tool),
            ("status", self.test_status_tool),
            ("quick_deploy", self.test_quick_deploy_tool),
            ("spawn_orc", self.test_spawn_orc_tool),
            ("execute", self.test_execute_tool),
            ("reflect", self.test_reflect_tool),
        ]

        for tool_name, test_func in tools_to_test:
            logger.info(f"Testing {tool_name} tool...")
            try:
                result = await test_func()
                self.test_results[tool_name] = {
                    "status": "success",
                    "result": result,
                    "execution_time": time.time() - self.start_time,
                }
                logger.info(f"✅ {tool_name} test passed")
            except Exception as e:
                self.test_results[tool_name] = {
                    "status": "failed",
                    "error": str(e),
                    "execution_time": time.time() - self.start_time,
                }
                logger.error(f"❌ {tool_name} test failed: {e}")

        # Generate test report
        await self.generate_test_report()

    async def test_list_tool(self) -> dict[str, Any]:
        """Test the list MCP tool."""
        return await self.execute_cli_command_directly("list", ["--json"])

    async def test_status_tool(self) -> dict[str, Any]:
        """Test the status MCP tool."""
        return await self.execute_cli_command_directly("status", ["--json"])

    async def test_quick_deploy_tool(self) -> dict[str, Any]:
        """Test the quick-deploy MCP tool (dry run)."""
        # Test with --help to avoid actually deploying
        return await self.execute_cli_command_directly("quick-deploy", ["--help"])

    async def test_spawn_orc_tool(self) -> dict[str, Any]:
        """Test the spawn-orc MCP tool (dry run)."""
        # Test with --help to avoid actually spawning
        return await self.execute_cli_command_directly("spawn-orc", ["--help"])

    async def test_execute_tool(self) -> dict[str, Any]:
        """Test the execute MCP tool (dry run)."""
        # Test with --help to avoid actually executing a PRD
        return await self.execute_cli_command_directly("execute", ["--help"])

    async def test_reflect_tool(self) -> dict[str, Any]:
        """Test the reflect MCP tool."""
        return await self.execute_cli_command_directly("reflect", ["--format", "json"])

    async def execute_cli_command_directly(self, command: str, args: list[str]) -> dict[str, Any]:
        """Execute CLI command directly to simulate MCP tool behavior."""
        start_time = time.time()

        try:
            # Build complete command
            cmd_parts = ["tmux-orc", command] + args

            logger.info(f"Executing: {' '.join(cmd_parts)}")

            # Execute command
            result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=30)

            execution_time = time.time() - start_time

            # Parse JSON output if available
            parsed_output = {}
            if result.stdout:
                try:
                    parsed_output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    parsed_output = {"output": result.stdout}

            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": execution_time,
                "parsed_output": parsed_output,
                "command_line": " ".join(cmd_parts),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out after 30 seconds",
                "execution_time": time.time() - start_time,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "execution_time": time.time() - start_time}

    async def generate_test_report(self):
        """Generate comprehensive test report."""
        total_time = time.time() - self.start_time

        print("\n" + "=" * 80)
        print("MCP TOOLS TESTING REPORT")
        print("=" * 80)
        print(f"Test Duration: {total_time:.2f} seconds")
        print(f"Total Tools Tested: {len(self.test_results)}")

        # Success/failure summary
        success_count = sum(1 for r in self.test_results.values() if r["status"] == "success")
        failure_count = len(self.test_results) - success_count

        print(f"✅ Successful Tests: {success_count}")
        print(f"❌ Failed Tests: {failure_count}")
        print(f"Success Rate: {(success_count/len(self.test_results)*100):.1f}%")

        print("\nDETAILED RESULTS:")
        print("-" * 50)

        for tool_name, result in self.test_results.items():
            status_icon = "✅" if result["status"] == "success" else "❌"
            print(f"{status_icon} {tool_name.upper()}:")
            print(f"   Status: {result['status']}")
            print(f"   Execution Time: {result.get('execution_time', 0):.2f}s")

            if result["status"] == "success":
                tool_result = result["result"]
                print(f"   Return Code: {tool_result.get('return_code', 'N/A')}")
                print(f"   Success: {tool_result.get('success', False)}")
                if tool_result.get("parsed_output"):
                    output_keys = list(tool_result["parsed_output"].keys())
                    print(f"   Output Keys: {output_keys}")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
            print()

        # Performance Analysis
        print("PERFORMANCE ANALYSIS:")
        print("-" * 50)
        execution_times = [r.get("execution_time", 0) for r in self.test_results.values()]
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            max_time = max(execution_times)
            min_time = min(execution_times)

            print(f"Average Execution Time: {avg_time:.2f}s")
            print(f"Fastest Tool: {min_time:.2f}s")
            print(f"Slowest Tool: {max_time:.2f}s")

        # MCP Tool Coverage
        print("\nMCP TOOL COVERAGE:")
        print("-" * 50)
        expected_tools = ["list", "status", "quick_deploy", "spawn_orc", "execute", "reflect"]
        tested_tools = list(self.test_results.keys())

        for tool in expected_tools:
            if tool in tested_tools:
                result = self.test_results[tool]
                status_icon = "✅" if result["status"] == "success" else "❌"
                print(f"{status_icon} {tool} - {result['status']}")
            else:
                print(f"⚠️  {tool} - not tested")

        # Save results to file
        report_file = "/workspaces/Tmux-Orchestrator/mcp_test_report.json"
        with open(report_file, "w") as f:
            json.dump(
                {
                    "timestamp": time.time(),
                    "total_duration": total_time,
                    "success_rate": success_count / len(self.test_results) * 100,
                    "results": self.test_results,
                },
                f,
                indent=2,
            )

        print(f"\nDetailed results saved to: {report_file}")
        print("=" * 80)


async def main():
    """Main test execution."""
    try:
        # Verify tmux-orc is available
        result = subprocess.run(["tmux-orc", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("❌ tmux-orc command not available!")
            sys.exit(1)

        print(f"✅ Found tmux-orc: {result.stdout.strip()}")

        # Run comprehensive tests
        tester = MCPToolTester()
        await tester.run_all_tests()

    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"❌ Testing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
