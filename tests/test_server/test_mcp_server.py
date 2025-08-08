"""Tests for MCP server functionality."""

import json
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict

import pytest
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool, ToolCall

from tmux_orchestrator.server.mcp import create_server


@pytest.fixture
def mock_tmux():
    """Create mock TMUXManager."""
    with patch('tmux_orchestrator.utils.tmux.TMUXManager') as mock:
        instance = Mock()
        mock.return_value = instance
        yield instance


@pytest.fixture
async def mcp_server(mock_tmux):
    """Create MCP server instance."""
    server = create_server()
    # Initialize the server (normally done by stdio_server)
    await server.__aenter__()
    yield server
    await server.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_server_creation():
    """Test that server can be created."""
    server = create_server()
    assert isinstance(server, Server)
    assert server.name == "tmux-orchestrator"


@pytest.mark.asyncio
async def test_list_tools(mcp_server):
    """Test listing available tools."""
    tools = await mcp_server.list_tools()
    
    # Verify we have tools
    assert len(tools) > 0
    
    # Check for expected tools
    tool_names = [tool.name for tool in tools]
    expected_tools = [
        'list_sessions',
        'list_agents', 
        'spawn_agent',
        'restart_agent',
        'send_message',
        'check_health',
        'team_status',
        'team_broadcast'
    ]
    
    for expected in expected_tools:
        assert expected in tool_names
    
    # Verify tool structure
    for tool in tools:
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'inputSchema')


@pytest.mark.asyncio
async def test_list_sessions_tool(mcp_server, mock_tmux):
    """Test list_sessions tool."""
    # Mock tmux response
    mock_tmux.list_sessions.return_value = [
        {'name': 'project1', 'windows': 3, 'created': '2024-01-01'},
        {'name': 'project2', 'windows': 5, 'created': '2024-01-02'}
    ]
    
    # Create tool call
    tool_call = ToolCall(
        name="list_sessions",
        arguments={}
    )
    
    # Execute tool
    result = await mcp_server.call_tool(tool_call)
    
    # Verify result
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert 'project1' in result[0].text
    assert 'project2' in result[0].text


@pytest.mark.asyncio
async def test_spawn_agent_tool(mcp_server, mock_tmux):
    """Test spawn_agent tool."""
    # Mock agent manager
    with patch('tmux_orchestrator.core.agent_manager.AgentManager') as mock_mgr_class:
        mock_mgr = Mock()
        mock_mgr.deploy_agent.return_value = "project-123:2"
        mock_mgr_class.return_value = mock_mgr
        
        # Create tool call
        tool_call = ToolCall(
            name="spawn_agent",
            arguments={
                "session_name": "project-123",
                "role": "developer"
            }
        )
        
        # Execute tool
        result = await mcp_server.call_tool(tool_call)
        
        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "project-123:2" in result[0].text
        mock_mgr.deploy_agent.assert_called_once_with("project-123", "developer")


@pytest.mark.asyncio
async def test_send_message_tool(mcp_server, mock_tmux):
    """Test send_message tool."""
    # Mock tmux send
    mock_tmux.send_message.return_value = True
    
    # Create tool call
    tool_call = ToolCall(
        name="send_message",
        arguments={
            "target": "project:0",
            "message": "Hello, agent!"
        }
    )
    
    # Execute tool
    result = await mcp_server.call_tool(tool_call)
    
    # Verify result
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "success" in result[0].text.lower()
    mock_tmux.send_message.assert_called_once_with("project:0", "Hello, agent!")


@pytest.mark.asyncio
async def test_check_health_tool(mcp_server, mock_tmux):
    """Test check_health tool."""
    with patch('tmux_orchestrator.core.recovery.check_agent_health') as mock_health:
        mock_health.return_value = {
            'healthy': True,
            'last_activity': '5 minutes ago',
            'status': 'active'
        }
        
        # Create tool call
        tool_call = ToolCall(
            name="check_health",
            arguments={
                "target": "project:1"
            }
        )
        
        # Execute tool
        result = await mcp_server.call_tool(tool_call)
        
        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "healthy" in result[0].text.lower()
        assert "5 minutes ago" in result[0].text


