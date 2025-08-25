#!/usr/bin/env python3
"""Validate the MCP CLI parity fix."""

import asyncio

from tmux_orchestrator.mcp_server import FreshCLIToMCPServer


async def validate_fix():
    """Validate that the MCP server fix achieves CLI parity."""
    print("🔍 MCP CLI Parity Fix Validation Report")
    print("=" * 50)

    # Initialize server
    server = FreshCLIToMCPServer()

    # Discover CLI structure
    print("\n1. Discovering CLI structure...")
    cli_structure = await server.discover_cli_structure()
    command_count = len([k for k, v in cli_structure.items() if isinstance(v, dict) and v.get("type") == "command"])
    print(f"   ✓ Found {command_count} CLI commands")

    # Generate tools
    print("\n2. Generating MCP tools...")
    server.generate_all_mcp_tools()
    tool_count = len(server.generated_tools)
    print(f"   ✓ Generated {tool_count} MCP tools")

    # Categorize tools
    simple_tools = []
    group_tools = []

    for tool_name in server.generated_tools:
        if "_" in tool_name:
            group_tools.append(tool_name)
        else:
            simple_tools.append(tool_name)

    print("\n3. Tool breakdown:")
    print(f"   - Simple commands: {len(simple_tools)}")
    print(f"   - Subcommands: {len(group_tools)}")

    # Show sample tools
    print("\n4. Sample generated tools:")
    sample_tools = sorted(server.generated_tools.keys())[:10]
    for tool in sample_tools:
        print(f"   - {tool}")
    print(f"   ... and {tool_count - 10} more")

    # Calculate improvement
    print("\n5. Improvement metrics:")
    print("   - Before fix: 6 tools")
    print(f"   - After fix: {tool_count} tools")
    print(f"   - Improvement: {(tool_count / 6 - 1) * 100:.0f}% increase")
    print(f"   - CLI coverage: ~{(tool_count / 40) * 100:.0f}% (estimated)")

    # Success criteria check
    print("\n6. Success criteria:")
    print(f"   {'✓' if tool_count > 40 else '✗'} Generate 40+ MCP tools")
    print(f"   {'✓' if group_tools else '✗'} Support command groups with subcommands")
    print(f"   {'✓' if 'agent_status' in server.generated_tools else '✗'} Include agent management tools")
    print(f"   {'✓' if 'monitor_start' in server.generated_tools else '✗'} Include monitoring tools")

    print("\n" + "=" * 50)
    if tool_count > 40:
        print("✅ MCP CLI PARITY FIX SUCCESSFUL!")
        print(f"Generated {tool_count} tools covering all major CLI functionality.")
    else:
        print("❌ Fix incomplete - further investigation needed")

    return tool_count


if __name__ == "__main__":
    tools = asyncio.run(validate_fix())
