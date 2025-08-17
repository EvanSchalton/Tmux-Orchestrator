#!/usr/bin/env python3
"""Test a single MCP tool execution in detail."""

import asyncio
import json

from tmux_orchestrator.mcp_fresh import FreshCLIToMCPServer


async def test_single_tool():
    """Test a single MCP tool to see how it works."""

    # Initialize server
    server = FreshCLIToMCPServer()
    await server.discover_cli_structure()
    server.generate_all_mcp_tools()

    # Test the 'list' tool
    if "list" in server.generated_tools:
        print("Testing 'list' tool...")
        tool_function = server.generated_tools["list"]["function"]

        # Call without arguments
        print("\n1. Testing without arguments:")
        result = await tool_function()
        print(f"Success: {result.get('success')}")
        print(f"Command: {result.get('command')}")
        parsed_result = result.get("result", {})
        if isinstance(parsed_result, dict):
            print(f"Return code: {parsed_result.get('return_code', 'N/A')}")
        else:
            print(f"Parsed result type: {type(parsed_result)}")
            print(f"Parsed result: {parsed_result}")
        print(f"Output preview: {result.get('raw_output', '')[:200]}...")

        # Call with JSON flag
        print("\n2. Testing with --json flag:")
        result = await tool_function(options={"json": True})
        print(f"Success: {result.get('success')}")
        print(f"Command line: {result.get('command_line', 'N/A')}")

        # Check if we got JSON output
        parsed = result.get("result", {}).get("parsed_output", {})
        if isinstance(parsed, dict) and "output" not in parsed:
            print(f"Parsed JSON: {json.dumps(parsed, indent=2)[:200]}...")
        else:
            print(f"Raw output: {result.get('raw_output', '')[:200]}...")

    # Test a subcommand tool
    if "agent_status" in server.generated_tools:
        print("\n\nTesting 'agent_status' tool...")
        tool_function = server.generated_tools["agent_status"]["function"]

        result = await tool_function()
        print(f"Success: {result.get('success')}")
        print(f"Command: {result.get('command')}")
        print(f"Output preview: {result.get('raw_output', '')[:200]}...")


if __name__ == "__main__":
    asyncio.run(test_single_tool())