@pytest.mark.asyncio
async def test_team_status_tool(mcp_server, mock_tmux):
    """Test team_status tool."""
    with patch('tmux_orchestrator.core.team_operations.get_team_status') as mock_status:
        mock_status.return_value = {
            'session': 'project1',
            'total_agents': 5,
            'active': 4,
            'idle': 1,
            'health': 'good'
        }
        
        # Create tool call
        tool_call = ToolCall(
            name="team_status",
            arguments={
                "session_name": "project1"
            }
        )
        
        # Execute tool
        result = await mcp_server.call_tool(tool_call)
        
        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert data['total_agents'] == 5
        assert data['health'] == 'good'


@pytest.mark.asyncio
async def test_team_broadcast_tool(mcp_server, mock_tmux):
    """Test team_broadcast tool."""
    with patch('tmux_orchestrator.core.team_operations.broadcast_to_team') as mock_broadcast:
        mock_broadcast.return_value = {
            'sent': 5,
            'failed': 0,
            'targets': ['project:0', 'project:1', 'project:2', 'project:3', 'project:4']
        }
        
        # Create tool call
        tool_call = ToolCall(
            name="team_broadcast",
            arguments={
                "session_name": "project",
                "message": "Team meeting at 3pm"
            }
        )
        
        # Execute tool
        result = await mcp_server.call_tool(tool_call)
        
        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "sent: 5" in result[0].text.lower() or "5 agents" in result[0].text.lower()


@pytest.mark.asyncio
async def test_restart_agent_tool(mcp_server, mock_tmux):
    """Test restart_agent tool."""
    with patch('tmux_orchestrator.core.agent_operations.restart_agent') as mock_restart:
        mock_restart.return_value = (True, "Agent restarted successfully")
        
        # Create tool call
        tool_call = ToolCall(
            name="restart_agent",
            arguments={
                "target": "project:2"
            }
        )
        
        # Execute tool
        result = await mcp_server.call_tool(tool_call)
        
        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "success" in result[0].text.lower()
        mock_restart.assert_called_once()


@pytest.mark.asyncio
async def test_list_agents_tool(mcp_server, mock_tmux):
    """Test list_agents tool."""
    with patch('tmux_orchestrator.core.recovery.discover_agents') as mock_discover:
        mock_discover.return_value = [
            {'target': 'project:0', 'session': 'project', 'window': '0', 'role': 'orchestrator'},
            {'target': 'project:1', 'session': 'project', 'window': '1', 'role': 'pm'},
            {'target': 'project:2', 'session': 'project', 'window': '2', 'role': 'developer'}
        ]
        
        # Create tool call
        tool_call = ToolCall(
            name="list_agents",
            arguments={}
        )
        
        # Execute tool
        result = await mcp_server.call_tool(tool_call)
        
        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        agents = json.loads(result[0].text)
        assert len(agents) == 3
        assert agents[0]['role'] == 'orchestrator'


@pytest.mark.asyncio
async def test_invalid_tool_call(mcp_server):
    """Test calling non-existent tool."""
    tool_call = ToolCall(
        name="invalid_tool",
        arguments={}
    )
    
    with pytest.raises(Exception) as excinfo:
        await mcp_server.call_tool(tool_call)
    
    assert "Unknown tool" in str(excinfo.value) or "not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_tool_with_invalid_arguments(mcp_server, mock_tmux):
    """Test tool with missing required arguments."""
    # Missing 'message' argument
    tool_call = ToolCall(
        name="send_message",
        arguments={
            "target": "project:0"
            # Missing 'message'
        }
    )
    
    with pytest.raises(Exception) as excinfo:
        await mcp_server.call_tool(tool_call)
    
    # Should raise validation error
    assert "message" in str(excinfo.value).lower() or "required" in str(excinfo.value).lower()