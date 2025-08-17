#!/usr/bin/env python3
"""
Direct MCP Server Testing - Tests the actual MCP server functionality
"""

import asyncio
import json
import subprocess
import sys
import time


async def test_mcp_server_tools():
    """Test the MCP server by actually running it and checking tool generation."""

    print("🔍 Testing Fresh CLI Reflection MCP Server")
    print("=" * 60)

    # Test 1: CLI Structure Discovery
    print("\n1️⃣ Testing CLI Structure Discovery...")
    result = subprocess.run(
        [
            "python",
            "-c",
            """
import asyncio
import sys
sys.path.append('/workspaces/Tmux-Orchestrator')
from tmux_orchestrator.mcp_fresh import FreshCLIToMCPServer

async def test():
    server = FreshCLIToMCPServer('test-server')
    cli_structure = await server.discover_cli_structure()
    print(f'Discovered {len(cli_structure)} CLI items')

    # Check for our 6 target commands
    target_commands = ['list', 'status', 'quick-deploy', 'spawn-orc', 'execute', 'reflect']
    found_commands = []

    for cmd in target_commands:
        if cmd in cli_structure and cli_structure[cmd].get('type') == 'command':
            found_commands.append(cmd)
            print(f'  ✅ Found: {cmd}')
        else:
            print(f'  ❌ Missing: {cmd}')

    print(f'Coverage: {len(found_commands)}/{len(target_commands)} commands')
    return len(found_commands) == len(target_commands)

result = asyncio.run(test())
exit(0 if result else 1)
        """,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode == 0:
        print("✅ CLI Discovery Test: PASSED")
        print(result.stdout)
    else:
        print("❌ CLI Discovery Test: FAILED")
        print(result.stderr)
        return False

    # Test 2: Tool Generation
    print("\n2️⃣ Testing MCP Tool Generation...")
    result = subprocess.run(
        [
            "python",
            "-c",
            """
import asyncio
import sys
sys.path.append('/workspaces/Tmux-Orchestrator')
from tmux_orchestrator.mcp_fresh import FreshCLIToMCPServer

async def test():
    server = FreshCLIToMCPServer('test-server')
    await server.discover_cli_structure()
    generated_tools = server.generate_all_mcp_tools()

    target_tools = ['list', 'status', 'quick_deploy', 'spawn_orc', 'execute', 'reflect']
    found_tools = []

    print(f'Generated {len(generated_tools)} MCP tools:')
    for tool_name in generated_tools:
        print(f'  • {tool_name} -> {generated_tools[tool_name]["command_name"]}')
        if tool_name in target_tools:
            found_tools.append(tool_name)

    print(f'Tool Coverage: {len(found_tools)}/{len(target_tools)} target tools')
    return len(found_tools) == len(target_tools)

result = asyncio.run(test())
exit(0 if result else 1)
        """,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode == 0:
        print("✅ Tool Generation Test: PASSED")
        print(result.stdout)
    else:
        print("❌ Tool Generation Test: FAILED")
        print(result.stderr)
        return False

    # Test 3: Tool Function Creation
    print("\n3️⃣ Testing Tool Function Creation...")
    result = subprocess.run(
        [
            "python",
            "-c",
            """
import asyncio
import sys
sys.path.append('/workspaces/Tmux-Orchestrator')
from tmux_orchestrator.mcp_fresh import FreshCLIToMCPServer

async def test():
    server = FreshCLIToMCPServer('test-server')
    await server.discover_cli_structure()
    server.generate_all_mcp_tools()

    # Test that tool functions are callable
    if 'list' in server.generated_tools:
        tool_func = server.generated_tools['list']['function']
        print(f'✅ List tool function created: {tool_func.__name__}')

        # Test argument conversion
        cli_args = server._convert_kwargs_to_cli_args({
            'args': ['--json'],
            'options': {'format': 'json'}
        })
        print(f'✅ Argument conversion: {cli_args}')

        return True
    return False

result = asyncio.run(test())
exit(0 if result else 1)
        """,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode == 0:
        print("✅ Tool Function Test: PASSED")
        print(result.stdout)
    else:
        print("❌ Tool Function Test: FAILED")
        print(result.stderr)
        return False

    return True


async def test_performance_metrics():
    """Test performance characteristics of the MCP server."""

    print("\n4️⃣ Testing Performance Metrics...")

    # Measure CLI discovery time
    start_time = time.time()
    result = subprocess.run(["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=30)
    discovery_time = time.time() - start_time

    if result.returncode == 0:
        cli_data = json.loads(result.stdout)
        commands = [k for k, v in cli_data.items() if isinstance(v, dict) and v.get("type") == "command"]

        print("✅ CLI Discovery Performance:")
        print(f"   • Discovery time: {discovery_time:.2f}s")
        print(f"   • Commands discovered: {len(commands)}")
        print(f"   • Rate: {len(commands)/discovery_time:.1f} commands/sec")

        return discovery_time < 5.0  # Should be under 5 seconds
    else:
        print("❌ Performance test failed")
        return False


async def main():
    """Main test runner."""
    print("🚀 Starting MCP Server Integration Tests")

    try:
        # Test server functionality
        server_tests_passed = await test_mcp_server_tools()
        performance_tests_passed = await test_performance_metrics()

        print("\n" + "=" * 60)
        print("📊 FINAL TEST RESULTS")
        print("=" * 60)

        print(f"🔧 Server Functionality: {'✅ PASSED' if server_tests_passed else '❌ FAILED'}")
        print(f"⚡ Performance Tests: {'✅ PASSED' if performance_tests_passed else '❌ FAILED'}")

        overall_success = server_tests_passed and performance_tests_passed
        print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")

        if overall_success:
            print("\n🎉 The Fresh CLI Reflection MCP Server is fully functional!")
            print("   • All 6 target tools are available")
            print("   • Tool generation works correctly")
            print("   • Performance is within acceptable limits")

        return overall_success

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
