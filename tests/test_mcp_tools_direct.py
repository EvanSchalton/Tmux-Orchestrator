# \!/usr/bin/env python3
import sys

sys.path.append("/workspaces/Tmux-Orchestrator")


def test_tool_definitions():
    """Test MCP tool definitions directly"""
    print("=== Testing Tool Definitions Directly ===\n")

    try:
        from tmux_orchestrator.mcp_server import list_tools

        # Call the decorated function directly
        tools = list_tools()

        print(f"✅ Found {len(tools)} tools defined")

        # Test first few tools
        for i, tool in enumerate(tools[:5]):
            print(f"\n{i+1}. Tool: {tool.name}")
            print(f"   Description: {tool.description[:60]}...")

            # Check schema structure
            schema = tool.inputSchema
            if isinstance(schema, dict):
                print(f"   Schema type: {schema.get('type', 'unknown')}")
                properties = schema.get("properties", {})
                required = schema.get("required", [])
                print(f"   Properties: {len(properties)}, Required: {len(required)}")
            else:
                print("   ⚠️  Invalid schema format")

        # Check for required tools
        tool_names = [t.name for t in tools]
        required_tools = ["list_agents", "spawn_agent", "send_message", "restart_agent"]

        print("\n=== Required Tools Check ===")
        for req_tool in required_tools:
            if req_tool in tool_names:
                print(f"✅ {req_tool}")
            else:
                print(f"❌ {req_tool} missing")

        return True

    except Exception as e:
        print(f"❌ Tool definition test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_tool_definitions()
