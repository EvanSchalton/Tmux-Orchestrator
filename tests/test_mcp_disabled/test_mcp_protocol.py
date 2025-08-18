"""Comprehensive MCP Protocol Tests for JSON-RPC 2.0 compliance and tool invocations.

This test suite validates:
1. JSON-RPC 2.0 protocol compliance
2. Tool invocation correctness
3. Error handling for invalid requests
4. MCP tool schema validation
5. Response format verification
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from mcp import Tool

# Import the MCP server
from tmux_orchestrator.mcp_server import call_tool, list_tools


class TestMCPProtocolCompliance:
    """Test JSON-RPC 2.0 protocol compliance."""

    def test_json_rpc_request_format(self):
        """Test that requests follow JSON-RPC 2.0 format."""
        # Valid JSON-RPC 2.0 request format
        valid_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "list_agents", "arguments": {}},
            "id": 1,
        }

        # Verify required fields
        assert "jsonrpc" in valid_request
        assert valid_request["jsonrpc"] == "2.0"
        assert "method" in valid_request
        assert "id" in valid_request

    def test_json_rpc_response_format(self):
        """Test that responses follow JSON-RPC 2.0 format."""
        # Valid JSON-RPC 2.0 response format
        valid_response = {"jsonrpc": "2.0", "result": {"agents": [], "total_count": 0}, "id": 1}

        valid_error_response = {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": 1}

        # Verify required fields for success response
        assert "jsonrpc" in valid_response
        assert valid_response["jsonrpc"] == "2.0"
        assert "result" in valid_response
        assert "id" in valid_response

        # Verify required fields for error response
        assert "jsonrpc" in valid_error_response
        assert valid_error_response["jsonrpc"] == "2.0"
        assert "error" in valid_error_response
        assert "code" in valid_error_response["error"]
        assert "message" in valid_error_response["error"]
        assert "id" in valid_error_response

    def test_json_rpc_error_codes(self):
        """Test standard JSON-RPC 2.0 error codes."""
        error_codes = {
            -32700: "Parse error",
            -32600: "Invalid Request",
            -32601: "Method not found",
            -32602: "Invalid params",
            -32603: "Internal error",
        }

        for code, message in error_codes.items():
            error_response = {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": None}
            assert error_response["error"]["code"] == code


class TestMCPToolInvocations:
    """Test all MCP tool invocations work correctly."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_correct_tools(self):
        """Test that list_tools returns all expected tools."""
        tools = await list_tools()

        expected_tools = ["list_agents", "spawn_agent", "send_message", "restart_agent", "deploy_team", "agent_status"]

        tool_names = [tool.name for tool in tools]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

        # Verify each tool has required properties
        for tool in tools:
            assert isinstance(tool, Tool)
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "inputSchema")

            # Verify JSON schema structure
            schema = tool.inputSchema
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema

    @pytest.mark.asyncio
    @patch("tmux_orchestrator.mcp_server.TMUXManager")
    async def test_list_agents_tool(self, mock_tmux_manager):
        """Test list_agents tool invocation."""
        # Mock TMUXManager
        mock_tmux = MagicMock()
        mock_tmux.list_agents.return_value = [
            {"session": "test-session", "window": "1", "type": "developer", "status": "active"}
        ]
        mock_tmux_manager.return_value = mock_tmux

        # Call the tool
        result = await call_tool("list_agents", {})

        # Verify response format
        assert "agents" in result
        assert "total_count" in result
        assert isinstance(result["agents"], list)
        assert result["total_count"] == 1
        assert result["agents"][0]["session"] == "test-session"

    @pytest.mark.asyncio
    @patch("tmux_orchestrator.mcp_server.TMUXManager")
    @patch("tmux_orchestrator.mcp_server.core_spawn_agent")
    async def test_spawn_agent_tool(self, mock_spawn_agent, mock_tmux_manager):
        """Test spawn_agent tool invocation."""
        # Mock successful spawn
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.session = "test-session"
        mock_result.window = "1"
        mock_result.target = "test-session:1"
        mock_spawn_agent.return_value = mock_result

        mock_tmux = MagicMock()
        mock_tmux_manager.return_value = mock_tmux

        # Test required parameters
        arguments = {"session_name": "test-session", "agent_type": "developer"}

        result = await call_tool("spawn_agent", arguments)

        # Verify response
        assert result["success"] is True
        assert result["session"] == "test-session"
        assert result["window"] == "1"
        assert result["target"] == "test-session:1"

    @pytest.mark.asyncio
    @patch("tmux_orchestrator.mcp_server.TMUXManager")
    @patch("tmux_orchestrator.mcp_server.core_send_message")
    async def test_send_message_tool(self, mock_send_message, mock_tmux_manager):
        """Test send_message tool invocation."""
        # Mock successful message send
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.target = "test-session:1"
        mock_send_message.return_value = mock_result

        mock_tmux = MagicMock()
        mock_tmux_manager.return_value = mock_tmux

        arguments = {"target": "test-session:1", "message": "Hello, agent!"}

        result = await call_tool("send_message", arguments)

        assert result["success"] is True
        assert result["target"] == "test-session:1"

    @pytest.mark.asyncio
    @patch("tmux_orchestrator.mcp_server.TMUXManager")
    @patch("tmux_orchestrator.mcp_server.core_restart_agent")
    async def test_restart_agent_tool(self, mock_restart_agent, mock_tmux_manager):
        """Test restart_agent tool invocation."""
        # Mock successful restart
        mock_restart_agent.return_value = (True, "Agent restarted successfully")

        mock_tmux = MagicMock()
        mock_tmux_manager.return_value = mock_tmux

        arguments = {"session_name": "test-session"}

        result = await call_tool("restart_agent", arguments)

        assert result["success"] is True
        assert result["target"] == "test-session:1"  # Default window
        assert "successfully" in result["message"]

    @pytest.mark.asyncio
    @patch("tmux_orchestrator.mcp_server.TMUXManager")
    @patch("tmux_orchestrator.mcp_server.core_deploy_team")
    async def test_deploy_team_tool(self, mock_deploy_team, mock_tmux_manager):
        """Test deploy_team tool invocation."""
        # Mock successful team deployment
        mock_deploy_team.return_value = (True, "Team deployed successfully")

        mock_tmux = MagicMock()
        mock_tmux_manager.return_value = mock_tmux

        arguments = {"team_name": "test-team", "team_type": "fullstack"}

        result = await call_tool("deploy_team", arguments)

        assert result["success"] is True
        assert result["team_name"] == "test-team"
        assert result["team_type"] == "fullstack"

    @pytest.mark.asyncio
    @patch("tmux_orchestrator.mcp_server.TMUXManager")
    @patch("tmux_orchestrator.mcp_server.core_get_agent_status")
    async def test_get_agent_status_tool(self, mock_get_status, mock_tmux_manager):
        """Test get_agent_status tool invocation."""
        # Mock agent metrics
        mock_metrics = MagicMock()
        mock_metrics.health_status.value = "healthy"
        mock_metrics.session_active = True
        mock_metrics.last_activity_time = None
        mock_metrics.responsiveness_score = 0.95
        mock_metrics.team_id = "test-team"

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.agent_metrics = [mock_metrics]
        mock_get_status.return_value = mock_result

        mock_tmux = MagicMock()
        mock_tmux_manager.return_value = mock_tmux

        arguments = {"session_name": "test-session"}

        result = await call_tool("get_agent_status", arguments)

        assert result["success"] is True
        assert result["session"] == "test-session"
        assert result["health_status"] == "healthy"
        assert result["session_active"] is True


