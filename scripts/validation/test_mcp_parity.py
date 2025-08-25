#!/usr/bin/env python3
"""Test MCP tool generation and CLI parity."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tmux_orchestrator.mcp_server import FreshCLIToMCPServer


async def test_mcp_generation():
    """Test MCP tool generation and report results."""
    print("=== MCP CLI Parity Test ===\n")

    # Initialize server
    server = FreshCLIToMCPServer()

    # Generate tools
    print("Generating MCP tools...")
    await server.discover_cli_structure()
    server.generate_all_mcp_tools()

    # Report results
    print(f"\nTotal MCP tools generated: {len(server.generated_tools)}")
    print("\nGenerated tools:")
    for tool_name in sorted(server.generated_tools.keys()):
        print(f"  - {tool_name}")

    # Check CLI commands
    print("\n\n=== CLI Command Analysis ===")
    result = subprocess.run(["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True)

    if result.returncode == 0:
        cli_data = json.loads(result.stdout)

        # Count total commands
        total_commands = 0
        command_groups = {}

        for cmd in cli_data.get("commands", []):
            if "commands" in cmd:  # It's a group
                group_name = cmd["name"]
                subcommands = cmd["commands"]
                command_groups[group_name] = len(subcommands)
                total_commands += len(subcommands)
                print(f"\n{group_name} group: {len(subcommands)} subcommands")
                for subcmd in subcommands:
                    print(f"  - {subcmd['name']}")
            else:
                total_commands += 1

        print(f"\nTotal CLI commands available: {total_commands}")
        print(
            f"MCP tool coverage: {len(server.generated_tools)}/{total_commands} ({len(server.generated_tools) / total_commands * 100:.1f}%)"
        )

        # Check for missing commands
        print("\n=== Parity Analysis ===")
        if len(server.generated_tools) < total_commands:
            print(f"⚠️  Missing {total_commands - len(server.generated_tools)} commands from MCP interface")

            # Try to identify which groups are missing
            for group_name, count in command_groups.items():
                group_tools = [t for t in server.generated_tools.keys() if t.startswith(f"{group_name}_")]
                if len(group_tools) < count:
                    print(f"  - {group_name}: {len(group_tools)}/{count} commands exposed")
        else:
            print("✅ Full CLI parity achieved!")
    else:
        print("Error getting CLI reflection data:", result.stderr)


if __name__ == "__main__":
    asyncio.run(test_mcp_generation())
