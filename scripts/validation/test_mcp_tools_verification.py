#!/usr/bin/env python3
"""
Comprehensive MCP Tools Verification Script

Tests that MCP tools are properly generated and can execute CLI commands.
"""

import asyncio
import json
import subprocess
import sys
import time

# Import the MCP server
from tmux_orchestrator.mcp_fresh import FreshCLIToMCPServer


async def test_mcp_tool_generation():
    """Test that all MCP tools are generated correctly."""
    print("🔍 Testing MCP Tool Generation...")

    server = FreshCLIToMCPServer()
    await server.discover_cli_structure()
    tools = server.generate_all_mcp_tools()

    print(f"✅ Generated {len(tools)} MCP tools")

    # Group tools by category
    standalone_tools = []
    group_tools = {}

    for tool_name, tool_info in tools.items():
        cmd_name = tool_info["command_name"]
        if " " in cmd_name:
            # It's a subcommand
            group, subcmd = cmd_name.split(" ", 1)
            if group not in group_tools:
                group_tools[group] = []
            group_tools[group].append((tool_name, subcmd))
        else:
            # It's a standalone command
            standalone_tools.append((tool_name, cmd_name))

    print(f"\n📋 Standalone Commands ({len(standalone_tools)}):")
    for tool_name, cmd_name in sorted(standalone_tools):
        print(f"  • {tool_name} → {cmd_name}")

    print(f"\n📁 Command Groups ({len(group_tools)}):")
    for group, subcmds in sorted(group_tools.items()):
        print(f"  • {group}: {len(subcmds)} subcommands")

    return server, tools


async def test_tool_execution(server: FreshCLIToMCPServer, sample_tools: list[str]):
    """Test execution of sample MCP tools."""
    print("\n🧪 Testing Tool Execution...")

    results = []

    for tool_name in sample_tools:
        if tool_name not in server.generated_tools:
            print(f"  ❌ Tool '{tool_name}' not found")
            continue

        tool_info = server.generated_tools[tool_name]
        tool_function = tool_info["function"]

        try:
            # Execute the tool with minimal arguments
            start_time = time.time()

            # Special handling for different commands
            if tool_name == "list" or tool_name == "status":
                result = await tool_function(options={"json": True})
            elif tool_name == "reflect":
                result = await tool_function(options={"format": "json"})
            elif tool_name == "agent_list":
                result = await tool_function(options={"json": True})
            elif tool_name == "server_status":
                result = await tool_function()
            else:
                result = await tool_function()

            execution_time = time.time() - start_time

            success = result.get("success", False)
            status = "✅" if success else "⚠️"

            print(f"  {status} {tool_name}: {result.get('command')} - {execution_time:.2f}s")

            if not success:
                error = result.get("error", "Unknown error")
                print(f"     Error: {error}")

            results.append((tool_name, success, execution_time))

        except Exception as e:
            print(f"  ❌ {tool_name}: Exception - {str(e)}")
            results.append((tool_name, False, 0))

    return results


async def test_json_output_support(server: FreshCLIToMCPServer):
    """Test which tools support JSON output."""
    print("\n📊 Testing JSON Output Support...")

    json_capable_tools = []

    # Test a few representative tools
    test_tools = ["list", "status", "agent_list", "team_status", "monitor_status"]

    for tool_name in test_tools:
        if tool_name not in server.generated_tools:
            continue

        tool_function = server.generated_tools[tool_name]["function"]

        try:
            result = await tool_function(options={"json": True})

            if result.get("success") and result.get("parsed_output"):
                # Check if we got actual JSON data
                output = result["parsed_output"]
                if isinstance(output, dict) and not output.get("output"):
                    json_capable_tools.append(tool_name)
                    print(f"  ✅ {tool_name}: JSON output supported")
                else:
                    print(f"  ⚠️  {tool_name}: No structured JSON output")
            else:
                print(f"  ❌ {tool_name}: Command failed")

        except Exception as e:
            print(f"  ❌ {tool_name}: {str(e)}")

    return json_capable_tools


