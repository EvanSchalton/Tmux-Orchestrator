"""Business logic for listing all team sessions."""

from typing import Any

from tmux_orchestrator.utils.tmux import TMUXManager


def list_all_teams(tmux: TMUXManager) -> list[dict[str, Any]]:
    """List all team sessions with summary information.

    Args:
        tmux: TMUXManager instance

    Returns:
        List of dictionaries with team session information
    """
    sessions: list[dict[str, str]] = tmux.list_sessions()

    if not sessions:
        return []

    teams: list[dict[str, Any]] = []

    for session in sessions:
        windows: list[dict[str, str]] = tmux.list_windows(session["name"])
        total_windows: int = len(windows)

        # Count agent windows
        agent_count: int = 0
        for window in windows:
            window_name_lower: str = window["name"].lower()
            if "claude" in window_name_lower or "pm" in window_name_lower:
                agent_count += 1

        # Determine session status
        status: str = "Active"
        if session.get("attached") == "0":
            status = "Detached"

        teams.append(
            {
                "name": session["name"],
                "windows": total_windows,
                "agents": agent_count,
                "status": status,
                "created": session.get("created", "Unknown"),
            }
        )

    return teams
