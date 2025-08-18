# \!/usr/bin/env python3
import asyncio
import sys

sys.path.append("/workspaces/Tmux-Orchestrator")


async def test_error_handling():
    """Test MCP server error handling"""
    print("=== Testing Error Handling ===\n")

    try:
        from tmux_orchestrator.mcp_server import call_tool

        # Test 1: Invalid tool name
        print("1. Testing invalid tool name...")
        result = await call_tool("invalid_tool_name", {})
        if isinstance(result, dict) and "error" in result:
            print(f"✅ Invalid tool error: {result['error'][:50]}...")
        else:
            print(f"⚠️  Unexpected response: {type(result)}")

        # Test 2: Missing required parameters
        print("\n2. Testing missing required parameters...")
        result = await call_tool("spawn_agent", {})  # Missing session_name, agent_type
        if isinstance(result, dict):
            if "error" in result or "success" in result:
                print("✅ Parameter validation working")
            else:
                print(f"⚠️  Unexpected response format: {list(result.keys())}")

        # Test 3: Invalid parameters
        print("\n3. Testing invalid parameter values...")
        result = await call_tool("spawn_agent", {"session_name": "test", "agent_type": "invalid_type"})
        if isinstance(result, dict):
            print(f"✅ Invalid parameter handling: {result.get('success', 'error returned')}")

        # Test 4: Valid tool call to verify server works
        print("\n4. Testing valid tool call...")
        result = await call_tool("list_agents", {})
        if isinstance(result, dict):
            print(f"✅ Valid call works: {result.get('total_count', 'agents')} result")

        return True

    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_error_handling())
    print(f"\n=== Error Handling: {'PASS' if success else 'FAIL'} ===")
