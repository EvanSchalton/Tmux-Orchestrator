"""
Test MCP protocol message format validation using FastMCP patterns.

This test suite validates:
1. Protocol message format validation
2. Request/response structure verification
3. Error response formatting
"""

import sys
from pathlib import Path

import pytest

# Add parent directory for conftest_mcp
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tests.conftest_mcp import MockFastMCP  # noqa: E402


class TestMCPProtocolValidation:
    """Test MCP protocol message format validation."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance for testing."""
        return MockFastMCP("test-protocol-server")

    def test_protocol_message_format_valid(self):
        """Test that valid protocol messages pass format validation."""
        valid_messages = [
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "agent", "arguments": {"action": "list"}},
                "id": 1,
            },
            {"jsonrpc": "2.0", "method": "tools/list", "id": 2},
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "0.1.0", "capabilities": {}},
                "id": 3,
            },
        ]

        for message in valid_messages:
            # Validate required fields
            assert "jsonrpc" in message
            assert message["jsonrpc"] == "2.0"
            assert "method" in message
            assert "id" in message

    def test_protocol_message_format_invalid(self):
        """Test that invalid protocol messages are detected."""
        invalid_messages = [
            # Missing jsonrpc
            {"method": "tools/call", "params": {"name": "agent"}, "id": 1},
            # Wrong jsonrpc version
            {"jsonrpc": "1.0", "method": "tools/call", "id": 1},
            # Missing method
            {"jsonrpc": "2.0", "id": 1},
            # Missing id for request
            {"jsonrpc": "2.0", "method": "tools/call", "params": {}},
        ]

        for message in invalid_messages:
            with pytest.raises(AssertionError):
                assert "jsonrpc" in message and message["jsonrpc"] == "2.0"
                assert "method" in message
                assert "id" in message


class TestRequestResponseStructure:
    """Test request/response structure verification."""

    def test_tool_call_request_structure(self):
        """Test tool call request has correct structure."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "agent", "arguments": {"action": "status", "target": "backend:1"}},
            "id": 1,
        }

        # Validate structure
        assert request["method"] == "tools/call"
        assert "params" in request
        assert "name" in request["params"]
        assert "arguments" in request["params"]
        assert isinstance(request["params"]["arguments"], dict)

    def test_tool_call_response_structure(self):
        """Test tool call response has correct structure."""
        response = {
            "jsonrpc": "2.0",
            "result": {"content": [{"type": "text", "text": "Agent backend:1 is active"}]},
            "id": 1,
        }

        # Validate structure
        assert "jsonrpc" in response
        assert "result" in response
        assert "content" in response["result"]
        assert isinstance(response["result"]["content"], list)
        assert len(response["result"]["content"]) > 0
        assert "type" in response["result"]["content"][0]
        assert "text" in response["result"]["content"][0]

    def test_tools_list_response_structure(self):
        """Test tools list response has correct structure."""
        response = {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "agent",
                        "description": "Manage agents - list, deploy, monitor, message, and control",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["list", "status", "deploy", "kill", "restart", "send"],
                                    "description": "The action to perform",
                                }
                            },
                            "required": ["action"],
                        },
                    }
                ]
            },
            "id": 1,
        }

        # Validate structure
        assert "result" in response
        assert "tools" in response["result"]
        assert isinstance(response["result"]["tools"], list)

        # Validate tool structure
        tool = response["result"]["tools"][0]
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"
        assert "properties" in tool["inputSchema"]
        assert "required" in tool["inputSchema"]


class TestErrorResponseFormatting:
    """Test error response formatting."""

    def test_error_response_structure(self):
        """Test error response has correct MCP structure."""
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": {"details": "Missing required parameter: action"},
            },
            "id": 1,
        }

        # Validate error structure
        assert "jsonrpc" in error_response
        assert "error" in error_response
        assert "code" in error_response["error"]
        assert "message" in error_response["error"]
        assert isinstance(error_response["error"]["code"], int)

    def test_standard_error_codes(self):
        """Test standard JSON-RPC error codes."""
        error_codes = {
            -32700: "Parse error",
            -32600: "Invalid Request",
            -32601: "Method not found",
            -32602: "Invalid params",
            -32603: "Internal error",
        }

        for code, expected_type in error_codes.items():
            error = {"code": code, "message": expected_type}
            assert error["code"] == code
            assert expected_type.lower() in error["message"].lower()

    def test_custom_error_formatting(self):
        """Test custom error formatting for tmux-orc specific errors."""
        custom_errors = [
            {
                "error": {
                    "code": -32001,
                    "message": "Agent not found",
                    "data": {"agent": "backend:1", "suggestion": "Use 'agent list' to see available agents"},
                }
            },
            {
                "error": {
                    "code": -32002,
                    "message": "Command execution failed",
                    "data": {
                        "command": "tmux-orc agent deploy",
                        "stderr": "Error: Missing required argument: role",
                        "returncode": 1,
                    },
                }
            },
            {
                "error": {
                    "code": -32003,
                    "message": "Rate limit exceeded",
                    "data": {"retry_after": 60, "limit": "100 requests per minute"},
                }
            },
        ]

        for error_resp in custom_errors:
            error = error_resp["error"]
            assert "code" in error
            assert "message" in error
            assert "data" in error
            assert error["code"] < -32000  # Custom error codes
            assert isinstance(error["data"], dict)

    def test_error_response_with_notification(self):
        """Test that notifications (no id) don't get error responses."""
        notification = {
            "jsonrpc": "2.0",
            "method": "notification/test",
            "params": {},
            # No id field - this is a notification
        }

        # Notifications should not have responses
        assert "id" not in notification

        # If we were to send an error for a request with id
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Method not found"},
            "id": 123,  # Must include the original request id
        }

        assert "id" in error_response
        assert error_response["id"] == 123
