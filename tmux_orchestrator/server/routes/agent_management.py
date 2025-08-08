"""Agent lifecycle management routes for MCP server."""

import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from tmux_orchestrator.server.tools.get_session_status import (
    AgentStatusRequest as ToolAgentStatusRequest,
)
from tmux_orchestrator.server.tools.get_session_status import get_agent_status
from tmux_orchestrator.server.tools.restart_agent import (
    RestartAgentRequest as ToolRestartRequest,
)
from tmux_orchestrator.server.tools.restart_agent import restart_agent
from tmux_orchestrator.server.tools.spawn_agent import (
    SpawnAgentRequest as ToolSpawnRequest,
)
from tmux_orchestrator.server.tools.spawn_agent import spawn_agent
from tmux_orchestrator.utils.tmux import TMUXManager

router = APIRouter()
tmux = TMUXManager()


class AgentSpawnRequest(BaseModel):
    """MCP tool request for spawning an agent."""
    session_name: str
    agent_type: str = "developer"  # developer, pm, qa, devops, reviewer, researcher, docs
    project_path: Optional[str] = None
    briefing_message: Optional[str] = None

    class Config:
        """Pydantic config for request validation."""
        json_schema_extra = {
            "example": {
                "session_name": "my-project",
                "agent_type": "developer",
                "project_path": "/path/to/project",
                "briefing_message": "You are the developer for this React project..."
            }
        }


class AgentSpawnResponse(BaseModel):
    """MCP tool response for agent spawning."""
    success: bool
    session: str
    window: str
    target: str
    message: Optional[str] = None

    class Config:
        """Pydantic config for response validation."""
        json_schema_extra = {
            "example": {
                "success": True,
                "session": "my-project",
                "window": "Claude-developer",
                "target": "my-project:Claude-developer",
                "message": "Agent developer spawned successfully"
            }
        }


class AgentRestartRequest(BaseModel):
    """MCP tool request for restarting an agent."""
    session: str
    window: str
    clear_terminal: bool = True
    restart_delay_seconds: float = 2.0

    class Config:
        """Pydantic config for request validation."""
        json_schema_extra = {
            "example": {
                "session": "my-project",
                "window": "Claude-developer",
                "clear_terminal": True,
                "restart_delay_seconds": 2.0
            }
        }


class AgentStatusRequest(BaseModel):
    """MCP tool request for agent status."""
    session: str
    window: str
    lines: int = 100

    class Config:
        """Pydantic config for request validation."""
        json_schema_extra = {
            "example": {
                "session": "my-project",
                "window": "Claude-developer",
                "lines": 100
            }
        }


class AgentStatusResponse(BaseModel):
    """MCP tool response for agent status."""
    session: str
    window: str
    target: str
    status: str
    recent_output: list[str]
    output_length: int

    class Config:
        """Pydantic config for response validation."""
        json_schema_extra = {
            "example": {
                "session": "my-project",
                "window": "Claude-developer",
                "target": "my-project:Claude-developer",
                "status": "active",
                "recent_output": ["Human: hello", "Assistant: Hi! How can I help?"],
                "output_length": 50
            }
        }


@router.post("/spawn", response_model=AgentSpawnResponse)
async def spawn_agent_tool(
    request: AgentSpawnRequest, background_tasks: BackgroundTasks
) -> AgentSpawnResponse:
    """MCP Tool: Spawn a new Claude agent in a tmux session.

    This is the primary MCP tool for creating new AI agents in the orchestration system.
    Agents are spawned in dedicated tmux windows with proper initialization.
    """
    # Convert API request to business logic request
    tool_request = ToolSpawnRequest(
        session_name=request.session_name,
        agent_type=request.agent_type,
        project_path=request.project_path,
        briefing_message=request.briefing_message
    )

    # Execute business logic
    result = spawn_agent(tmux, tool_request)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message)

    # Schedule briefing if provided
    if request.briefing_message:
        background_tasks.add_task(
            _delayed_briefing,
            result.target,
            request.briefing_message
        )

    return AgentSpawnResponse(
        success=result.success,
        session=result.session,
        window=result.window,
        target=result.target,
        message=f"Agent {request.agent_type} spawned successfully"
    )


@router.post("/restart")
async def restart_agent_tool(request: AgentRestartRequest) -> dict[str, str | bool]:
    """MCP Tool: Restart a failed or stuck agent.

    This tool handles agent recovery by safely restarting Claude processes
    while preserving the session context.
    """
    tool_request = ToolRestartRequest(
        session=request.session,
        window=request.window,
        clear_terminal=request.clear_terminal,
        restart_delay_seconds=request.restart_delay_seconds
    )

    result = await restart_agent(tmux, tool_request)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message)

    return {
        "success": True,
        "target": result.target,
        "message": f"Agent {result.target} restarted successfully"
    }


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status_tool(request: AgentStatusRequest) -> AgentStatusResponse:
    """MCP Tool: Get detailed status of a specific agent.

    This tool provides comprehensive status information about an agent
    including activity state and recent output.
    """
    tool_request = ToolAgentStatusRequest(
        session=request.session,
        window=request.window,
        lines=request.lines
    )

    result = get_agent_status(tmux, tool_request)

    if result.error_message:
        raise HTTPException(
            status_code=404 if result.status == "not_found" else 500,
            detail=result.error_message
        )

    return AgentStatusResponse(
        session=result.session,
        window=result.window,
        target=result.target,
        status=result.status,
        recent_output=result.recent_output,
        output_length=result.output_length
    )


@router.delete("/kill/{session}/{window}")
async def kill_agent_tool(session: str, window: str) -> dict[str, str | bool]:
    """MCP Tool: Kill a specific agent.

    This tool forcefully terminates an agent by killing its tmux window.
    Use with caution as this will lose any unsaved context.
    """
    try:
        target = f"{session}:{window}"

        if not tmux.has_session(session):
            raise HTTPException(status_code=404, detail="Session not found")

        # Kill the specific window
        success = tmux._run_tmux(['kill-window', '-t', target], check=False)

        if success.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to kill agent window: {success.stderr}"
            )

        return {
            "success": True,
            "target": target,
            "message": f"Agent {target} killed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_all_agents() -> dict[str, list[dict[str, str]]]:
    """MCP Tool: List all active agents across all sessions.

    This tool provides a comprehensive view of all running agents
    in the orchestration system.
    """
    try:
        agents = tmux.list_agents()

        return {
            "agents": agents,
            "count": len(agents),
            "active": len([a for a in agents if a['status'] == 'Active']),
            "idle": len([a for a in agents if a['status'] == 'Idle'])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _delayed_briefing(target: str, message: str) -> None:
    """Send briefing message after Claude starts."""
    # Wait for Claude to fully initialize
    await asyncio.sleep(5)
    tmux.send_message(target, message)
