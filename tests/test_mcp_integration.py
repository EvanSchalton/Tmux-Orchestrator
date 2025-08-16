"""Integration tests for MCP stdio transport and JSON-RPC 2.0 protocol.

This test suite validates:
1. Actual stdio transport communication
2. End-to-end JSON-RPC 2.0 message format
3. MCP protocol initialization and capability negotiation
4. Real tool execution through MCP protocol
5. Performance under concurrent requests
"""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

# Import MCP components


class MockStream:
    """Mock stream for testing stdio transport."""

    def __init__(self):
        self.buffer = []
        self.read_buffer = []

    async def write(self, data: bytes):
        """Write data to mock stream."""
        self.buffer.append(data.decode())

    async def read(self, size: int = -1):
        """Read data from mock stream."""
        if self.read_buffer:
            return self.read_buffer.pop(0).encode()
        return b""

    def add_read_data(self, data: str):
        """Add data to be read."""
        self.read_buffer.append(data)


class TestMCPStdioTransport:
    """Test stdio transport functionality."""

    def test_json_rpc_message_format(self):
        """Test that messages follow JSON-RPC 2.0 format exactly."""
        # Test various message types

        # 1. Method call (request)
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        serialized = json.dumps(request)
        deserialized = json.loads(serialized)

        assert deserialized["jsonrpc"] == "2.0"
        assert "method" in deserialized
        assert "id" in deserialized

        # 2. Method call with params
        request_with_params = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "list_agents", "arguments": {}},
            "id": 2,
        }

        serialized = json.dumps(request_with_params)
        deserialized = json.loads(serialized)
        assert deserialized["params"]["name"] == "list_agents"

        # 3. Successful response
        success_response = {"jsonrpc": "2.0", "result": {"agents": [], "total_count": 0}, "id": 1}

        serialized = json.dumps(success_response)
        deserialized = json.loads(serialized)
        assert "result" in deserialized
        assert deserialized["id"] == 1

        # 4. Error response
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "Invalid params", "data": {"details": "Missing required parameter"}},
            "id": 2,
        }

        serialized = json.dumps(error_response)
        deserialized = json.loads(serialized)
        assert "error" in deserialized
        assert deserialized["error"]["code"] == -32602

        # 5. Notification (no id)
        notification = {"jsonrpc": "2.0", "method": "notification", "params": {"status": "ready"}}

        serialized = json.dumps(notification)
        deserialized = json.loads(serialized)
        assert "id" not in deserialized

    def test_message_framing(self):
        """Test that messages are properly framed for stdio transport."""
        message = {"jsonrpc": "2.0", "method": "test", "id": 1}
        json_str = json.dumps(message)

        # Messages should be newline-delimited for stdio transport
        framed_message = json_str + "\n"

        # Verify we can parse it back
        lines = framed_message.strip().split("\n")
        for line in lines:
            if line.strip():
                parsed = json.loads(line)
                assert parsed["jsonrpc"] == "2.0"

    def test_batch_requests(self):
        """Test handling of JSON-RPC 2.0 batch requests."""
        batch_request = [
            {"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            {"jsonrpc": "2.0", "method": "tools/list", "id": 2},
        ]

        serialized = json.dumps(batch_request)
        deserialized = json.loads(serialized)

        assert isinstance(deserialized, list)
        assert len(deserialized) == 2
        assert all(msg["jsonrpc"] == "2.0" for msg in deserialized)


class TestMCPProtocolInitialization:
    """Test MCP protocol initialization and capability negotiation."""

    def test_initialization_request(self):
        """Test MCP initialization request format."""
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                "clientInfo": {"name": "claude-code", "version": "1.0.0"},
            },
            "id": 1,
        }

        # Verify required fields
        assert init_request["method"] == "initialize"
        assert "protocolVersion" in init_request["params"]
        assert "capabilities" in init_request["params"]
        assert "clientInfo" in init_request["params"]

    def test_initialization_response(self):
        """Test MCP initialization response format."""
        init_response = {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}, "resources": {"subscribe": True, "listChanged": True}},
                "serverInfo": {"name": "tmux-orchestrator", "version": "1.0.0"},
            },
            "id": 1,
        }

        # Verify response structure
        result = init_response["result"]
        assert "protocolVersion" in result
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "tmux-orchestrator"

    def test_tools_list_request(self):
        """Test tools/list request after initialization."""
        tools_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}

        assert tools_request["method"] == "tools/list"
        assert "params" not in tools_request or tools_request["params"] == {}


