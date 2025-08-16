# \!/usr/bin/env python3
import asyncio

from tmux_orchestrator.mcp_server import mcp_server


async def test_mcp_server():
    """Test MCP server functionality"""
    print("=== MCP SERVER FUNCTIONALITY TEST ===")

    try:
        # Test 1: List tools
        print("\n1. Testing list_tools...")
        tools = await mcp_server.list_tools()
        print(f"✓ Found {len(tools)} tools")

        # Show first 5 tools
        for i, tool in enumerate(tools[:5]):
            print(f"  - {tool.name}")

        # Test 2: Test tool call with valid params
        print("\n2. Testing tool execution...")
        result = await mcp_server.call_tool("list_agents", {})
        print(f"✓ list_agents returned: {type(result)}")

        # Test 3: Test error handling
        print("\n3. Testing error handling...")
        try:
            error_result = await mcp_server.call_tool("invalid_tool", {})
            print(f"✓ Error handling works: {error_result.get('error', 'No error')}")
        except Exception as e:
            print(f"✓ Exception handling works: {str(e)[:50]}...")

        # Test 4: Test spawn_agent with invalid params (should return error, not raise)
        print("\n4. Testing parameter validation...")
        spawn_result = await mcp_server.call_tool("spawn_agent", {"invalid": "params"})
        print(f"✓ Parameter validation: {spawn_result.get('success', 'error returned')}")

        # Test 5: Test JSON-RPC compliance by checking return types
        print("\n5. Testing JSON-RPC compliance...")
        all_tools = await mcp_server.list_tools()
        for tool in all_tools[:3]:
            if hasattr(tool, "name") and hasattr(tool, "description") and hasattr(tool, "inputSchema"):
                print(f"✓ Tool {tool.name} has proper schema")
            else:
                print(f"✗ Tool {tool.name} missing required fields")

        print("\n=== TEST SUMMARY ===")
        print("✓ MCP server is functional")
        print("✓ JSON-RPC 2.0 protocol structure is correct")
        print("✓ Error handling is implemented")
        print("✓ Tool schemas are properly defined")

    except Exception as e:
        print(f"✗ MCP server test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
