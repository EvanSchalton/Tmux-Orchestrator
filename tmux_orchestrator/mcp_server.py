"""MCP (Model Context Protocol) server implementation for tmux-orchestrator.

This server provides a stdio-based MCP interface that Claude Code can use directly
to interact with the tmux orchestrator system.
"""

import asyncio
import logging
from typing import Any

from mcp import Tool
from mcp.server import Server
from mcp.server.stdio import stdio_server

from tmux_orchestrator.core.agent_operations.restart_agent import restart_agent as core_restart_agent
from tmux_orchestrator.core.team_operations.deploy_team import deploy_standard_team as core_deploy_team
from tmux_orchestrator.server.tools.get_agent_status import (
    AgentStatusRequest,
)
from tmux_orchestrator.server.tools.get_agent_status import (
    get_agent_status as core_get_agent_status,
)
from tmux_orchestrator.server.tools.send_message import (
    SendMessageRequest,
)
from tmux_orchestrator.server.tools.send_message import (
    send_message as core_send_message,
)
from tmux_orchestrator.server.tools.spawn_agent import (
    SpawnAgentRequest,
)
from tmux_orchestrator.server.tools.spawn_agent import (
    spawn_agent as core_spawn_agent,
)
from tmux_orchestrator.utils.tmux import TMUXManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Create server instance
mcp_server = Server("tmux-orchestrator")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="list_agents",
            description="List all active tmux sessions and their Claude agents",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="spawn_agent",
            description="Spawn a new Claude agent in a tmux session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {"type": "string", "description": "Name for the tmux session"},
                    "agent_type": {
                        "type": "string",
                        "description": "Type of agent (developer, pm, qa, devops, reviewer, researcher, docs)",
                        "enum": ["developer", "pm", "qa", "devops", "reviewer", "researcher", "docs"],
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project directory (optional)",
                    },
                    "briefing_message": {
                        "type": "string",
                        "description": "Initial briefing message for the agent (optional)",
                    },
                },
                "required": ["session_name", "agent_type"],
            },
        ),
        Tool(
            name="send_message",
            description="Send a message to a specific Claude agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target identifier (session:window format)",
                    },
                    "message": {"type": "string", "description": "Message to send"},
                },
                "required": ["target", "message"],
            },
        ),
        Tool(
            name="restart_agent",
            description="Restart a Claude agent in its tmux session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {"type": "string", "description": "Name of the tmux session"},
                    "window_name": {
                        "type": "string",
                        "description": "Name of the tmux window (optional)",
                    },
                },
                "required": ["session_name"],
            },
        ),
        Tool(
            name="deploy_team",
            description="Deploy a team of specialized Claude agents",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_name": {"type": "string", "description": "Name for the team"},
                    "team_type": {
                        "type": "string",
                        "description": "Type of team (frontend, backend, fullstack, testing)",
                        "enum": ["frontend", "backend", "fullstack", "testing"],
                    },
                },
                "required": ["team_name", "team_type"],
            },
        ),
        Tool(
            name="get_agent_status",
            description="Get detailed status of a specific Claude agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {"type": "string", "description": "Name of the tmux session"},
                    "window_name": {
                        "type": "string",
                        "description": "Name of the tmux window (optional)",
                    },
                },
                "required": ["session_name"],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Handle tool calls from the MCP client."""
    logger.info(f"Tool called: {name} with arguments: {arguments}")

    try:
        tmux = TMUXManager()

        if name == "list_agents":
            # List all active agents
            agents = tmux.list_agents()
            return {
                "agents": [
                    {
                        "session": agent["session"],
                        "window": agent.get("window", "0"),
                        "type": agent.get("type", "unknown"),
                        "status": agent.get("status", "unknown"),
                    }
                    for agent in agents
                ],
                "total_count": len(agents),
            }

        elif name == "spawn_agent":
            # Spawn a new agent
            request = SpawnAgentRequest(
                session_name=arguments["session_name"],
                agent_type=arguments["agent_type"],
                project_path=arguments.get("project_path"),
                briefing_message=arguments.get("briefing_message"),
            )
            result = core_spawn_agent(tmux, request)

            if result.success:
                # If briefing message provided, send it after spawning
                if request.briefing_message:
                    msg_request = SendMessageRequest(
                        target=result.target,
                        message=request.briefing_message,
                    )
                    core_send_message(tmux, msg_request)

                return {
                    "success": True,
                    "session": result.session,
                    "window": result.window,
                    "target": result.target,
                    "message": f"Successfully spawned {request.agent_type} agent in {result.target}",
                }
            else:
                return {"success": False, "error": result.error_message or "Failed to spawn agent"}

        elif name == "send_message":
            # Send a message to an agent
            send_request = SendMessageRequest(
                target=arguments["target"],
                message=arguments["message"],
            )
            send_result = core_send_message(tmux, send_request)

            return {
                "success": send_result.success,
                "target": send_result.target,
                "message": "Message sent successfully" if send_result.success else send_result.error_message,
            }

        elif name == "restart_agent":
            # Restart an agent
            session_name = arguments["session_name"]
            window_name = arguments.get("window_name", "1")
            target = f"{session_name}:{window_name}"

            success, message = core_restart_agent(tmux, target)

            return {
                "success": success,
                "target": target,
                "message": message,
            }

        elif name == "deploy_team":
            # Deploy a team of agents
            success, message = core_deploy_team(
                tmux=tmux,
                team_type=arguments["team_type"],
                size=3,  # Default size
                project_name=arguments["team_name"],
            )

            return {
                "success": success,
                "team_name": arguments["team_name"],
                "team_type": arguments["team_type"],
                "message": message,
            }

        elif name == "get_agent_status":
            # Get agent status
            session_name = arguments["session_name"]
            window_name = arguments.get("window_name", "1")
            agent_id = f"{session_name}:{window_name}"

            status_request = AgentStatusRequest(
                agent_id=agent_id,
                include_activity_history=True,
                activity_limit=5,
            )
            status_result = core_get_agent_status(tmux, status_request)

            if status_result.success and status_result.agent_metrics:
                metrics = status_result.agent_metrics[0]
                return {
                    "success": True,
                    "session": session_name,
                    "window": window_name,
                    "health_status": metrics.health_status.value,
                    "session_active": metrics.session_active,
                    "last_activity": metrics.last_activity_time.isoformat() if metrics.last_activity_time else None,
                    "responsiveness_score": metrics.responsiveness_score,
                    "team_id": metrics.team_id,
                }
            else:
                return {
                    "success": False,
                    "error": status_result.error_message or "Agent not found",
                }

        else:
            return {"error": f"Unknown tool: {name}"}

    except Exception as e:
        logger.error(f"Error executing tool {name}: {str(e)}")
        return {"error": f"Tool execution failed: {str(e)}"}


async def main():
    """Run the MCP server using stdio transport."""
    logger.info("Starting tmux-orchestrator MCP server...")

    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
