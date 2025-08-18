# \!/usr/bin/env python3
import asyncio
import sys

sys.path.append("/workspaces/Tmux-Orchestrator")


async def test_tool_definitions():
    """Test MCP tool definitions with proper async"""
    print("=== Testing Tool Definitions (Async) ===\n")

    try:
        from tmux_orchestrator.mcp_server import list_tools

        # Call the async function properly
        tools = await list_tools()

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

                # Validate schema has required JSON Schema fields
                if "type" in schema and "properties" in schema:
                    print("   ✅ Valid JSON Schema structure")
                else:
                    print("   ⚠️  Missing required schema fields")
            else:
                print("   ❌ Invalid schema format")

        # Check for core functionality tools
        tool_names = [t.name for t in tools]
        core_tools = [
            "list_agents",
            "spawn_agent",
            "send_message",
            "restart_agent",
            "agent_status",
            "deploy_team",
            "team_broadcast",
        ]

        print("\n=== Core Tools Verification ===")
        found_tools = 0
        for core_tool in core_tools:
            if core_tool in tool_names:
                print(f"✅ {core_tool}")
                found_tools += 1
            else:
                print(f"❌ {core_tool} missing")

        print(f"\nSummary: {found_tools}/{len(core_tools)} core tools found")
        print(f"Total tools available: {len(tools)}")

        return len(tools) > 0 and found_tools >= len(core_tools) * 0.8

    except Exception as e:
        print(f"❌ Tool definition test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_tool_definitions())
    print(f"\n=== Result: {'PASS' if success else 'FAIL'} ===")
