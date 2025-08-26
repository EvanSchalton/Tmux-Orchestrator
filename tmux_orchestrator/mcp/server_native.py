#!/usr/bin/env python3
"""
Native MCP Server for Tmux Orchestrator

Simplified FastMCP implementation using native tools with type hints.
The parameter schemas are enforced through Python type hints and validation.
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import native MCP tools
try:
    from ..mcp_tools import (
        # Core tools for primary functionality
        agent_list,
        agent_send_message,
        agent_status,
        health_check,
        list_contexts,
        show_context,
        spawn_agent,
        spawn_pm,
        system_status,
        team_broadcast,
        team_status,
    )

    logger.info("✅ Successfully imported native MCP tools")
except ImportError as e:
    logger.error(f"❌ Failed to import native MCP tools: {e}")
    sys.exit(1)

# Create FastMCP application
app = FastMCP("tmux-orchestrator-native")

# =============================================================================
# CORE MCP TOOLS - Native Implementation
# =============================================================================


@app.tool()
async def list_agents(
    format: str = "table", filter_session: Optional[str] = None, include_idle: bool = True
) -> Dict[str, Any]:
    """List all active agents across sessions with filtering options."""
    return await agent_list(format, filter_session, include_idle)


@app.tool()
async def get_agent_status(target: str, include_metrics: bool = False) -> Dict[str, Any]:
    """Get detailed status of a specific agent (session:window format)."""
    return await agent_status(target, include_metrics)


@app.tool()
async def send_agent_message(
    target: str, message: str, priority: str = "normal", expect_response: bool = False
) -> Dict[str, Any]:
    """Send message to a specific agent with priority levels."""
    return await agent_send_message(target, message, priority, expect_response)


@app.tool()
async def create_agent(
    role: str,
    session_name: str,
    briefing: str,
    window: Optional[int] = None,
    technology_stack: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Spawn a new agent with specified role and context."""
    return await spawn_agent(role, session_name, briefing, window, technology_stack)


@app.tool()
async def create_project_manager(
    session_name: str, window: int = 1, project_context: Optional[str] = None, team_size: Optional[int] = None
) -> Dict[str, Any]:
    """Spawn a project manager agent."""
    return await spawn_pm(session_name, window, project_context, team_size)


@app.tool()
async def broadcast_to_team(
    team_name: str, message: str, priority: str = "normal", exclude_roles: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Broadcast message to all team members."""
    return await team_broadcast(team_name, message, priority, exclude_roles)


@app.tool()
async def get_team_status(
    team_name: Optional[str] = None, include_agents: bool = True, format: str = "table"
) -> Dict[str, Any]:
    """Get status of team or all teams."""
    return await team_status(team_name, include_agents, format)


@app.tool()
async def get_system_status(format: str = "dashboard", include_performance: bool = False) -> Dict[str, Any]:
    """Get comprehensive system status."""
    return await system_status(format, include_performance)


@app.tool()
async def run_health_check(
    target: Optional[str] = None, deep_check: bool = False, auto_fix: bool = False
) -> Dict[str, Any]:
    """Perform comprehensive health check."""
    return await health_check(target, deep_check, auto_fix)


@app.tool()
async def get_context(context_name: str) -> Dict[str, Any]:
    """Show context information (orc, pm, mcp, tmux-comms)."""
    return await show_context(context_name)


@app.tool()
async def get_contexts() -> Dict[str, Any]:
    """List all available contexts."""
    return await list_contexts()


# =============================================================================
# SERVER MANAGEMENT
# =============================================================================


async def main():
    """Run the native MCP tools server."""
    logger.info("🚀 Starting Native MCP Tools Server...")

    # Get tool count and names from tool manager
    tools = app._tool_manager.list_tools()
    tool_count = len(tools)
    logger.info(f"📊 Registered {tool_count} native MCP tools:")

    for tool_name in sorted([tool.name for tool in tools]):
        logger.info(f"  • {tool_name}")

    logger.info("📈 Native implementation advantages:")
    logger.info("  • No kwargs string parsing overhead")
    logger.info("  • Type-safe parameter validation")
    logger.info("  • Consistent error handling")
    logger.info("  • API Designer coordinated schemas")

    logger.info("🌐 Starting MCP protocol server...")
    await app.run_stdio_async()


def sync_main():
    """Synchronous entry point for CLI integration."""
    asyncio.run(main())


if __name__ == "__main__":
    sync_main()
