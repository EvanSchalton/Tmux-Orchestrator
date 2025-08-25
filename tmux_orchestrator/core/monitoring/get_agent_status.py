"""Business logic for getting individual agent status information."""

from typing import Any

from tmux_orchestrator.utils.tmux import TMUXManager


def get_agent_status(tmux: TMUXManager, target: str) -> tuple[bool, dict[str, Any]]:
    """Get detailed status information for a specific agent.

    Args:
        tmux: TMUXManager instance
        target: Target agent in format session:window

    Returns:
        Tuple of (success, status_data) containing agent information
    """
    # Validate target format
    try:
        session, window = target.split(":")
        if not session or not window:
            return False, {"error": f"Invalid target format '{target}'. Use session:window"}
    except ValueError:
        return False, {"error": f"Invalid target format '{target}'. Use session:window"}

    try:
        # Check if session exists
        if not tmux.has_session(session):
            return False, {"error": f"Session '{session}' not found"}

        # Get window information
        windows = tmux.list_windows(session)
        target_window = None

        for win in windows:
            if win.get("index") == window or win.get("name") == window:
                target_window = win
                break

        if not target_window:
            return False, {"error": f"Window '{window}' not found in session '{session}'"}

        # Capture pane content for analysis
        pane_content = tmux.capture_pane(target, lines=50)

        # Analyze agent state
        agent_state = _analyze_agent_state(pane_content)

        # Get recent activity
        recent_activity = _extract_recent_activity(pane_content)

        # Determine agent type from window name or content
        agent_type = _determine_agent_type(target_window.get("name", ""), pane_content)

        # Check if Claude is responsive
        is_responsive = _check_claude_responsiveness(pane_content)

        # Compile status data
        status_data = {
            "target": target,
            "session": session,
            "window": window,
            "window_name": target_window.get("name", ""),
            "active": target_window.get("active", "0") == "1",
            "agent_type": agent_type,
            "state": agent_state,
            "is_responsive": is_responsive,
            "recent_activity": recent_activity,
            "content_preview": pane_content[:300] if pane_content else "",
            "health": _determine_agent_health(agent_state, is_responsive),
        }

        return True, status_data

    except Exception as e:
        return False, {"error": f"Error getting agent status: {str(e)}"}


def _analyze_agent_state(pane_content: str) -> str:
    """Analyze pane content to determine agent state."""
    if not pane_content:
        return "unknown"

    content_lower = pane_content.lower()

    # Check for various states in order of priority
    if "error" in content_lower or "failed" in content_lower:
        return "error"
    elif "claude code" in content_lower and "│ >" in pane_content:
        return "ready"
    elif any(pattern in content_lower for pattern in ["working on", "processing", "analyzing"]):
        return "working"
    elif any(pattern in content_lower for pattern in ["waiting", "awaiting", "ready for"]):
        return "idle"
    elif "claude code" in content_lower:
        return "starting"
    elif "claude --dangerously-skip-permissions" in pane_content:
        return "launching"
    else:
        return "unknown"


def _extract_recent_activity(pane_content: str) -> list[str]:
    """Extract recent activity lines from pane content."""
    if not pane_content:
        return []

    lines = pane_content.split("\n")
    # Get last 5 non-empty lines that look like activity
    activity_lines: list[str] = []

    for line in reversed(lines):
        line = line.strip()
        if line and len(activity_lines) < 5:
            # Filter out prompt lines and system messages
            if not line.startswith("│ >") and not line.startswith("└─"):
                activity_lines.append(line)

    return list(reversed(activity_lines))


def _determine_agent_type(window_name: str, pane_content: str) -> str:
    """Determine the type of agent based on window name and content."""
    name_lower = window_name.lower()

    # Check window name first
    type_mappings = {
        "pm": "Project Manager",
        "developer": "Developer",
        "dev": "Developer",
        "qa": "QA Engineer",
        "devops": "DevOps Engineer",
        "reviewer": "Code Reviewer",
        "docs": "Documentation Writer",
        "research": "Researcher",
    }

    for key, value in type_mappings.items():
        if key in name_lower:
            return value

    # Check for claude prefix patterns
    if name_lower.startswith("claude-"):
        agent_type = name_lower[7:].replace("-", " ").replace("_", " ").title()
        return agent_type

    # Fallback to analyzing content for role indicators
    content_lower = pane_content.lower()
    if "project manager" in content_lower:
        return "Project Manager"
    elif "developer" in content_lower:
        return "Developer"
    elif "qa engineer" in content_lower:
        return "QA Engineer"

    return "Unknown Agent"


def _check_claude_responsiveness(pane_content: str) -> bool:
    """Check if Claude appears to be responsive."""
    if not pane_content:
        return False

    # Look for signs Claude is running and responsive
    responsive_indicators = [
        "│ >",  # Active prompt
        "Claude Code",  # Interface loaded
        "Type a message",  # Ready for input
    ]

    # Look for signs Claude is not responsive
    unresponsive_indicators = [
        "command not found",
        "connection refused",
        "timeout",
        "error:",
        "failed to",
    ]

    has_responsive = any(indicator in pane_content for indicator in responsive_indicators)
    has_unresponsive = any(indicator.lower() in pane_content.lower() for indicator in unresponsive_indicators)

    return has_responsive and not has_unresponsive


def _determine_agent_health(state: str, is_responsive: bool) -> str:
    """Determine overall agent health."""
    if not is_responsive:
        return "unhealthy"
    elif state == "error":
        return "error"
    elif state in ["ready", "working", "idle"]:
        return "healthy"
    elif state in ["starting", "launching"]:
        return "starting"
    else:
        return "unknown"
