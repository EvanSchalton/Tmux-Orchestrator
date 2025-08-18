"""Business logic for getting session status information."""

from typing import Any

from tmux_orchestrator.utils.tmux import TMUXManager


def get_session_status(tmux: TMUXManager, session_name: str) -> tuple[bool, dict[str, Any]]:
    """Get comprehensive status information for a tmux session.

    Args:
        tmux: TMUXManager instance
        session_name: Name of the session to check

    Returns:
        Tuple of (success, status_data) where status_data contains session info
    """
    try:
        # Check if session exists
        if not tmux.has_session(session_name):
            return False, {"error": f"Session '{session_name}' not found"}

        # Get session basic info
        sessions = tmux.list_sessions()
        session_info = None
        for session in sessions:
            if session["name"] == session_name:
                session_info = session
                break

        if not session_info:
            return False, {"error": f"Failed to retrieve session info for '{session_name}'"}

        # Get windows in the session
        windows = tmux.list_windows(session_name)

        # Analyze each window to determine agent status
        window_details = []
        agent_count = 0
        active_agents = 0
        idle_agents = 0

        for window in windows:
            window_index = window.get("index", "")
            window_name = window.get("name", "")
            is_active = window.get("active", "0") == "1"

            # Get pane content to analyze agent state
            target = f"{session_name}:{window_index}"
            pane_content = tmux.capture_pane(target, lines=20)

            # Determine if this is a Claude agent window
            is_agent = _is_claude_agent_window(window_name, pane_content)
            agent_status = "unknown"

            if is_agent:
                agent_count += 1
                if _is_agent_idle(pane_content):
                    agent_status = "idle"
                    idle_agents += 1
                else:
                    agent_status = "active"
                    active_agents += 1

            window_details.append(
                {
                    "index": window_index,
                    "name": window_name,
                    "active": is_active,
                    "is_agent": is_agent,
                    "agent_status": agent_status,
                    "content_preview": pane_content[:200] if pane_content else "",
                }
            )

        # Compile comprehensive status
        status_data = {
            "session_name": session_name,
            "created": session_info.get("created", ""),
            "attached": session_info.get("attached", "0") == "1",
            "window_count": len(windows),
            "agent_count": agent_count,
            "active_agents": active_agents,
            "idle_agents": idle_agents,
            "windows": window_details,
            "health": _determine_session_health(agent_count, active_agents, idle_agents),
        }

        return True, status_data

    except Exception as e:
        return False, {"error": f"Error getting session status: {str(e)}"}


def _is_claude_agent_window(window_name: str, pane_content: str) -> bool:
    """Determine if a window contains a Claude agent."""
    # Check window name patterns
    agent_patterns = ["claude", "pm", "developer", "qa", "devops", "reviewer"]
    name_lower = window_name.lower()

    if any(pattern in name_lower for pattern in agent_patterns):
        return True

    # Check pane content for Claude indicators
    claude_indicators = [
        "Claude Code",
        "│ >",  # Claude prompt
        "Type a message",
        "claude --dangerously-skip-permissions",
    ]

    return any(indicator in pane_content for indicator in claude_indicators)


def _is_agent_idle(pane_content: str) -> bool:
    """Determine if an agent appears to be idle based on pane content."""
    # Look for idle indicators
    idle_patterns = [
        "waiting for",
        "ready for",
        "awaiting",
        "standing by",
        "idle",
        "completed",
        "│ >",  # Empty Claude prompt
    ]

    content_lower = pane_content.lower()
    return any(pattern in content_lower for pattern in idle_patterns)


def _determine_session_health(agent_count: int, active_agents: int, idle_agents: int) -> str:
    """Determine overall session health based on agent states."""
    if agent_count == 0:
        return "no_agents"
    elif active_agents == agent_count:
        return "fully_active"
    elif idle_agents == agent_count:
        return "all_idle"
    elif active_agents > 0:
        return "mixed"
    else:
        return "unknown"
