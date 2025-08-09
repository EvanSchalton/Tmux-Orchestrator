"""System monitoring and status reporting routes for MCP server."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from tmux_orchestrator.server.tools.get_session_status import get_session_status
from tmux_orchestrator.utils.tmux import TMUXManager

router = APIRouter()
tmux = TMUXManager()


class SystemStatusRequest(BaseModel):
    """MCP tool request for system status."""

    include_details: bool = True
    include_recent_activity: bool = False

    model_config = ConfigDict(
        json_schema_extra={"example": {"include_details": True, "include_recent_activity": False}}
    )


class SystemStatusResponse(BaseModel):
    """MCP tool response for system status."""

    total_sessions: int
    total_agents: int
    active_agents: int
    idle_agents: int
    sessions: list[dict[str, str]]
    agents: list[dict[str, str]]
    system_health: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_sessions": 3,
                "total_agents": 5,
                "active_agents": 2,
                "idle_agents": 3,
                "sessions": [{"name": "my-project", "created": "123456"}],
                "agents": [{"session": "my-project", "type": "developer"}],
                "system_health": "healthy",
            }
        }
    )


class SessionDetailRequest(BaseModel):
    """MCP tool request for detailed session information."""

    session: str
    include_activity: bool = True
    activity_lines: int = 10

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session": "my-project",
                "include_activity": True,
                "activity_lines": 10,
            }
        }
    )


class SessionDetailResponse(BaseModel):
    """MCP tool response for session details."""

    session: dict[str, str]
    windows: list[dict[str, str]]
    agents: list[dict[str, str]]
    window_activity: list[dict[str, Any]]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session": {"name": "my-project", "created": "123456"},
                "windows": [{"index": "0", "name": "Claude-developer"}],
                "agents": [{"session": "my-project", "type": "developer"}],
                "window_activity": [{"window": {}, "is_idle": False}],
            }
        }
    )


class ActivityReportRequest(BaseModel):
    """MCP tool request for activity reporting."""

    time_window_minutes: int = 60
    include_idle_agents: bool = False
    session_filter: list[str] = []

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "time_window_minutes": 60,
                "include_idle_agents": False,
                "session_filter": ["my-project", "other-project"],
            }
        }
    )


class HealthCheckResponse(BaseModel):
    """MCP tool response for health check."""

    status: str
    tmux_responsive: bool
    active_sessions: int
    timestamp: str
    details: dict[str, Any] = {}

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "tmux_responsive": True,
                "active_sessions": 3,
                "timestamp": "2025-01-08T10:30:00Z",
                "details": {"uptime": "2 hours"},
            }
        }
    )


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status_tool(request: SystemStatusRequest) -> SystemStatusResponse:
    """MCP Tool: Get comprehensive system status.

    This is the primary monitoring tool that provides an overview of all
    sessions, agents, and system health in the orchestration system.
    """
    try:
        result = get_session_status(tmux)

        # Determine system health based on agent states
        system_health = "healthy"
        if result.total_agents == 0:
            system_health = "no_agents"
        elif result.active_agents == 0 and result.total_agents > 0:
            system_health = "all_idle"
        elif result.active_agents / result.total_agents < 0.3:
            system_health = "low_activity"

        return SystemStatusResponse(
            total_sessions=result.total_sessions,
            total_agents=result.total_agents,
            active_agents=result.active_agents,
            idle_agents=result.idle_agents,
            sessions=result.sessions,
            agents=result.agents,
            system_health=system_health,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=list[dict[str, Any]])
async def list_all_sessions_tool() -> list[dict[str, Any]]:
    """MCP Tool: List all tmux sessions with basic information.

    This tool provides a quick overview of all active tmux sessions
    without detailed agent information.
    """
    try:
        sessions = tmux.list_sessions()

        # Enhance session info with agent counts
        enhanced_sessions = []
        for session in sessions:
            # Get agents for this session
            all_agents = tmux.list_agents()
            session_agents = [agent for agent in all_agents if agent["session"] == session["name"]]

            enhanced_sessions.append(
                {
                    **session,
                    "agent_count": len(session_agents),
                    "active_agents": len([a for a in session_agents if a["status"] == "Active"]),
                    "idle_agents": len([a for a in session_agents if a["status"] == "Idle"]),
                }
            )

        return enhanced_sessions

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_name}", response_model=SessionDetailResponse)
async def get_session_detail_tool(session_name: str, request: SessionDetailRequest) -> SessionDetailResponse:
    """MCP Tool: Get detailed information about a specific session.

    This tool provides comprehensive information about a single session
    including windows, agents, and recent activity.
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

        # Get recent activity if requested
        window_activity = []
        if request.include_activity:
            for window in windows:
                target = f"{session_name}:{window['index']}"
                recent_output = tmux.capture_pane(target, lines=request.activity_lines)

                window_activity.append(
                    {
                        "window": window,
                        "recent_output": recent_output.split("\n")[-5:] if recent_output else [],
                        "is_idle": tmux._is_idle(recent_output) if recent_output else True,
                        "last_lines_count": len(recent_output.split("\n")) if recent_output else 0,
                    }
                )

        return SessionDetailResponse(
            session=session_info,
            windows=windows,
            agents=session_agents,
            window_activity=window_activity,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthCheckResponse)
