#!/usr/bin/env python3
"""Simple MCP Tools functionality test."""

import asyncio
import json

from tmux_orchestrator.mcp_fresh import FreshCLIToMCPServer


async def test_mcp_tools():
    """Test key MCP tools work correctly."""

    # Initialize server
    print("Initializing MCP server...")
    server = FreshCLIToMCPServer()
    await server.discover_cli_structure()
    server.generate_all_mcp_tools()

    print(f"\n✅ Generated {len(server.generated_tools)} MCP tools")

    # Test cases
    test_cases = [
        # Tool name, args, expected success
        ("reflect", {"options": {"format": "json"}}, True),
        ("server_status", {}, True),
        ("list", {"options": {"json": True}}, True),
        ("agent_list", {}, True),
        ("monitor_status", {}, True),
    ]

    print("\n🧪 Testing tool execution:")
    passed = 0
    failed = 0

    for tool_name, args, expected_success in test_cases:
        if tool_name not in server.generated_tools:
            print(f"  ❌ {tool_name}: Tool not found")
            failed += 1
            continue

        tool_function = server.generated_tools[tool_name]["function"]

        try:
            result = await tool_function(**args)
            success = result.get("success", False)

            if success == expected_success:
                print(f"  ✅ {tool_name}: Working correctly")
                passed += 1

                # Show sample output for reflect command
                if tool_name == "reflect" and success:
                    output = result.get("raw_output", "")
                    if output.startswith("{"):
                        data = json.loads(output)
                        print(f"     → Found {len(data)} CLI items")
            else:
                print(f"  ❌ {tool_name}: Expected success={expected_success}, got {success}")
                if not success:
                    print(f"     → Error: {result.get('error', 'Unknown')}")
                failed += 1

        except Exception as e:
            print(f"  ❌ {tool_name}: Exception - {str(e)}")
            failed += 1

    # Summary
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    print(f"✨ Success rate: {passed/(passed+failed)*100:.1f}%")

    return passed > 0 and failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_mcp_tools())
    print(f"\n{'✅ All tests passed!' if success else '❌ Some tests failed'}")