async def test_argument_passing(server: FreshCLIToMCPServer):
    """Test that arguments are passed correctly to tools."""
    print("\n🔧 Testing Argument Passing...")

    # Test reflect command with different formats
    if "reflect" in server.generated_tools:
        tool_function = server.generated_tools["reflect"]["function"]

        for format_type in ["tree", "json", "markdown"]:
            try:
                result = await tool_function(options={"format": format_type})
                if result.get("success"):
                    # Check if format was applied
                    output = result.get("raw_output", "")
                    if format_type == "json" and output.startswith("{"):
                        print(f"  ✅ reflect --format {format_type}: Correct output format")
                    elif format_type == "markdown" and "# tmux-orc" in output:
                        print(f"  ✅ reflect --format {format_type}: Correct output format")
                    elif format_type == "tree" and "CLI Commands" in output:
                        print(f"  ✅ reflect --format {format_type}: Correct output format")
                    else:
                        print(f"  ⚠️  reflect --format {format_type}: Unexpected output")
                else:
                    print(f"  ❌ reflect --format {format_type}: Command failed")
            except Exception as e:
                print(f"  ❌ reflect --format {format_type}: {str(e)}")


def verify_cli_parity():
    """Verify that MCP tools match CLI commands."""
    print("\n🔄 Verifying CLI Parity...")

    # Get CLI commands
    result = subprocess.run(["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True)

    if result.returncode != 0:
        print("  ❌ Failed to get CLI structure")
        return False

    cli_structure = json.loads(result.stdout)

    # Count commands and groups
    cli_commands = sum(1 for v in cli_structure.values() if isinstance(v, dict) and v.get("type") == "command")
    cli_groups = sum(1 for v in cli_structure.values() if isinstance(v, dict) and v.get("type") == "group")

    print(f"  📋 CLI Structure: {cli_commands} commands, {cli_groups} groups")

    # Get MCP tools count
    result = subprocess.run(["tmux-orc", "server", "tools"], capture_output=True, text=True)

    # Extract tool count from output
    for line in result.stdout.split("\n"):
        if "Total:" in line and "tools available" in line:
            tool_count = int(line.split()[1])
            print(f"  🔧 MCP Tools: {tool_count} total")

            if tool_count > (cli_commands + cli_groups):
                print("  ✅ Full parity achieved (tools include subcommands)")
                return True
            else:
                print("  ❌ Parity gap detected")
                return False

    return False


async def main():
    """Run all MCP tool verification tests."""
    print("=" * 60)
    print("🚀 MCP Tools Comprehensive Verification")
    print("=" * 60)

    # Test 1: Tool Generation
    server, tools = await test_mcp_tool_generation()

    # Test 2: Tool Execution (sample tools)
    sample_tools = [
        "list",  # Standalone command
        "status",  # Standalone command
        "reflect",  # Standalone command
        "agent_list",  # Subcommand
        "server_status",  # Subcommand
        "monitor_status",  # Subcommand
    ]

    execution_results = await test_tool_execution(server, sample_tools)

    # Test 3: JSON Output Support
    json_tools = await test_json_output_support(server)

    # Test 4: Argument Passing
    await test_argument_passing(server)

    # Test 5: CLI Parity
    parity_ok = verify_cli_parity()

    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)

    successful_tools = sum(1 for _, success, _ in execution_results if success)
    print(f"✅ Tool Generation: {len(tools)} tools created")
    print(f"✅ Tool Execution: {successful_tools}/{len(execution_results)} tested successfully")
    print(f"✅ JSON Support: {len(json_tools)} tools with JSON output")
    print(f"{'✅' if parity_ok else '❌'} CLI Parity: {'Achieved' if parity_ok else 'Gap detected'}")

    # Performance check
    total_time = sum(t for _, _, t in execution_results)
    if execution_results:
        avg_time = total_time / len(execution_results)
        print(f"⏱️  Average execution time: {avg_time:.2f}s per tool")

    print("\n✨ MCP Tools Verification Complete!")

    return len(tools) == 92 and successful_tools == len(execution_results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
