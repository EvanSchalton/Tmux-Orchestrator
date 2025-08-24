#!/usr/bin/env python3
"""
QA Test: MCP Protocol Functionality

This script tests the MCP (Model Context Protocol) server functionality
including basic operations, tool registration, and error handling.

Test scenarios:
1. MCP server startup and basic functionality
2. Tool registration and availability
3. JSON-RPC request/response handling
4. Error handling for malformed requests
"""

import json
import logging
import subprocess
import time
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MCPProtocolTest:
    """Test class for MCP protocol functionality."""

    def __init__(self):
        self.server_process: subprocess.Popen | None = None
        self.test_results = {}
        self.errors = []

    def start_mcp_server(self, timeout: int = 10) -> bool:
        """Start the MCP server and test basic connectivity."""
        logger.info("🚀 Starting MCP server...")

        try:
            # Start the MCP server
            self.server_process = subprocess.Popen(
                ["python", "-m", "tmux_orchestrator.mcp_server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # Give server time to start
            time.sleep(2)

            # Check if process is still running
            if self.server_process.poll() is not None:
                stderr_output = self.server_process.stderr.read()
                logger.error(f"❌ MCP server failed to start: {stderr_output}")
                return False

            logger.info("✅ MCP server started successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to start MCP server: {e}")
            return False

    def stop_mcp_server(self) -> None:
        """Stop the MCP server."""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                logger.info("✅ MCP server stopped")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                logger.warning("⚠️  MCP server killed (did not terminate gracefully)")
            except Exception as e:
                logger.error(f"❌ Error stopping MCP server: {e}")

    def send_mcp_request(self, request: dict[str, Any], timeout: int = 5) -> dict[str, Any] | None:
        """Send a JSON-RPC request to the MCP server."""
        if not self.server_process:
            logger.error("❌ MCP server not running")
            return None

        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.server_process.stdin.write(request_json)
            self.server_process.stdin.flush()

            # Read response (with timeout)
            response_line = self.server_process.stdout.readline()
            if response_line.strip():
                return json.loads(response_line.strip())

            return None

        except Exception as e:
            logger.error(f"❌ Error sending MCP request: {e}")
            return None

    def test_server_initialization(self) -> dict[str, Any]:
        """Test basic server initialization and capabilities."""
        logger.info("🔍 Testing server initialization...")

        # Test 1: Initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"roots": {"listChanged": True}},
                "clientInfo": {"name": "qa-test-client", "version": "1.0.0"},
            },
        }

        response = self.send_mcp_request(init_request)

        if response:
            logger.info("✅ Server initialization successful")
            return {"test": "server_initialization", "success": True, "response": response}
        else:
            logger.error("❌ Server initialization failed")
            return {"test": "server_initialization", "success": False, "error": "No response received"}

    def test_tools_list(self) -> dict[str, Any]:
        """Test listing available tools."""
        logger.info("🔍 Testing tools list...")

        list_tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

        response = self.send_mcp_request(list_tools_request)

        if response and "result" in response:
            tools = response["result"].get("tools", [])
            logger.info(f"✅ Found {len(tools)} tools")
            for tool in tools:
                logger.info(f"   - {tool.get('name', 'unknown')}")

            return {
                "test": "tools_list",
                "success": True,
                "tools_count": len(tools),
                "tools": [tool.get("name") for tool in tools],
            }
        else:
            logger.error("❌ Tools list failed")
            return {"test": "tools_list", "success": False, "error": "Failed to get tools list"}

    def test_spawn_agent_tool(self) -> dict[str, Any]:
        """Test the spawn agent tool functionality."""
        logger.info("🔍 Testing spawn agent tool...")

        spawn_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "spawn_agent",
                "arguments": {
                    "role": "test-agent",
                    "target": "qa-test:1",
                    "briefing": "This is a QA test agent for MCP protocol testing",
                },
            },
        }

        response = self.send_mcp_request(spawn_request)

        if response and "result" in response:
            logger.info("✅ Spawn agent tool call successful")
            return {"test": "spawn_agent_tool", "success": True, "response": response["result"]}
        else:
            logger.error("❌ Spawn agent tool call failed")
            return {
                "test": "spawn_agent_tool",
                "success": False,
                "error": response.get("error") if response else "No response",
            }

    def test_error_handling(self) -> dict[str, Any]:
        """Test error handling for malformed requests."""
        logger.info("🔍 Testing error handling...")

        test_cases = [
            {"name": "malformed_json", "request": "{ invalid json", "expected": "parse_error"},
            {
                "name": "invalid_method",
                "request": {"jsonrpc": "2.0", "id": 4, "method": "nonexistent_method"},
                "expected": "method_not_found",
            },
            {
                "name": "missing_params",
                "request": {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    # Missing required params
                },
                "expected": "invalid_params",
            },
        ]

        results = []
        for test_case in test_cases:
            logger.info(f"  Testing: {test_case['name']}")

            if isinstance(test_case["request"], str):
                # Send malformed JSON
                try:
                    self.server_process.stdin.write(test_case["request"] + "\n")
                    self.server_process.stdin.flush()
                    response_line = self.server_process.stdout.readline()
                    response = json.loads(response_line.strip()) if response_line.strip() else None
                except Exception:
                    response = None
            else:
                response = self.send_mcp_request(test_case["request"])

            if response and "error" in response:
                logger.info(f"    ✅ Error handled correctly: {response['error'].get('code', 'unknown')}")
                results.append(
                    {"test_case": test_case["name"], "success": True, "error_code": response["error"].get("code")}
                )
            else:
                logger.warning(f"    ⚠️  Unexpected response for {test_case['name']}")
                results.append({"test_case": test_case["name"], "success": False, "response": response})

        return {"test": "error_handling", "results": results, "success": all(r["success"] for r in results)}

    def test_basic_functionality(self) -> dict[str, Any]:
        """Test basic MCP functionality without complex operations."""
        logger.info("🔍 Testing basic MCP functionality...")

        # Simple ping-like test
        ping_request = {"jsonrpc": "2.0", "id": 6, "method": "ping"}

        response = self.send_mcp_request(ping_request)

        # Even if ping isn't implemented, we should get a proper JSON-RPC error
        if response:
            if "result" in response:
                logger.info("✅ Basic functionality test passed (ping response)")
                return {"test": "basic_functionality", "success": True, "type": "ping_success"}
            elif "error" in response:
                logger.info("✅ Basic functionality test passed (proper error response)")
                return {"test": "basic_functionality", "success": True, "type": "proper_error"}

        logger.error("❌ Basic functionality test failed")
        return {"test": "basic_functionality", "success": False}

    def run_comprehensive_mcp_test(self) -> dict[str, Any]:
        """Run comprehensive MCP protocol test."""
        logger.info("🚀 Starting comprehensive MCP protocol test...")
        logger.info("=" * 70)

        test_results = {}

        try:
            # Start server
            if not self.start_mcp_server():
                return {"error": "Failed to start MCP server", "server_startup": False}

            test_results["server_startup"] = True

            # Run tests
            test_results["initialization"] = self.test_server_initialization()
            test_results["basic_functionality"] = self.test_basic_functionality()
            test_results["tools_list"] = self.test_tools_list()
            test_results["error_handling"] = self.test_error_handling()

            # Optional: Test specific tools if server is responding well
            if test_results["tools_list"]["success"]:
                test_results["spawn_agent"] = self.test_spawn_agent_tool()

        except Exception as e:
            logger.error(f"❌ Test execution error: {e}")
            test_results["execution_error"] = str(e)

        finally:
            self.stop_mcp_server()

        # Generate summary
        successful_tests = sum(1 for test in test_results.values() if isinstance(test, dict) and test.get("success"))
        total_tests = len([test for test in test_results.values() if isinstance(test, dict) and "success" in test])

        test_results["summary"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": f"{(successful_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%",
            "server_started": test_results.get("server_startup", False),
        }

        logger.info("=" * 70)
        logger.info(f"🏁 MCP test complete: {successful_tests}/{total_tests} tests passed")

        if test_results["summary"]["server_started"]:
            logger.info("✅ MCP server startup successful")
        else:
            logger.error("❌ MCP server startup failed")

        return test_results


def main():
    """Run the MCP protocol test."""
    tester = MCPProtocolTest()
    results = tester.run_comprehensive_mcp_test()

    # Save results
    results_file = "qa_mcp_protocol_test_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"📄 Results saved to: {results_file}")

    # Return appropriate exit code
    if not results.get("server_startup", False):
        logger.error("🚨 MCP server failed to start")
        return 1
    elif results["summary"]["successful_tests"] < results["summary"]["total_tests"]:
        logger.warning("⚠️  Some MCP tests failed")
        return 1
    else:
        logger.info("✅ All MCP tests passed")
        return 0


if __name__ == "__main__":
    exit(main())