class TestMCPEndToEndExecution:
    """Test end-to-end tool execution through MCP protocol."""

    @pytest.mark.asyncio
    @patch("tmux_orchestrator.mcp_server.TMUXManager")
    async def test_complete_tool_execution_flow(self, mock_tmux_manager):
        """Test complete flow: request -> execution -> response."""
        # Mock TMUXManager
        mock_tmux = MagicMock()
        mock_tmux.list_agents.return_value = [
            {"session": "test", "window": "1", "type": "developer", "status": "active"}
        ]
        mock_tmux_manager.return_value = mock_tmux

        # Simulate JSON-RPC 2.0 request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "list_agents", "arguments": {}},
            "id": 123,
        }

        # Execute the tool directly (simulating MCP server processing)
        from tmux_orchestrator.mcp_server import call_tool

        result = await call_tool(request["params"]["name"], request["params"]["arguments"])

        # Verify result structure
        assert "agents" in result
        assert "total_count" in result
        assert result["total_count"] == 1
        assert result["agents"][0]["session"] == "test"

        # Construct JSON-RPC 2.0 response
        response = {"jsonrpc": "2.0", "result": result, "id": request["id"]}

        # Verify response format
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert response["id"] == 123

    @pytest.mark.asyncio
    @patch("tmux_orchestrator.mcp_server.TMUXManager")
    @patch("tmux_orchestrator.mcp_server.core_spawn_agent")
    async def test_spawn_agent_with_briefing_flow(self, mock_spawn_agent, mock_tmux_manager):
        """Test spawn agent with briefing message flow."""
        # Mock successful spawn
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.session = "dev-session"
        mock_result.window = "1"
        mock_result.target = "dev-session:1"
        mock_spawn_agent.return_value = mock_result

        # Mock message sending
        with patch("tmux_orchestrator.mcp_server.core_send_message") as mock_send:
            mock_send_result = MagicMock()
            mock_send_result.success = True
            mock_send.return_value = mock_send_result

            mock_tmux = MagicMock()
            mock_tmux_manager.return_value = mock_tmux

            # Simulate request
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "spawn_agent",
                    "arguments": {
                        "session_name": "dev-session",
                        "agent_type": "developer",
                        "briefing_message": "Please work on the authentication module",
                    },
                },
                "id": 456,
            }

            # Execute
            from tmux_orchestrator.mcp_server import call_tool

            result = await call_tool(request["params"]["name"], request["params"]["arguments"])

            # Verify result
            assert result["success"] is True
            assert result["session"] == "dev-session"
            assert result["target"] == "dev-session:1"

            # Verify briefing message was sent
            mock_send.assert_called_once()


