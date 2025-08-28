"""
Native MCP Tools FastMCP Server Integration

This module demonstrates how to integrate the native MCP tools with FastMCP,
using the API Designer's exact parameter schemas for each tool.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

# Import all native tools
from . import (
    agent_list,
    agent_send_message,
    agent_status,
    health_check,
    list_contexts,
    show_context,
    # Spawning & Deployment
    spawn_agent,
    spawn_pm,
    # Monitoring & Health
    system_status,
    team_broadcast,
    team_status,
)

logger = logging.getLogger(__name__)

# Create FastMCP app
app = FastMCP("tmux-orchestrator-native")

# =============================================================================
# AGENT MANAGEMENT TOOLS (6 tools)
# =============================================================================


@app.tool()
async def list_agents(
    format: str = "table", filter_session: Optional[str] = None, include_idle: bool = True
) -> Dict[str, Any]:
    """List all active agents with filtering options."""
    return await agent_list(format, filter_session, include_idle)


@app.tool(description="Get detailed status of a specific agent with optional metrics")
async def get_agent_status(target: str, include_metrics: bool = False) -> Dict[str, Any]:
    """Get detailed status of a specific agent."""
    return await agent_status(target, include_metrics)


@app.tool()
async def send_agent_message(
    target: str, message: str, priority: str = "normal", expect_response: bool = False
) -> Dict[str, Any]:
    """Send message to a specific agent."""
    return await agent_send_message(target, message, priority, expect_response)


# =============================================================================
# SPAWNING & DEPLOYMENT TOOLS (4 tools)
# =============================================================================


@app.tool(description="Spawn a new agent with role, briefing, and technology focus")
async def create_agent(
    role: str,
    session_name: str,
    briefing: str,
    window: Optional[int] = None,
    technology_stack: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Spawn a new agent with specified role and context."""
    return await spawn_agent(role, session_name, briefing, window, technology_stack)


@app.tool(description="Spawn a project manager with team awareness")
async def create_project_manager(
    session_name: str, window: int = 1, project_context: Optional[str] = None, team_size: Optional[int] = None
) -> Dict[str, Any]:
    """Spawn a project manager agent."""
    return await spawn_pm(session_name, window, project_context, team_size)


# =============================================================================
# TEAM COORDINATION TOOLS (4 tools)
# =============================================================================


@app.tool(description="Get status of team or all teams with agent details")
async def get_team_status(
    team_name: Optional[str] = None, include_agents: bool = True, format: str = "table"
) -> Dict[str, Any]:
    """Get team status information."""
    return await team_status(team_name, include_agents, format)


@app.tool()
async def broadcast_to_team(
    team_name: str, message: str, priority: str = "normal", exclude_roles: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Broadcast message to team members."""
    return await team_broadcast(team_name, message, priority, exclude_roles)


# =============================================================================
# MONITORING & HEALTH TOOLS (3 tools)
# =============================================================================


@app.tool()
async def get_system_status(format: str = "dashboard", include_performance: bool = False) -> Dict[str, Any]:
    """Get comprehensive system status."""
    return await system_status(format, include_performance)


@app.tool()
async def run_health_check(
    target: Optional[str] = None, deep_check: bool = False, auto_fix: bool = False
) -> Dict[str, Any]:
    """Perform system health check."""
    return await health_check(target, deep_check, auto_fix)


# =============================================================================
# CONTEXT MANAGEMENT TOOLS (2 primary tools)
# =============================================================================


@app.tool()
async def get_context(context_name: str) -> Dict[str, Any]:
    """Show context information."""
    return await show_context(context_name)


@app.tool()
async def get_contexts() -> Dict[str, Any]:
    """List all available contexts."""
    return await list_contexts()


# =============================================================================
# SERVER ENTRY POINT
# =============================================================================


async def main():
    """Run the native MCP tools server."""
    logger.info("Starting Native MCP Tools Server...")
    logger.info(f"Registered {len(app.tools)} native tools")

    # List all registered tools for debugging
    for tool_name in sorted(app.tools.keys()):
        logger.info(f"  • {tool_name}")

    # Run the server
    await app.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
