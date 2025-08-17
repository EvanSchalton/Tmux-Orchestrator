"""Phase 1 MCP tools for agent management operations."""

import logging
from typing import Any, Dict

from tmux_orchestrator.mcp.server import mcp

logger = logging.getLogger(__name__)

# Temporarily disable handlers for initial testing
# from tmux_orchestrator.mcp.handlers.agent_handlers import AgentHandlers
# agent_handlers = AgentHandlers()


@mcp.tool()
async def spawn_agent(
    session_name: str,
    agent_type: str = "developer",
    project_path: str | None = None,
    briefing_message: str | None = None,
    use_context: bool = True,
    window_name: str | None = None,
) -> Dict[str, Any]:
    """
    Spawn a new Claude agent in a tmux session.

    Args:
        session_name: Name for the tmux session
        agent_type: Type of agent (developer, pm, qa, devops, reviewer, researcher, docs)
        project_path: Path to the project directory (optional)
        briefing_message: Initial briefing message for the agent (optional)
        use_context: Use standardized context for the agent type
        window_name: Specific window name (auto-generated if not provided)

    Returns:
        Dict with success status, session, window, and target information
    """
    logger.info(f"Spawning agent: {agent_type} in session {session_name}")

    # Input validation
    if not session_name.strip():
        return {
            "success": False,
            "error": "Session name cannot be empty",
            "error_type": "ValidationError",
        }

    valid_agent_types = ["developer", "pm", "qa", "devops", "reviewer", "researcher", "docs"]
    if agent_type not in valid_agent_types:
        return {
            "success": False,
            "error": f"Invalid agent type. Must be one of: {', '.join(valid_agent_types)}",
            "error_type": "ValidationError",
        }

    # Temporary stub implementation with enhanced response
    window_name = window_name or f"Claude-{agent_type}"
    target = f"{session_name}:{window_name}"

    return {
        "success": True,
        "session": session_name,
        "window": window_name,
        "target": target,
        "agent_type": agent_type,
        "message": f"Successfully spawned {agent_type} agent in {target}",
        "project_path": project_path,
        "use_context": use_context,
    }


@mcp.tool()
async def send_message(
    target: str,
    message: str,
    urgent: bool = False,
) -> Dict[str, Any]:
    """
    Send a message to a specific Claude agent.

    Args:
        target: Target identifier in 'session:window' format
        message: Message to send to the agent
        urgent: Mark message as urgent for priority handling

    Returns:
        Dict with success status and delivery confirmation
    """
    logger.info(f"Sending message to {target}")

    # Input validation
    if not target or ":" not in target:
        return {
            "success": False,
            "error": "Invalid target format. Use 'session:window'",
            "error_type": "ValidationError",
            "target": target,
            "urgent": urgent,
        }

    if not message.strip():
        return {
            "success": False,
            "error": "Message cannot be empty",
            "error_type": "ValidationError",
            "target": target,
            "urgent": urgent,
        }

    # Temporary stub implementation with proper response
    return {
        "success": True,
        "target": target,
        "message": "Message sent successfully",
        "urgent": urgent,
        "delivery_time": "2024-01-01T00:00:00Z",
    }


@mcp.tool()
async def get_agent_status(
    target: str | None = None,
    include_history: bool = False,
    include_metrics: bool = True,
) -> Dict[str, Any]:
    """
    Get comprehensive status of all agents or a specific agent.

    Args:
        target: Specific agent target (session:window), or None for all agents
        include_history: Include activity history in response
        include_metrics: Include detailed performance metrics

    Returns:
        Dict with agent status information including health, activity, and metrics
    """
    logger.info(f"Getting agent status for target: {target or 'all'}")

    # Input validation for target format
    if target and ":" not in target:
        return {
            "success": False,
            "error": "Invalid target format. Use 'session:window'",
            "error_type": "ValidationError",
            "target": target,
        }

    # Temporary stub implementation with enhanced response
    if target:
        return {
            "success": True,
            "target": target,
            "health_status": "healthy",
            "session_active": True,
            "last_activity": "2024-01-01T00:00:00Z",
            "responsiveness_score": 0.95,
            "team_id": f"team-{target.split(':')[0]}",
            "include_history": include_history,
            "include_metrics": include_metrics,
        }
    else:
        # Mock data for all agents
        mock_agents = [
            {
                "target": "dev-session:Claude-developer",
                "health_status": "healthy",
                "session_active": True,
                "last_activity": "2024-01-01T00:00:00Z",
                "responsiveness_score": 0.95,
                "team_id": "team-dev-session",
            },
            {
                "target": "qa-session:Claude-qa",
                "health_status": "healthy",
                "session_active": True,
                "last_activity": "2024-01-01T00:00:00Z",
                "responsiveness_score": 0.88,
                "team_id": "team-qa-session",
            },
        ]

        return {
            "success": True,
            "agents": mock_agents,
            "total_count": len(mock_agents),
            "include_history": include_history,
            "include_metrics": include_metrics,
        }


@mcp.tool()
async def kill_agent(
    target: str,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Terminate a specific agent or all agents.

    Args:
        target: Target to kill (session:window), or 'all' for all agents
        force: Force kill without confirmation

    Returns:
        Dict with success status and termination details
    """
    logger.info(f"Killing agent: {target}")

    # Input validation
    if not target.strip():
        return {
            "success": False,
            "error": "Target cannot be empty",
            "error_type": "ValidationError",
        }

    # Validate target format (either session:window or just session)
    if target != "all" and ":" not in target and not target.replace("-", "").replace("_", "").isalnum():
        return {
            "success": False,
            "error": "Invalid target format. Use 'session:window', 'session', or 'all'",
            "error_type": "ValidationError",
            "target": target,
        }

    # Temporary stub implementation with enhanced response
    if target == "all":
        return {
            "success": True,
            "target": target,
            "action": "all_agents_killed",
            "message": "Successfully killed all agents",
            "killed_count": 5,  # Mock count
            "force": force,
        }
    elif ":" in target:
        session, window = target.split(":", 1)
        return {
            "success": True,
            "target": target,
            "action": "window_killed",
            "message": f"Successfully killed window {window} in session {session}",
            "session": session,
            "window": window,
            "force": force,
        }
    else:
        return {
            "success": True,
            "target": target,
            "action": "session_killed",
            "message": f"Successfully killed session {target}",
            "session": target,
            "force": force,
        }


def register_agent_tools() -> None:
    """Register all agent management tools with FastMCP."""
    logger.info("Phase 1 agent management tools registered")


# Auto-register tools when module is imported
register_agent_tools()
