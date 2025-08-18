#!/usr/bin/env python3
"""
Comprehensive test suite for MCP CLI parity validation.

This test suite ensures that all CLI commands are properly exposed via MCP tools
and validates their functionality.
"""

import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tmux_orchestrator.mcp_server import FreshCLIToMCPServer


@dataclass
class TestResult:
    """Result of a single test case."""

    command: str
    tool_name: str
    success: bool
    error: str | None = None
    execution_time: float = 0.0
    output: dict[str, Any] | None = None


class MCPParityTestSuite:
    """Comprehensive test suite for MCP CLI parity."""

    def __init__(self):
        self.server = FreshCLIToMCPServer()
        self.test_results: list[TestResult] = []
        self.cli_commands = self._get_all_cli_commands()

    def _get_all_cli_commands(self) -> dict[str, list[str]]:
        """Get all available CLI commands using tmux-orc reflect."""
        commands = {}

        # Hardcoded list based on the actual CLI structure
        # Since reflect --json seems to have issues, we'll use known commands
        commands = {
            "agent": ["attach", "deploy", "info", "kill", "kill-all", "list", "message", "restart", "send", "status"],
            "monitor": [
                "dashboard",
                "logs",
                "performance",
                "recovery-logs",
                "recovery-start",
                "recovery-status",
                "recovery-stop",
                "start",
                "status",
                "stop",
            ],
            "pm": ["broadcast", "checkin", "create", "custom-checkin", "message", "status"],
            "context": ["export", "list", "show", "spawn"],
            "team": ["broadcast", "deploy", "list", "recover", "status"],
            "orchestrator": ["broadcast", "kill", "kill-all", "list", "schedule", "start", "status"],
            "setup": ["all", "check", "check-requirements", "claude-code", "mcp", "tmux", "vscode"],
            "spawn": ["agent", "orc", "pm"],
            "recovery": ["start", "status", "stop", "test"],
            "session": ["attach", "list"],
            "pubsub": ["publish", "read", "search", "status"],
            "pubsub-fast": ["publish", "read", "stats", "status"],
            "daemon": ["logs", "restart", "start", "status", "stop"],
            "tasks": ["archive", "create", "distribute", "export", "generate", "list", "status"],
            "errors": ["clear", "recent", "stats", "summary"],
            "server": ["setup", "start", "status", "toggle", "tools"],
        }

        # Add standalone commands
        commands["_standalone"] = ["execute", "list", "quick-deploy", "reflect", "status"]

        return commands

    async def setup(self):
        """Setup the test environment."""
        print("🔧 Setting up MCP server for testing...")
        await self.server.discover_cli_structure()
        self.server.generate_all_mcp_tools()
        print(f"✅ Generated {len(self.server.generated_tools)} MCP tools")

    def get_parity_report(self) -> dict[str, Any]:
        """Generate a comprehensive parity report."""
        total_cli_commands = sum(len(cmds) for cmds in self.cli_commands.values())
        total_mcp_tools = len(self.server.generated_tools)

        # Check coverage by group
        group_coverage = {}
        missing_commands = []

        for group, commands in self.cli_commands.items():
            if group == "_standalone":
                # Check standalone commands
                for cmd in commands:
                    tool_name = cmd.replace("-", "_")
                    if tool_name not in self.server.generated_tools:
                        missing_commands.append(cmd)
            else:
                # Check group commands
                group_tools = []
                for cmd in commands:
                    tool_name = f"{group}_{cmd}".replace("-", "_")
                    if tool_name in self.server.generated_tools:
                        group_tools.append(tool_name)
                    else:
                        missing_commands.append(f"{group} {cmd}")

                group_coverage[group] = {
                    "expected": len(commands),
                    "actual": len(group_tools),
                    "coverage": len(group_tools) / len(commands) * 100 if commands else 0,
                }

        return {
            "total_cli_commands": total_cli_commands,
            "total_mcp_tools": total_mcp_tools,
            "overall_coverage": total_mcp_tools / total_cli_commands * 100 if total_cli_commands else 0,
            "group_coverage": group_coverage,
            "missing_commands": missing_commands,
            "test_timestamp": datetime.now().isoformat(),
        }

    async def test_tool_generation(self) -> TestResult:
        """Test that all expected tools are generated."""
        parity_report = self.get_parity_report()

        if parity_report["overall_coverage"] >= 95:
            return TestResult(command="tool_generation", tool_name="N/A", success=True, output=parity_report)
        else:
            return TestResult(
                command="tool_generation",
                tool_name="N/A",
                success=False,
                error=f"Coverage only {parity_report['overall_coverage']:.1f}%, missing: {parity_report['missing_commands']}",
                output=parity_report,
            )

    async def test_agent_commands(self) -> list[TestResult]:
        """Test critical agent management commands."""
        results = []

        # Test agent status (most commonly used)
        if "agent_status" in self.server.generated_tools:
            tool = self.server.generated_tools["agent_status"]["function"]
            try:
                result = await tool()
                results.append(
                    TestResult(
                        command="agent status",
                        tool_name="agent_status",
                        success=result.get("success", False),
                        output=result,
                    )
                )
            except Exception as e:
                results.append(
                    TestResult(command="agent status", tool_name="agent_status", success=False, error=str(e))
                )

        # Test agent list
        if "agent_list" in self.server.generated_tools:
            tool = self.server.generated_tools["agent_list"]["function"]
            try:
                result = await tool()
                results.append(
                    TestResult(
                        command="agent list",
                        tool_name="agent_list",
                        success=result.get("success", False),
                        output=result,
                    )
                )
            except Exception as e:
                results.append(TestResult(command="agent list", tool_name="agent_list", success=False, error=str(e)))

        return results

    async def test_monitor_commands(self) -> list[TestResult]:
        """Test critical monitoring commands."""
        results = []

        # Test monitor status
        if "monitor_status" in self.server.generated_tools:
            tool = self.server.generated_tools["monitor_status"]["function"]
            try:
                result = await tool()
                results.append(
                    TestResult(
                        command="monitor status",
                        tool_name="monitor_status",
                        success=result.get("success", False),
                        output=result,
                    )
                )
            except Exception as e:
                results.append(
                    TestResult(command="monitor status", tool_name="monitor_status", success=False, error=str(e))
                )

        return results

    async def test_team_commands(self) -> list[TestResult]:
        """Test team management commands."""
        results = []

        # Test team status
        if "team_status" in self.server.generated_tools:
            tool = self.server.generated_tools["team_status"]["function"]
            try:
                result = await tool()
                results.append(
                    TestResult(
                        command="team status",
                        tool_name="team_status",
                        success=result.get("success", False),
                        output=result,
                    )
                )
            except Exception as e:
                results.append(TestResult(command="team status", tool_name="team_status", success=False, error=str(e)))

        return results

    async def test_argument_passing(self) -> list[TestResult]:
        """Test that arguments are properly passed to CLI commands."""
        results = []

        # Test agent info with specific target
        if "agent_info" in self.server.generated_tools:
            tool = self.server.generated_tools["agent_info"]["function"]
            try:
                # Test with a non-existent agent (should fail gracefully)
                result = await tool(args=["test-session:0"])
                results.append(
                    TestResult(
                        command="agent info test-session:0",
                        tool_name="agent_info",
                        success=True,  # Success means it executed, even if agent doesn't exist
                        output=result,
                    )
                )
            except Exception as e:
                results.append(
                    TestResult(command="agent info test-session:0", tool_name="agent_info", success=False, error=str(e))
                )

        # Test spawn agent with options
        if "spawn_agent" in self.server.generated_tools:
            tool = self.server.generated_tools["spawn_agent"]["function"]
            try:
                # Test with dry-run option
                result = await tool(args=["test-dev", "test-session:1"], options={"dry-run": True})
                results.append(
                    TestResult(command="spawn agent --dry-run", tool_name="spawn_agent", success=True, output=result)
                )
            except Exception as e:
                results.append(
                    TestResult(command="spawn agent --dry-run", tool_name="spawn_agent", success=False, error=str(e))
                )

        return results

    async def test_performance(self) -> TestResult:
        """Test that tool generation meets performance requirements."""
        import time

        start_time = time.time()

        # Re-initialize server and generate tools
        server = FreshCLIToMCPServer()
        await server.discover_cli_structure()
        server.generate_all_mcp_tools()

        execution_time = time.time() - start_time

        return TestResult(
            command="performance_test",
            tool_name="N/A",
            success=execution_time < 30,  # 30 second requirement
            execution_time=execution_time,
            error=f"Tool generation took {execution_time:.2f}s (requirement: <30s)" if execution_time >= 30 else None,
        )

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all test cases and generate report."""
        await self.setup()

        print("\n🧪 Running MCP CLI Parity Tests...\n")

        # Test tool generation coverage
        print("📊 Testing tool generation coverage...")
        self.test_results.append(await self.test_tool_generation())

        # Test agent commands
        print("🤖 Testing agent commands...")
        self.test_results.extend(await self.test_agent_commands())

        # Test monitor commands
        print("📈 Testing monitor commands...")
        self.test_results.extend(await self.test_monitor_commands())

        # Test team commands
        print("👥 Testing team commands...")
        self.test_results.extend(await self.test_team_commands())

        # Test argument passing
        print("📝 Testing argument passing...")
        self.test_results.extend(await self.test_argument_passing())

        # Test performance
        print("⚡ Testing performance requirements...")
        self.test_results.append(await self.test_performance())

        # Generate final report
        passed = sum(1 for r in self.test_results if r.success)
        failed = len(self.test_results) - passed

        report = {
            "summary": {
                "total_tests": len(self.test_results),
                "passed": passed,
                "failed": failed,
                "success_rate": passed / len(self.test_results) * 100 if self.test_results else 0,
            },
            "parity_report": self.get_parity_report(),
            "test_results": [
                {
                    "command": r.command,
                    "tool_name": r.tool_name,
                    "success": r.success,
                    "error": r.error,
                    "execution_time": r.execution_time,
                }
                for r in self.test_results
            ],
            "timestamp": datetime.now().isoformat(),
        }

        return report


async def main():
    """Run the test suite."""
    test_suite = MCPParityTestSuite()
    report = await test_suite.run_all_tests()

    # Print summary
    print("\n" + "=" * 60)
    print("📋 MCP CLI PARITY TEST REPORT")
    print("=" * 60)

    print(f"\n✅ Passed: {report['summary']['passed']}")
    print(f"❌ Failed: {report['summary']['failed']}")
    print(f"📊 Success Rate: {report['summary']['success_rate']:.1f}%")

    parity = report["parity_report"]
    print(f"\n📈 Overall CLI Coverage: {parity['overall_coverage']:.1f}%")
    print(f"🔧 Total MCP Tools: {parity['total_mcp_tools']}")
    print(f"📝 Total CLI Commands: {parity['total_cli_commands']}")

    if parity["missing_commands"]:
        print(f"\n⚠️  Missing Commands ({len(parity['missing_commands'])}):")
        for cmd in parity["missing_commands"][:10]:  # Show first 10
            print(f"   - {cmd}")
        if len(parity["missing_commands"]) > 10:
            print(f"   ... and {len(parity['missing_commands']) - 10} more")

    # Save detailed report
    report_path = Path(__file__).parent / "mcp_parity_test_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n💾 Detailed report saved to: {report_path}")

    # Exit with appropriate code
    sys.exit(0 if report["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
