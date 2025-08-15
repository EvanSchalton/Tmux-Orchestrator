"""Agent management routes for MCP server."""

import asyncio
from typing import Optional, Union

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from tmux_orchestrator.server.tools.get_session_status import (
    AgentStatusRequest as ToolAgentStatusRequest,
)
from tmux_orchestrator.server.tools.get_session_status import (
    get_agent_status,
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


class AgentSpawnRequest(BaseModel):
    """API request model for spawning an agent."""

    session_name: str
    agent_type: str = "developer"  # developer, pm, qa, devops, reviewer
    project_path: Optional[str] = None
    briefing_message: Optional[str] = None


class AgentSpawnResponse(BaseModel):
    """API response model for agent spawning."""

    success: bool
    session: str
    window: str
    message: Optional[str] = None


class AgentStatusResponse(BaseModel):
    """API response model for agent status."""

    session: str
    window: str
    type: str
    status: str


@router.post("/spawn", response_model=AgentSpawnResponse)
async def tmux_spawn_agent(request: AgentSpawnRequest, background_tasks: BackgroundTasks) -> AgentSpawnResponse:
    """Spawn a new Claude agent in a tmux session.

    This is the main MCP tool for creating new agents.
    """
    # Convert API request to business logic request
    tool_request = ToolSpawnRequest(
        session_name=request.session_name,
        agent_type=request.agent_type,
        project_path=request.project_path,
        briefing_message=request.briefing_message,
    )

    # Execute business logic
    result = await spawn_agent(tmux, tool_request)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message)

    # Schedule briefing if provided
    if request.briefing_message:
        background_tasks.add_task(_delayed_briefing, result.target, request.briefing_message)

    return AgentSpawnResponse(
        success=result.success,
        session=result.session,
        window=result.window,
        message=f"Agent {request.agent_type} spawned successfully",
    )


@router.post("/restart")
async def tmux_restart_agent(session: str, window: str) -> dict[str, Union[str, bool]]:
    """Restart a failed or stuck agent.

    MCP tool for agent recovery.
    """
    tool_request = ToolRestartRequest(session=session, window=window)

    result = await restart_agent(tmux, tool_request)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message)

    return {"success": True, "message": f"Agent {result.target} restarted successfully"}


@router.get("/list", response_model=list[AgentStatusResponse])
async def list_agents() -> list[AgentStatusResponse]:
    """List all active agents across sessions.

    MCP tool for monitoring agent status.
    """
    try:
        agents = tmux.list_agents()
        return [
            AgentStatusResponse(
                session=agent["session"],
                window=agent["window"],
                type=agent["type"],
                status=agent["status"],
            )
            for agent in agents
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{session}/{window}")
async def get_agent_status_route(session: str, window: str) -> dict[str, Union[str, list[str], int]]:
    """Get detailed status of a specific agent.

    MCP tool for individual agent monitoring.
    """
    tool_request = ToolAgentStatusRequest(session=session, window=window, lines=100)

    result = get_agent_status(tmux, tool_request)

    if result.error_message:
        raise HTTPException(
            status_code=404 if result.status == "not_found" else 500,
            detail=result.error_message,
        )

    return {
        "session": result.session,
        "window": result.window,
        "target": result.target,
        "status": result.status,
        "recent_output": result.recent_output,
        "output_length": result.output_length,
    }


async def _delayed_briefing(target: str, message: str) -> None:
    """Send briefing message after Claude starts."""
    # Wait for Claude to fully initialize
    await asyncio.sleep(5)
    tmux.send_message(target, message)
