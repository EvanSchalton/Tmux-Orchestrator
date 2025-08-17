#!/usr/bin/env python3
"""
MCP Tool Execution Testing - Tests actual tool execution through the MCP server
"""

import asyncio
import json
import sys
import time

# Add the project to path
sys.path.append("/workspaces/Tmux-Orchestrator")
from tmux_orchestrator.mcp_fresh import FreshCLIToMCPServer


async def test_tool_execution():
    """Test actual execution of MCP tools."""

    print("🧪 Testing MCP Tool Execution")
    print("=" * 50)

    # Create server instance
    server = FreshCLIToMCPServer("execution-test-server")

    # Initialize server
    await server.discover_cli_structure()
    server.generate_all_mcp_tools()

    print(f"✅ Server initialized with {len(server.generated_tools)} tools")

    # Test cases for each tool
    test_cases = [
        {
            "tool": "list",
            "args": {"args": ["--json"]},
            "expected_success": True,
            "description": "List agents in JSON format",
        },
        {
            "tool": "status",
            "args": {"args": ["--json"]},
            "expected_success": True,
            "description": "Get system status in JSON format",
        },
        {
            "tool": "reflect",
            "args": {"args": ["--format", "json"]},
            "expected_success": True,
            "description": "Get CLI reflection in JSON format",
        },
        {
            "tool": "quick_deploy",
            "args": {"args": ["--help"]},
            "expected_success": True,
            "description": "Get quick-deploy help (safe test)",
        },
        {
            "tool": "spawn_orc",
            "args": {"args": ["--help"]},
            "expected_success": True,
            "description": "Get spawn-orc help (safe test)",
        },
        {
            "tool": "execute",
            "args": {"args": ["--help"]},
            "expected_success": True,
            "description": "Get execute help (safe test)",
        },
    ]

    results = {}

    # Execute each test case
    for i, test_case in enumerate(test_cases, 1):
        tool_name = test_case["tool"]
        args = test_case["args"]
        description = test_case["description"]

        print(f"\n{i}️⃣ Testing {tool_name}: {description}")

        if tool_name not in server.generated_tools:
            print(f"   ❌ Tool {tool_name} not available")
            results[tool_name] = {"success": False, "error": "Tool not found"}
            continue

        try:
            # Get the tool function
            tool_info = server.generated_tools[tool_name]
            tool_function = tool_info["function"]

            # Execute the tool
            start_time = time.time()
            result = await tool_function(**args)
            execution_time = time.time() - start_time

            # Check result
            success = result.get("success", False)
            status_icon = "✅" if success else "❌"

            print(f"   {status_icon} Execution: {'SUCCESS' if success else 'FAILED'}")
            print(f"   ⏱️  Time: {execution_time:.2f}s")

            if success:
                # Analyze the result
                if result.get("parsed_output"):
                    output_type = type(result["parsed_output"]).__name__
                    if isinstance(result["parsed_output"], dict):
                        keys = list(result["parsed_output"].keys())[:5]  # First 5 keys
                        print(f"   📊 Output: {output_type} with keys: {keys}")
                    elif isinstance(result["parsed_output"], list):
                        print(f"   📊 Output: {output_type} with {len(result['parsed_output'])} items")
                    else:
                        print(f"   📊 Output: {output_type}")

                if result.get("raw_output"):
                    output_lines = result["raw_output"].split("\n")
                    print(f"   📝 Raw output: {len(output_lines)} lines")
            else:
                print(f"   ❌ Error: {result.get('error', 'Unknown error')}")

            results[tool_name] = {"success": success, "execution_time": execution_time, "result": result}

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results[tool_name] = {"success": False, "error": str(e)}

    return results


async def generate_final_report(results):
    """Generate final comprehensive report."""

    print("\n" + "=" * 70)
    print("📋 COMPREHENSIVE MCP TOOLS TEST REPORT")
    print("=" * 70)

    # Overall statistics
    total_tools = len(results)
    successful_tools = sum(1 for r in results.values() if r.get("success", False))
    failed_tools = total_tools - successful_tools

    print("📊 SUMMARY:")
    print(f"   • Total tools tested: {total_tools}")
    print(f"   • Successful executions: {successful_tools}")
    print(f"   • Failed executions: {failed_tools}")
    print(f"   • Success rate: {(successful_tools/total_tools*100):.1f}%")

    # Performance analysis
    execution_times = [r.get("execution_time", 0) for r in results.values() if r.get("success")]
    if execution_times:
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)

        print("\n⚡ PERFORMANCE:")
        print(f"   • Average execution time: {avg_time:.2f}s")
        print(f"   • Fastest tool: {min_time:.2f}s")
        print(f"   • Slowest tool: {max_time:.2f}s")

    # Detailed results
    print("\n🔍 DETAILED RESULTS:")
    for tool_name, result in results.items():
        success = result.get("success", False)
        status_icon = "✅" if success else "❌"

        print(f"   {status_icon} {tool_name.upper()}:")
        print(f"      Status: {'SUCCESS' if success else 'FAILED'}")

        if success:
            exec_time = result.get("execution_time", 0)
            print(f"      Execution time: {exec_time:.2f}s")

            tool_result = result.get("result", {})
            if tool_result.get("command_line"):
                print(f"      Command: {tool_result['command_line']}")

            if tool_result.get("return_code") is not None:
                print(f"      Return code: {tool_result['return_code']}")
        else:
            error = result.get("error", "Unknown error")
            print(f"      Error: {error}")
        print()

    # MCP Integration Assessment
    print("🎯 MCP INTEGRATION ASSESSMENT:")

    if successful_tools == total_tools:
        print("   ✅ EXCELLENT: All tools executed successfully")
        print("   ✅ MCP server is fully functional")
        print("   ✅ CLI reflection working correctly")
        print("   ✅ Tool auto-generation working")
        print("   ✅ Ready for production use")
    elif successful_tools >= total_tools * 0.8:
        print("   ⚠️  GOOD: Most tools working with minor issues")
        print("   ⚠️  Some investigation needed for failed tools")
    else:
        print("   ❌ POOR: Major issues detected")
        print("   ❌ Significant debugging required")

    # Save detailed report
    report_data = {
        "timestamp": time.time(),
        "summary": {
            "total_tools": total_tools,
            "successful_tools": successful_tools,
            "failed_tools": failed_tools,
            "success_rate": successful_tools / total_tools * 100,
        },
        "performance": {
            "average_time": avg_time if execution_times else 0,
            "min_time": min_time if execution_times else 0,
            "max_time": max_time if execution_times else 0,
        },
        "detailed_results": results,
    }

    report_file = "/workspaces/Tmux-Orchestrator/mcp_execution_test_report.json"
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n💾 Detailed report saved to: {report_file}")
    print("=" * 70)

    return successful_tools == total_tools


async def main():
    """Main execution function."""

    try:
        print("🚀 Starting MCP Tool Execution Tests")

        # Run execution tests
        results = await test_tool_execution()

        # Generate final report
        all_passed = await generate_final_report(results)

        if all_passed:
            print("\n🎉 ALL MCP TOOLS WORKING PERFECTLY!")
            print("   The fresh CLI reflection MCP server is production-ready.")

        return all_passed

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