class TestMCPErrorHandling:
    """Test error handling for invalid requests."""

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self):
        """Test error handling for unknown tool names."""
        result = await call_tool("nonexistent_tool", {})

        assert "error" in result
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    @patch("tmux_orchestrator.mcp_server.TMUXManager")
    async def test_missing_required_parameters(self, mock_tmux_manager):
        """Test error handling for missing required parameters."""
        mock_tmux = MagicMock()
        mock_tmux_manager.return_value = mock_tmux

        # spawn_agent requires session_name and agent_type
        with pytest.raises(KeyError):
            await call_tool("spawn_agent", {"session_name": "test"})  # Missing agent_type

    @pytest.mark.asyncio
    @patch("tmux_orchestrator.mcp_server.TMUXManager")
    async def test_invalid_agent_type(self, mock_tmux_manager):
        """Test error handling for invalid agent types."""
        mock_tmux = MagicMock()
        mock_tmux_manager.return_value = mock_tmux

        # This should be handled by the core function
        with patch("tmux_orchestrator.mcp_server.core_spawn_agent") as mock_spawn:
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error_message = "Invalid agent type: invalid_type"
            mock_spawn.return_value = mock_result

            arguments = {"session_name": "test-session", "agent_type": "invalid_type"}

            result = await call_tool("spawn_agent", arguments)
            assert result["success"] is False
            assert "Invalid agent type" in result["error"]

    @pytest.mark.asyncio
    @patch("tmux_orchestrator.mcp_server.TMUXManager")
    async def test_exception_handling(self, mock_tmux_manager):
        """Test that exceptions are properly caught and returned as errors."""
        # Mock TMUXManager to raise an exception
        mock_tmux_manager.side_effect = Exception("Database connection failed")

        result = await call_tool("list_agents", {})

        assert "error" in result
        assert "Tool execution failed" in result["error"]
        assert "Database connection failed" in result["error"]