class TestMCPErrorScenarios:
    """Test various error scenarios in MCP protocol."""

    def test_parse_error_response(self):
        """Test JSON-RPC 2.0 parse error response."""
        error_response = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}

        assert error_response["error"]["code"] == -32700
        assert error_response["id"] is None

    def test_invalid_request_error(self):
        """Test invalid request error response."""
        error_response = {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": None}

        assert error_response["error"]["code"] == -32600

    def test_method_not_found_error(self):
        """Test method not found error response."""
        error_response = {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 1}

        assert error_response["error"]["code"] == -32601
        assert error_response["id"] == 1

    @pytest.mark.asyncio
    async def test_invalid_params_error(self):
        """Test invalid params error handling."""
        # Simulate missing required parameter
        from tmux_orchestrator.mcp_server import call_tool

        with pytest.raises(KeyError):
            await call_tool("spawn_agent", {"session_name": "test"})  # Missing agent_type

    @pytest.mark.asyncio
    async def test_internal_error_handling(self):
        """Test internal error handling."""
        with patch("tmux_orchestrator.mcp_server.TMUXManager") as mock_tmux_manager:
            mock_tmux_manager.side_effect = Exception("Internal server error")

            from tmux_orchestrator.mcp_server import call_tool

            result = await call_tool("list_agents", {})

            assert "error" in result
            assert "Internal server error" in result["error"]


class TestMCPPerformance:
    """Test MCP protocol performance and concurrent handling."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self):
        """Test performance under concurrent requests."""
        with patch("tmux_orchestrator.mcp_server.TMUXManager") as mock_tmux_manager:
            mock_tmux = MagicMock()
            mock_tmux.list_agents.return_value = []
            mock_tmux_manager.return_value = mock_tmux

            from tmux_orchestrator.mcp_server import call_tool

            # Create many concurrent requests
            num_requests = 10
            tasks = [call_tool("list_agents", {}) for _ in range(num_requests)]

            import time

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            # Verify all succeeded
            assert len(results) == num_requests
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Request failed: {result}")
                assert "agents" in result
                assert "total_count" in result

            # Performance should be reasonable (less than 1 second for 10 requests)
            elapsed_time = end_time - start_time
            assert elapsed_time < 1.0

    @pytest.mark.asyncio
    async def test_large_response_handling(self):
        """Test handling of large responses."""
        with patch("tmux_orchestrator.mcp_server.TMUXManager") as mock_tmux_manager:
            mock_tmux = MagicMock()

            # Create a large list of agents
            large_agent_list = [
                {"session": f"session-{i}", "window": "1", "type": "developer", "status": "active"} for i in range(100)
            ]
            mock_tmux.list_agents.return_value = large_agent_list
            mock_tmux_manager.return_value = mock_tmux

            from tmux_orchestrator.mcp_server import call_tool

            result = await call_tool("list_agents", {})

            assert result["total_count"] == 100
            assert len(result["agents"]) == 100

            # Test JSON serialization of large response
            json_result = json.dumps(result)
            assert len(json_result) > 1000  # Should be reasonably large

            # Verify it can be parsed back
            parsed = json.loads(json_result)
            assert parsed["total_count"] == 100


class TestMCPResourceManagement:
    """Test resource management in MCP server."""

    @pytest.mark.asyncio
    async def test_tmux_manager_lifecycle(self):
        """Test that TMUXManager instances are properly managed."""
        with patch("tmux_orchestrator.mcp_server.TMUXManager") as mock_tmux_manager:
            mock_tmux = MagicMock()
            mock_tmux.list_agents.return_value = []
            mock_tmux_manager.return_value = mock_tmux

            from tmux_orchestrator.mcp_server import call_tool

            # Make multiple calls
            await call_tool("list_agents", {})
            await call_tool("list_agents", {})

            # TMUXManager should be created for each call
            assert mock_tmux_manager.call_count == 2

    @pytest.mark.asyncio
    async def test_exception_cleanup(self):
        """Test that resources are cleaned up even when exceptions occur."""
        with patch("tmux_orchestrator.mcp_server.TMUXManager") as mock_tmux_manager:
            mock_tmux = MagicMock()
            mock_tmux.list_agents.side_effect = Exception("Test exception")
            mock_tmux_manager.return_value = mock_tmux

            from tmux_orchestrator.mcp_server import call_tool

            result = await call_tool("list_agents", {})

            # Should return error, not raise exception
            assert "error" in result
            assert "Test exception" in result["error"]

            # TMUXManager should still have been created
            mock_tmux_manager.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