async def health_check_tool() -> HealthCheckResponse:
    """MCP Tool: Comprehensive health check for the orchestration system.

    This tool performs a health check of the entire system including
    tmux connectivity and agent responsiveness.
    """
    try:
        # Test tmux connectivity
        sessions = tmux.list_sessions()
        agents = tmux.list_agents()

        # Perform basic health checks
        checks_passed: list[str] = []
        details = {
            "tmux_sessions": len(sessions),
            "total_agents": len(agents),
            "responsive_agents": len([a for a in agents if a["status"] == "Active"]),
            "checks_passed": checks_passed,
        }

        # Check if tmux is responding
        if len(sessions) >= 0:  # Even 0 sessions means tmux is responsive
            checks_passed.append("tmux_connectivity")

        # Check if we have any agents
        if len(agents) > 0:
            checks_passed.append("agents_present")

        # Check if at least some agents are active (if any exist)
        if len(agents) == 0 or len([a for a in agents if a["status"] == "Active"]) > 0:
            checks_passed.append("agents_responsive")

        status = "healthy" if len(checks_passed) >= 2 else "degraded"

        return HealthCheckResponse(
            status=status,
            tmux_responsive=True,
            active_sessions=len(sessions),
            timestamp="2025-01-08T00:00:00Z",  # Would use datetime.utcnow() in real implementation
            details=details,
        )

    except Exception as e:
        return HealthCheckResponse(
            status="unhealthy",
            tmux_responsive=False,
            active_sessions=0,
            timestamp="2025-01-08T00:00:00Z",
            details={"error": str(e), "checks_passed": []},
        )


@router.get("/agents/idle")
async def get_idle_agents_tool() -> dict[str, Any]:
    """MCP Tool: Get list of idle agents available for new tasks.

    This tool identifies agents that are currently idle and can
    be assigned new tasks or responsibilities.
    """
    try:
        agents = tmux.list_agents()
        idle_agents = [agent for agent in agents if agent["status"] == "Idle"]

        # Group idle agents by type
        by_type: dict[str, list[dict[str, str]]] = {}
        for agent in idle_agents:
            agent_type = agent["type"]
            if agent_type not in by_type:
                by_type[agent_type] = []
            by_type[agent_type].append(agent)

        return {
            "idle_agents": idle_agents,
            "count": len(idle_agents),
            "by_type": by_type,
            "available_types": list(by_type.keys()),
            "sessions": list(set(agent["session"] for agent in idle_agents)),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/active")
async def get_active_agents_tool() -> dict[str, Any]:
    """MCP Tool: Get list of active agents and their current activities.

    This tool shows which agents are currently active and provides
    insight into their recent activities for monitoring purposes.
    """
    try:
        agents = tmux.list_agents()
        active_agents: list[dict[str, Any]] = []

        for agent in agents:
            if agent["status"] == "Active":
                # Get recent output to understand what they're working on
                target = f"{agent['session']}:{agent['window']}"
                recent_output = tmux.capture_pane(target, lines=20)

                # Create a new dict with proper typing
                agent_data: dict[str, Any] = {
                    **agent,
                    "recent_activity": recent_output.split("\n")[-5:] if recent_output else [],
                    "activity_length": len(recent_output.split("\n")) if recent_output else 0,
                }
                active_agents.append(agent_data)

        # Group active agents by session
        by_session: dict[str, list[dict[str, Any]]] = {}
        for agent in active_agents:
            session: str = agent["session"]
            if session not in by_session:
                by_session[session] = []
            by_session[session].append(dict(agent))

        return {
            "active_agents": active_agents,
            "count": len(active_agents),
            "by_session": by_session,
            "sessions": list(by_session.keys()),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
