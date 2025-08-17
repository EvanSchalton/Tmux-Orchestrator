#!/usr/bin/env python3
"""
Simple script to count available MCP tools by simulating tool generation.
"""

import re
import subprocess
import time


def count_mcp_tools_from_generation():
    """Count MCP tools by running generation simulation."""
    print("🔧 Simulating MCP tool generation to count tools...")

    # Run a Python script to simulate tool generation
    test_script = """
import sys
sys.path.insert(0, ".")
from tmux_orchestrator.mcp_server import FreshCLIToMCPServer
import asyncio

async def count_tools():
    server = FreshCLIToMCPServer()
    await server.discover_cli_structure()
    server.generate_all_mcp_tools()
    return len(server.generated_tools)

result = asyncio.run(count_tools())
print(f"TOOL_COUNT:{result}")
"""

    start_time = time.time()

    result = subprocess.run(
        ["python", "-c", test_script], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
    )

    generation_time = time.time() - start_time

    # Extract tool count
    tool_count = 0
    if result.returncode == 0:
        match = re.search(r"TOOL_COUNT:(\d+)", result.stdout)
        if match:
            tool_count = int(match.group(1))

        # Also check for log messages
        for line in result.stdout.split("\n"):
            if "Successfully generated" in line and "MCP tools" in line:
                match = re.search(r"Successfully generated (\d+) MCP tools", line)
                if match:
                    tool_count = int(match.group(1))

    return tool_count, generation_time, result.stdout, result.stderr


def main():
    """Count and report MCP tools."""
    print("📊 MCP Tool Count Validation")
    print("=" * 50)

    tool_count, generation_time, stdout, stderr = count_mcp_tools_from_generation()

    print(f"\n✅ MCP Tools Generated: {tool_count}")
    print(f"⏱️  Generation Time: {generation_time:.2f}s")

    # Performance check
    if generation_time < 30:
        print("✅ Performance: PASSED (< 30s requirement)")
    else:
        print("❌ Performance: FAILED (> 30s requirement)")

    # Coverage estimate (based on 92-95 expected commands)
    expected_commands = 92
    coverage = (tool_count / expected_commands * 100) if expected_commands > 0 else 0

    print(f"\n📈 Coverage Estimate: {coverage:.1f}%")
    if coverage >= 95:
        print("✅ Coverage: PASSED (>= 95% requirement)")
    else:
        print("❌ Coverage: NEEDS IMPROVEMENT")

    # Save simple summary
    with open("mcp_tool_count.txt", "w") as f:
        f.write(f"MCP Tools: {tool_count}\n")
        f.write(f"Generation Time: {generation_time:.2f}s\n")
        f.write(f"Coverage: {coverage:.1f}%\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    print("\n💾 Summary saved to: mcp_tool_count.txt")


if __name__ == "__main__":
    main()
