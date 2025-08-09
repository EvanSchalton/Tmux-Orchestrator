"""Monitoring and status routes for MCP server."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tmux_orchestrator.server.tools.get_session_status import get_session_status
from tmux_orchestrator.utils.tmux import TMUXManager

router = APIRouter()
tmux = TMUXManager()


class SystemStatus(BaseModel):
    """API response model for system status."""

    total_sessions: int
    total_agents: int
    active_agents: int
    idle_agents: int
    sessions: list[dict[str, str]]


class SessionStatus(BaseModel):
    """API response model for session status."""

    session_name: str
    created: str
    attached: str
    windows: list[dict[str, str]]
    agents: list[dict[str, str]]


@router.get("/status", response_model=SystemStatus)
async def tmux_get_session_status() -> SystemStatus:
    """Get comprehensive system status.

    Primary MCP tool for system monitoring.
    """
    try:
        result = get_session_status(tmux)

        return SystemStatus(
            total_sessions=result.total_sessions,
            total_agents=result.total_agents,
            active_agents=result.active_agents,
            idle_agents=result.idle_agents,
            sessions=result.sessions,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=list[SessionStatus])
async def list_sessions() -> list[SessionStatus]:
    """List all tmux sessions with detailed information.

    MCP tool for session monitoring.
    """
    try:
        sessions = tmux.list_sessions()
        session_details = []

        for session in sessions:
            # Get windows for this session
            windows = tmux.list_windows(session["name"])

            # Get agents for this session
            all_agents = tmux.list_agents()
            session_agents = [agent for agent in all_agents if agent["session"] == session["name"]]

            session_details.append(
                SessionStatus(
                    session_name=session["name"],
                    created=session["created"],
                    attached=session["attached"],
                    windows=windows,
                    agents=session_agents,
                )
            )

        return session_details

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_name}")
async def get_session_detail(session_name: str) -> dict[str, Any]:
    """Get detailed information about a specific session.

    MCP tool for individual session monitoring.
    """
    try:
        if not tmux.has_session(session_name):
            raise HTTPException(status_code=404, detail="Session not found")

        # Get session info
        sessions = tmux.list_sessions()
        session_info = next((s for s in sessions if s["name"] == session_name), None)

        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found in list")

        # Get windows
        windows = tmux.list_windows(session_name)

        # Get agents
        all_agents = tmux.list_agents()
        session_agents = [agent for agent in all_agents if agent["session"] == session_name]

        # Get recent activity from each window
        window_activity = []
        for window in windows:
            target = f"{session_name}:{window['index']}"
            recent_output = tmux.capture_pane(target, lines=10)

            window_activity.append(
                {
                    "window": window,
                    "recent_output": recent_output.split("\n")[-5:] if recent_output else [],
                    "is_idle": tmux._is_idle(recent_output) if recent_output else True,
                }
            )

        return {
            "session": session_info,
            "windows": windows,
            "agents": session_agents,
            "window_activity": window_activity,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint for the MCP server."""
    try:
        # Test tmux connectivity
        sessions = tmux.list_sessions()

        return {
            "status": "healthy",
            "tmux_responsive": True,
            "active_sessions": len(sessions),
            "timestamp": "2025-01-08T00:00:00Z",  # Would use datetime in real implementation
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "tmux_responsive": False,
            "error": str(e),
            "timestamp": "2025-01-08T00:00:00Z",
        }


@router.get("/agents/idle")
async def get_idle_agents() -> dict[str, Any]:
    """Get list of idle agents that can receive new tasks.

    MCP tool for workload distribution.
    """
    try:
        agents = tmux.list_agents()
        idle_agents = [agent for agent in agents if agent["status"] == "Idle"]

        return {
            "idle_agents": idle_agents,
            "count": len(idle_agents),
            "available_types": list(set(agent["type"] for agent in idle_agents)),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/active")
async def get_active_agents() -> dict[str, Any]:
    """Get list of active agents and their current tasks.

    MCP tool for activity monitoring.
    """
    try:
        agents = tmux.list_agents()
        active_agents = []

        for agent in agents:
            if agent["status"] == "Active":
                # Get recent output to understand what they're working on
                target = f"{agent['session']}:{agent['window']}"
                recent_output = tmux.capture_pane(target, lines=20)

                active_agents.append(
                    {
                        **agent,
                        "recent_activity": recent_output.split("\n")[-5:] if recent_output else [],
                    }
                )

        return {"active_agents": active_agents, "count": len(active_agents)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
