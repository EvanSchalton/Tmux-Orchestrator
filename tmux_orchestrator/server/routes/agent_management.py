"""Agent lifecycle management routes for MCP server."""

import asyncio
from datetime import datetime, timezone
from typing import Union

from fastapi import APIRouter, BackgroundTasks, HTTPException

# Import comprehensive Pydantic models
from tmux_orchestrator.server.models.agent_models import (
    AgentRestartRequest,
    AgentSpawnRequest,
    AgentSpawnResponse,
    AgentStatusRequest,
    AgentStatusResponse,
)
from tmux_orchestrator.server.tools.get_session_status import (
    AgentStatusRequest as ToolAgentStatusRequest,
)
from tmux_orchestrator.server.tools.get_session_status import (
    get_agent_status,
)
from tmux_orchestrator.server.tools.kill_agent import (
    KillAgentRequest as ToolKillRequest,
)
from tmux_orchestrator.server.tools.kill_agent import (
    kill_agent,
)
from tmux_orchestrator.server.tools.restart_agent import (
    RestartAgentRequest as ToolRestartRequest,
)
from tmux_orchestrator.server.tools.restart_agent import (
    restart_agent,
)
from tmux_orchestrator.server.tools.spawn_agent import (
    SpawnAgentRequest as ToolSpawnRequest,
)
from tmux_orchestrator.server.tools.spawn_agent import (
    spawn_agent,
)
from tmux_orchestrator.utils.tmux import TMUXManager

router = APIRouter()
tmux = TMUXManager()


@router.post("/spawn", response_model=AgentSpawnResponse)
async def spawn_agent_tool(request: AgentSpawnRequest, background_tasks: BackgroundTasks) -> AgentSpawnResponse:
    """MCP Tool: Spawn a new Claude agent in a tmux session.

    This is the primary MCP tool for creating new AI agents in the orchestration system.
    Agents are spawned in dedicated tmux windows with proper initialization.
    """
    # Convert API request to business logic request
    tool_request = ToolSpawnRequest(
        session_name=request.session_name,
        agent_type=request.agent_type,
        project_path=request.project_path,
        briefing_message=request.briefing_message,
    )

    # Execute business logic
    result = spawn_agent(tmux, tool_request)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message)

    # Schedule briefing if provided
    if request.briefing_message:
        background_tasks.add_task(_delayed_briefing, result.target, request.briefing_message)

    return AgentSpawnResponse(
        success=result.success,
        session=result.session,
        window=result.window,
        target=result.target,
        agent_type=request.agent_type,
        created_at=datetime.now(timezone.utc).isoformat(),
        error_message=None,
    )


@router.post("/restart")
async def restart_agent_tool(
    request: AgentRestartRequest,
) -> dict[str, Union[str, bool]]:
    """MCP Tool: Restart a failed or stuck agent.

    This tool handles agent recovery by safely restarting Claude processes
    while preserving the session context.
    """
    # Parse target into session and window
    if ":" not in request.target:
        raise HTTPException(status_code=400, detail="Target must be in format 'session:window'")

    session, window = request.target.split(":", 1)

    tool_request = ToolRestartRequest(
        session=session,
        window=window,
        clear_terminal=True,  # Default to clearing terminal
        restart_delay_seconds=2,  # Default delay
    )

    result = await restart_agent(tmux, tool_request)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message)

    return {
        "success": True,
        "target": result.target,
        "message": f"Agent {result.target} restarted successfully",
    }


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status_tool(request: AgentStatusRequest) -> AgentStatusResponse:
    """MCP Tool: Get detailed status of a specific agent.

    This tool provides comprehensive status information about an agent
    including activity state and recent output.
    """
    # Parse target into session and window
    if ":" not in request.target:
        raise HTTPException(status_code=400, detail="Target must be in format 'session:window'")

    session, window = request.target.split(":", 1)

    tool_request = ToolAgentStatusRequest(
        session=session, window=window, lines=request.activity_lines if request.include_activity else 0
    )

    result = get_agent_status(tmux, tool_request)

    if result.error_message:
        raise HTTPException(
            status_code=404 if result.status == "not_found" else 500,
            detail=result.error_message,
        )

    # Convert result to proper response format
    activity_lines = []
    if result.recent_output:
        # recent_output is already a list[str]
        activity_lines = result.recent_output[-10:]

    return AgentStatusResponse(
        target=result.target,
        status=result.status,
        responsive=result.status == "active",
        last_activity=datetime.now(timezone.utc).isoformat(),
        uptime_minutes=0,  # TODO: Calculate actual uptime
        activity_summary=activity_lines,
        health_score=100 if result.status == "active" else 50,
        error_details=None,
    )


@router.delete("/kill/{session}/{window}")
async def kill_agent_tool(
    session: str, window: str, reason: str = "Manual termination requested", force: bool = False, notify_pm: bool = True
) -> dict[str, Union[str, bool, str]]:
    """MCP Tool: Kill a specific agent with proper cleanup.

    This tool terminates an agent with logging, optional graceful shutdown,
    and PM notification. Provides better tracking and coordination.
    """
    target = f"{session}:{window}"

    # Use the business logic tool
    tool_request = ToolKillRequest(target=target, reason=reason, force=force, notify_pm=notify_pm)

    result = kill_agent(tmux, tool_request)

    if not result.success:
        error_msg = result.error_message or "Unknown error"
        status_code = 404 if "not found" in error_msg.lower() else 500
        raise HTTPException(status_code=status_code, detail=error_msg)

    return {
        "success": True,
        "target": target,
        "message": f"Agent {target} terminated successfully",
        "reason": result.reason,
        "graceful_shutdown": result.graceful_shutdown,
        "pm_notified": result.pm_notified,
        "termination_time": result.termination_time.isoformat(),
    }


@router.get("/list")
async def list_all_agents() -> dict[str, Union[list[dict[str, str]], int]]:
    """MCP Tool: List all active agents across all sessions.

    This tool provides a comprehensive view of all running agents
    in the orchestration system.
    """
    try:
        agents = tmux.list_agents()

        return {
            "agents": agents,
            "count": len(agents),
            "active": len([a for a in agents if a["status"] == "Active"]),
            "idle": len([a for a in agents if a["status"] == "Idle"]),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _delayed_briefing(target: str, message: str) -> None:
    """Send briefing message after Claude starts."""
    # Wait for Claude to fully initialize
    await asyncio.sleep(5)
    tmux.send_message(target, message)
