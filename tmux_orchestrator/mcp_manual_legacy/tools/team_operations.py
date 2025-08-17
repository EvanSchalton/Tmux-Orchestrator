"""Phase 2 MCP tools for team operations and coordination."""

import logging
from typing import Any, Dict, List

from tmux_orchestrator.mcp.handlers.team_handlers import TeamHandlers
from tmux_orchestrator.mcp.server import mcp

logger = logging.getLogger(__name__)

# Initialize handlers
team_handlers = TeamHandlers()


@mcp.tool()
async def deploy_team(
    team_name: str,
    team_type: str,
    size: int = 3,
    project_path: str | None = None,
    briefing_context: str | None = None,
) -> Dict[str, Any]:
    """
    Deploy a team of specialized Claude agents.

    Args:
        team_name: Name for the team/session
        team_type: Type of team (frontend, backend, fullstack, testing)
        size: Number of agents in the team (2-6 recommended)
        project_path: Path to project directory
        briefing_context: Additional context for the team

    Returns:
        Dict with deployment status, agent details, and team configuration
    """
    logger.info(f"Deploying {team_type} team '{team_name}' with {size} agents")

    # Input validation
    valid_team_types = ["frontend", "backend", "fullstack", "testing"]
    if team_type not in valid_team_types:
        return {
            "success": False,
            "error": f"Invalid team type. Must be one of: {', '.join(valid_team_types)}",
            "error_type": "ValidationError",
            "team_name": team_name,
        }

    if not 2 <= size <= 10:
        return {
            "success": False,
            "error": "Team size must be between 2 and 10",
            "error_type": "ValidationError",
            "team_name": team_name,
        }

    if not team_name.strip():
        return {
            "success": False,
            "error": "Team name cannot be empty",
            "error_type": "ValidationError",
        }

    return await team_handlers.deploy_team(
        team_name=team_name,
        team_type=team_type,
        size=size,
        project_path=project_path,
        briefing_context=briefing_context,
    )


@mcp.tool()
async def get_team_status(
    session: str | None = None,
    detailed: bool = False,
    include_agents: bool = True,
) -> Dict[str, Any]:
    """
    Get comprehensive status of a team or all teams.

    Args:
        session: Specific team session, or None for all teams
        detailed: Include detailed agent metrics
        include_agents: Include individual agent status

    Returns:
        Dict with team health, agent status, and performance metrics
    """
    logger.info(f"Getting team status for session: {session or 'all'}")

    return await team_handlers.get_team_status(
        session=session,
        detailed=detailed,
        include_agents=include_agents,
    )


@mcp.tool()
async def team_broadcast(
    session: str,
    message: str,
    exclude_windows: List[str] | None = None,
    urgent: bool = False,
) -> Dict[str, Any]:
    """
    Broadcast a message to all agents in a team.

    Args:
        session: Team session to broadcast to
        message: Message to broadcast
        exclude_windows: Window names to exclude from broadcast
        urgent: Mark message as urgent

    Returns:
        Dict with broadcast results and delivery confirmations
    """
    logger.info(f"Broadcasting to team {session}: {message[:50]}...")

    # Input validation
    if not session.strip():
        return {
            "success": False,
            "error": "Session name cannot be empty",
            "error_type": "ValidationError",
        }

    if not message.strip():
        return {
            "success": False,
            "error": "Message cannot be empty",
            "error_type": "ValidationError",
            "session": session,
        }

    return await team_handlers.team_broadcast(
        session=session,
        message=message,
        exclude_windows=exclude_windows or [],
        urgent=urgent,
    )


def register_team_tools() -> None:
    """Register all team operation tools with FastMCP."""
    logger.info("Phase 2 team operation tools registered")


# Auto-register tools when module is imported
register_team_tools()
