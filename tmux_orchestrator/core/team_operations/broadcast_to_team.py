"""Business logic for broadcasting messages to team agents."""

from datetime import datetime
from typing import Any, Optional

from tmux_orchestrator.utils.tmux import TMUXManager


def broadcast_to_team(
    tmux: TMUXManager,
    session: str,
    message: str,
    exclude_windows: Optional[list[str | None]] = None,
    priority: str = "normal",
    agent_types: Optional[list[str | None]] = None,
) -> tuple[bool, str, list[dict[str, Any]]]:
    """Broadcast a message to all agents in a session.

    Args:
        tmux: TMUXManager instance
        session: Session name
        message: Message to broadcast
        exclude_windows: Optional list of window names/indices to exclude
        priority: Message priority (low, normal, high, urgent)
        agent_types: Optional list of specific agent types to target

    Returns:
        Tuple of (success, summary_message, detailed_results)
    """
    if not tmux.has_session(session):
        return False, f"Session '{session}' not found", []

    windows: list[dict[str, str]] = tmux.list_windows(session)
    agent_windows: list[dict[str, str]] = []
    exclude_windows = exclude_windows or []
    agent_types_lower = [t.lower() for t in (agent_types or []) if t is not None] if agent_types else []

    # Find agent windows
    for window in windows:
        window_name_lower: str = window["name"].lower()
        window_index: str = window["index"]

        # Check if window should be excluded
        if (
            window_name_lower in [e.lower() for e in exclude_windows if e is not None]
            or window_index in exclude_windows
        ):
            continue

        # Check if it's an agent window
        is_agent = "claude" in window_name_lower or "pm" in window_name_lower

        if is_agent:
            # Filter by agent type if specified
            if agent_types:
                type_match = any(agent_type in window_name_lower for agent_type in agent_types_lower)
                if not type_match:
                    continue

            agent_windows.append(window)

    if not agent_windows:
        return False, f"No matching agent windows found in session '{session}'", []

    # Format message with priority if needed
    formatted_message = _format_broadcast_message(message, priority)

    # Send message to each agent
    results: list[dict[str, Any]] = []
    success_count: int = 0
    failed_count: int = 0
    timestamp = datetime.utcnow().isoformat() + "Z"

    for window in agent_windows:
        target: str = f"{session}:{window['index']}"

        try:
            success: bool = tmux.send_message(target, formatted_message)
            agent_type = _determine_agent_type(window["name"])

            results.append(
                {
                    "target": target,
                    "window_name": window["name"],
                    "window_index": window["index"],
                    "agent_type": agent_type,
                    "success": success,
                    "timestamp": timestamp,
                    "priority": priority,
                    "error": None if success else "Failed to send message",
                }
            )

            if success:
                success_count += 1
            else:
                failed_count += 1

        except Exception as e:
            results.append(
                {
                    "target": target,
                    "window_name": window["name"],
                    "window_index": window["index"],
                    "agent_type": _determine_agent_type(window["name"]),
                    "success": False,
                    "timestamp": timestamp,
                    "priority": priority,
                    "error": str(e),
                }
            )
            failed_count += 1

    total_agents: int = len(agent_windows)
    summary_parts = [f"Broadcast complete: {success_count}/{total_agents} agents reached"]

    if failed_count > 0:
        summary_parts.append(f"{failed_count} failed")
    if exclude_windows:
        summary_parts.append(f"{len(exclude_windows)} excluded")
    if agent_types:
        summary_parts.append(f"filtered by types: {', '.join([t for t in agent_types if t is not None])}")

    summary: str = " | ".join(summary_parts)

    return success_count > 0, summary, results


def _format_broadcast_message(message: str, priority: str) -> str:
    """Format message with priority indicator if needed.

    Args:
        message: Original message
        priority: Priority level

    Returns:
        Formatted message
    """
    priority_prefixes = {"urgent": "🚨 URGENT: ", "high": "⚠️ HIGH PRIORITY: ", "low": "ℹ️ FYI: ", "normal": ""}

    prefix = priority_prefixes.get(priority, "")
    return f"{prefix}{message}" if prefix else message


def _determine_agent_type(window_name: str) -> str:
    """Determine agent type from window name.

    Args:
        window_name: Window name

    Returns:
        Agent type string
    """
    window_name_lower = window_name.lower()

    if "pm" in window_name_lower:
        return "project_manager"
    elif "qa" in window_name_lower:
        return "qa_engineer"
    elif "frontend" in window_name_lower:
        return "frontend_developer"
    elif "backend" in window_name_lower:
        return "backend_developer"
    elif "devops" in window_name_lower:
        return "devops_engineer"
    elif "reviewer" in window_name_lower:
        return "code_reviewer"
    elif "researcher" in window_name_lower:
        return "researcher"
    elif "docs" in window_name_lower:
        return "documentation_writer"
    elif "claude" in window_name_lower:
        return "developer"
    else:
        return "unknown"
