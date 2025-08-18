"""Business logic for restarting individual agents."""

import time
from datetime import datetime
from typing import Any

from tmux_orchestrator.utils.tmux import TMUXManager


def restart_agent(
    tmux: TMUXManager,
    target: str,
    health_check: bool = True,
    preserve_context: bool = True,
    custom_command: str | None = None,
    timeout: int = 10,
) -> tuple[bool, str, dict[str, Any]]:
    """Restart a specific Claude agent with advanced options.

    Args:
        tmux: TMUXManager instance
        target: Target agent in format session:window
        health_check: Perform health check before restart
        preserve_context: Try to preserve agent context/briefing
        custom_command: Custom command to start agent (default: claude)
        timeout: Maximum time to wait for restart (seconds)

    Returns:
        Tuple of (success, message, details)
    """
    start_time = time.time()
    details = {
        "target": target,
        "start_time": datetime.utcnow().isoformat() + "Z",
        "health_check_performed": health_check,
        "context_preserved": False,
        "restart_reason": None,
        "window_info": None,
    }

    # Parse target
    try:
        session, window = target.split(":")
        if not session or not window:
            details["error"] = "Invalid target format"
            return False, f"Invalid target format '{target}'. Use session:window", details
    except ValueError:
        details["error"] = "Invalid target format"
        return False, f"Invalid target format '{target}'. Use session:window", details

    # Check if target exists
    if not tmux.has_session(session):
        details["error"] = "Session not found"
        return False, f"Session '{session}' not found", details

    # Get window information
    windows = tmux.list_windows(session)
    window_info = next((w for w in windows if w["index"] == window), None)
    if not window_info:
        details["error"] = "Window not found"
        return False, f"Window '{window}' not found in session '{session}'", details

    details["window_info"] = window_info

    # Perform health check if requested
    if health_check:
        pane_content = tmux.capture_pane(target, lines=50)
        health_status = _analyze_agent_health(pane_content)
        details["health_status"] = health_status
        details["restart_reason"] = health_status.get("reason", "Manual restart")

        # If agent is healthy and responsive, confirm restart
        if health_status.get("is_healthy", False):
            details["warning"] = "Agent appears healthy"

    # Capture context if preserve_context is enabled
    agent_context = None
    if preserve_context:
        agent_context = _extract_agent_context(tmux, target, window_info)
        details["extracted_context"] = bool(agent_context)

    # Kill the current Claude process
    tmux.send_keys(target, "C-c")
    time.sleep(1)

    # Clear any remaining input
    tmux.send_keys(target, "C-u")
    time.sleep(0.5)

    # Determine startup command
    if custom_command:
        startup_command = custom_command
    else:
        startup_command = "claude --dangerously-skip-permissions"

    # Start new Claude instance
    tmux.send_keys(target, startup_command)
    time.sleep(0.5)
    tmux.send_keys(target, "Enter")

    # Wait for startup
    time.sleep(2)

    # Restore context if available
    if agent_context and preserve_context:
        time.sleep(1)  # Give Claude time to fully start
        _restore_agent_context(tmux, target, agent_context)
        details["context_preserved"] = True

    # Verify restart success
    restart_duration = time.time() - start_time
    if restart_duration < timeout:
        # Check if agent started successfully
        new_content = tmux.capture_pane(target, lines=20)
        if "claude" in new_content.lower() or "human:" in new_content.lower():
            details["restart_duration"] = restart_duration
            details["status"] = "success"
            return True, f"Agent at {target} restarted successfully in {restart_duration:.1f}s", details
        else:
            details["error"] = "Agent did not start properly"
            details["status"] = "failed"
            return False, f"Agent at {target} failed to start properly", details
    else:
        details["error"] = "Restart timeout exceeded"
        details["status"] = "timeout"
        return False, f"Agent restart at {target} timed out after {timeout}s", details


def _analyze_agent_health(pane_content: str) -> dict[str, Any]:
    """Analyze agent health from pane content.

    Args:
        pane_content: Content from agent's pane

    Returns:
        Health analysis dictionary
    """
    content_lower = pane_content.lower()

    health_status = {"is_healthy": True, "is_responsive": True, "has_errors": False, "is_stuck": False, "reason": None}

    # Check for various unhealthy states
    if "error" in content_lower or "exception" in content_lower:
        health_status["has_errors"] = True
        health_status["is_healthy"] = False
        health_status["reason"] = "Agent has errors"
    elif "rate limit" in content_lower:
        health_status["is_responsive"] = False
        health_status["reason"] = "Rate limited"
    elif pane_content.count("\n") < 5 and len(pane_content) < 100:
        health_status["is_stuck"] = True
        health_status["is_healthy"] = False
        health_status["reason"] = "Agent appears stuck"
    elif "killed" in content_lower or "terminated" in content_lower:
        health_status["is_healthy"] = False
        health_status["is_responsive"] = False
        health_status["reason"] = "Agent was terminated"

    return health_status


def _extract_agent_context(tmux: TMUXManager, target: str, window_info: dict[str, str]) -> dict[str, Any | None]:
    """Extract agent context and briefing information.

    Args:
        tmux: TMUXManager instance
        target: Target agent
        window_info: Window information

    Returns:
        Context dictionary or None
    """
    window_name = window_info.get("name", "")

    # Determine agent type from window name
    agent_type = "developer"  # default
    if "pm" in window_name.lower():
        agent_type = "pm"
    elif "qa" in window_name.lower():
        agent_type = "qa"
    elif "devops" in window_name.lower():
        agent_type = "devops"
    elif "reviewer" in window_name.lower():
        agent_type = "reviewer"

    # Try to extract briefing from recent conversation
    pane_content = tmux.capture_pane(target, lines=100)
    briefing = _extract_briefing_from_content(pane_content)

    return {"agent_type": agent_type, "window_name": window_name, "briefing": briefing, "session": target.split(":")[0]}


def _extract_briefing_from_content(content: str) -> str | None:
    """Extract briefing message from pane content.

    Args:
        content: Pane content

    Returns:
        Briefing message or None
    """
    # Look for common briefing patterns
    lines = content.split("\n")
    briefing_keywords = ["you are", "your role", "briefing:", "context:", "task:"]

    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in briefing_keywords):
            # Extract next few lines as briefing
            briefing_lines = []
            for j in range(i, min(i + 10, len(lines))):
                if lines[j].strip():
                    briefing_lines.append(lines[j])
            if briefing_lines:
                return "\n".join(briefing_lines)

    return None


def _restore_agent_context(tmux: TMUXManager, target: str, context: dict[str, Any]) -> None:
    """Restore agent context after restart.

    Args:
        tmux: TMUXManager instance
        target: Target agent
        context: Context dictionary
    """
    agent_type = context.get("agent_type", "developer")
    briefing = context.get("briefing", "")
    session = context.get("session", "")

    # Send context restoration message
    restoration_message = f"You are a {agent_type} agent in the {session} project. "

    if briefing:
        restoration_message += f"Your previous briefing was: {briefing[:200]}... "

    restoration_message += "You were just restarted. Please continue with your tasks."

    tmux.send_message(target, restoration_message)