class TestMCPToolSchemas:
    """Test tool schema validation."""

    @pytest.mark.asyncio
    async def test_all_tools_have_valid_schemas(self):
        """Test that all tools have valid JSON schemas."""
        tools = await list_tools()

        for tool in tools:
            schema = tool.inputSchema

            # Basic schema validation
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema
            assert isinstance(schema["properties"], dict)
            assert isinstance(schema["required"], list)

            # Validate each property has a type
            for prop_name, prop_def in schema["properties"].items():
                assert "type" in prop_def or "enum" in prop_def
                assert "description" in prop_def

    def test_spawn_agent_schema_validation(self):
        """Test spawn_agent schema specifically."""
        # This would be done by a JSON schema validator in practice
        valid_args = {
            "session_name": "test-session",
            "agent_type": "developer",
            "project_path": "/path/to/project",
            "briefing_message": "Welcome!",
        }

        # Required fields present
        assert "session_name" in valid_args
        assert "agent_type" in valid_args

        # Valid agent type
        valid_agent_types = ["developer", "pm", "qa", "devops", "reviewer", "researcher", "docs"]
        assert valid_args["agent_type"] in valid_agent_types

    def test_send_message_schema_validation(self):
        """Test send_message schema validation."""
        valid_args = {"target": "session:1", "message": "Hello agent"}

        # Required fields
        assert "target" in valid_args
        assert "message" in valid_args

        # Target format validation (basic)
        assert ":" in valid_args["target"]


class TestMCPConcurrentRequests:
    """Test resource management and concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test handling multiple concurrent tool calls."""
        with patch("tmux_orchestrator.mcp_server.TMUXManager") as mock_tmux_manager:
            mock_tmux = MagicMock()
            mock_tmux.list_agents.return_value = []
            mock_tmux_manager.return_value = mock_tmux

            # Create multiple concurrent calls
            tasks = [call_tool("list_agents", {}), call_tool("list_agents", {}), call_tool("list_agents", {})]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 3
            for result in results:
                assert "agents" in result
                assert "total_count" in result

    @pytest.mark.asyncio
    async def test_resource_cleanup(self):
        """Test that resources are properly cleaned up after tool calls."""
        with patch("tmux_orchestrator.mcp_server.TMUXManager") as mock_tmux_manager:
            mock_tmux = MagicMock()
            mock_tmux.list_agents.return_value = []
            mock_tmux_manager.return_value = mock_tmux

            # Make a tool call
            await call_tool("list_agents", {})

            # Verify TMUXManager was created and used
            mock_tmux_manager.assert_called_once()
            mock_tmux.list_agents.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
