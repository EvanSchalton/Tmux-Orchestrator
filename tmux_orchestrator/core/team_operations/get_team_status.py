"""Business logic for getting team status."""

from datetime import datetime
from typing import Any

from tmux_orchestrator.utils.tmux import TMUXManager


def get_team_status(tmux: TMUXManager, session: str) -> dict[str, Any | None]:
    """Get detailed team status for a session.

    Args:
        tmux: TMUXManager instance
        session: Session name to check

    Returns:
        Dictionary with team status or None if session not found
    """
    # Check if session exists
    if not tmux.has_session(session):
        return None

    # Get session info
    sessions: list[dict[str, str]] = tmux.list_sessions()
    session_info: dict[str, str | None] = next((s for s in sessions if s["name"] == session), None)

    if not session_info:
        return None

    # Get windows in session
    windows: list[dict[str, str]] = tmux.list_windows(session)

    if not windows:
        return {
            "session_name": session,
            "session_info": session_info,
            "windows": [],
            "summary": {
                "total_windows": 0,
                "active_agents": 0,
                "healthy_agents": 0,
                "idle_agents": 0,
                "error_agents": 0,
                "team_health": "empty",
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    # Process each window
    processed_windows: list[dict[str, Any]] = []
    active_agents: int = 0
    healthy_agents: int = 0
    idle_agents: int = 0
    error_agents: int = 0

    for window in windows:
        target: str = f"{session}:{window['index']}"

        # Determine window type
        window_name: str = window["name"]
        window_type: str = _determine_window_type(window_name)
        is_agent = "claude" in window_name.lower() or "pm" in window_name.lower()

        # Get pane content to determine status
        pane_content: str = tmux.capture_pane(target, 50)  # Increased lines for better analysis
        status, last_activity, health_score = _determine_window_status(tmux, pane_content)

        # Count agents by status
        if is_agent:
            active_agents += 1
            if status in ["Active", "Complete"]:
                healthy_agents += 1
            elif status == "Idle":
                idle_agents += 1
            elif status == "Error":
                error_agents += 1

        processed_windows.append(
            {
                "index": window["index"],
                "name": window_name,
                "type": window_type,
                "status": status,
                "last_activity": last_activity,
                "target": target,
                "is_agent": is_agent,
                "health_score": health_score,
                "pane_id": window.get("pane_id", ""),
            }
        )

    # Calculate team health
    team_health = _calculate_team_health(active_agents, healthy_agents, idle_agents, error_agents)

    return {
        "session_name": session,
        "session_info": session_info,
        "windows": processed_windows,
        "summary": {
            "total_windows": len(windows),
            "active_agents": active_agents,
            "healthy_agents": healthy_agents,
            "idle_agents": idle_agents,
            "error_agents": error_agents,
            "team_health": team_health,
            "health_percentage": (healthy_agents / active_agents * 100) if active_agents > 0 else 0,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def _determine_window_type(window_name: str) -> str:
    """Determine the type of a window based on its name.

    Args:
        window_name: Name of the window

    Returns:
        String description of window type
    """
    window_name_lower: str = window_name.lower()

    if "claude" in window_name_lower or "pm" in window_name_lower or "qa" in window_name_lower:
        if "pm" in window_name_lower:
            return "Project Manager"
        elif "qa" in window_name_lower:
            return "QA Engineer"
        elif "frontend" in window_name_lower:
            return "Frontend Dev"
        elif "backend" in window_name_lower:
            return "Backend Dev"
        else:
            return "Developer"
    elif "dev" in window_name_lower or "server" in window_name_lower:
        return "Dev Server"
    elif "shell" in window_name_lower:
        return "Shell"
    else:
        return "Other"


def _determine_window_status(tmux: TMUXManager, pane_content: str) -> tuple[str, str, float]:
    """Determine status and activity from pane content.

    Args:
        tmux: TMUXManager instance
        pane_content: Content from the pane

    Returns:
        Tuple of (status, last_activity, health_score)
    """
    status: str = "Active"
    last_activity: str = "Working..."
    health_score: float = 1.0

    content_lower = pane_content.lower()

    # Check for various states
    if tmux._is_idle(pane_content):
        status = "Idle"
        last_activity = "Waiting for task"
        health_score = 0.7
    elif "error" in content_lower or "exception" in content_lower or "failed" in content_lower:
        status = "Error"
        last_activity = "Has errors"
        health_score = 0.2
    elif "completed" in content_lower or "finished" in content_lower:
        status = "Complete"
        last_activity = "Task completed"
        health_score = 0.9
    elif "rate limit" in content_lower:
        status = "Rate Limited"
        last_activity = "Waiting for rate limit reset"
        health_score = 0.5
    elif "compacting" in content_lower or "thinking" in content_lower:
        status = "Processing"
        last_activity = "Deep thinking/processing"
        health_score = 0.8
    elif any(activity in content_lower for activity in ["implementing", "working on", "creating", "updating"]):
        status = "Active"
        last_activity = "Actively working"
        health_score = 1.0

    return status, last_activity, health_score


def _calculate_team_health(active_agents: int, healthy_agents: int, idle_agents: int, error_agents: int) -> str:
    """Calculate overall team health status.

    Args:
        active_agents: Total number of agents
        healthy_agents: Number of healthy agents
        idle_agents: Number of idle agents
        error_agents: Number of agents with errors

    Returns:
        Team health status string
    """
    if active_agents == 0:
        return "empty"

    health_ratio = healthy_agents / active_agents
    error_ratio = error_agents / active_agents

    if error_ratio > 0.5:
        return "critical"
    elif error_ratio > 0.2:
        return "degraded"
    elif health_ratio >= 0.8:
        return "healthy"
    elif health_ratio >= 0.5:
        return "fair"
    else:
        return "poor"
