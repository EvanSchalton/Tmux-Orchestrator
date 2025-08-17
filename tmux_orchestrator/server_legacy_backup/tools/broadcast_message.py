"""Business logic for broadcasting messages to multiple Claude agents."""

from dataclasses import dataclass
from typing import Optional

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class BroadcastMessageRequest:
    """Request parameters for broadcasting a message."""

    session: Optional[str] = None  # Optional - if None, broadcast to all sessions
    message: str = ""
    agent_types: Optional[list[str]] = None  # Filter by agent types (e.g., ["developer", "qa"])
    exclude_targets: Optional[list[str]] = None  # Targets to exclude from broadcast
    urgent: bool = False
    role: Optional[str] = None  # Broadcast to specific role across all sessions (e.g., "pm")


@dataclass
class BroadcastMessageResult:
    """Result of broadcasting a message operation."""

    success: bool
    session: str
    message_sent: str
    targets_sent: list[str]
    targets_failed: list[str]
    error_message: Optional[str] = None


def broadcast_message(tmux: TMUXManager, request: BroadcastMessageRequest) -> BroadcastMessageResult:
    """
    Broadcast a message to multiple Claude agents.

    Can broadcast to:
    - All agents in a specific session
    - All agents of a specific type in a session
    - All agents of a specific role across all sessions
    - All agents across all sessions (if session is None)

    Args:
        tmux: TMUXManager instance for tmux operations
        request: BroadcastMessageRequest with message and filters

    Returns:
        BroadcastMessageResult indicating success/failure for each target

    Raises:
        ValueError: If message is empty
    """
    # Validate message content
    if not request.message.strip():
        return BroadcastMessageResult(
            success=False,
            session=request.session or "all",
            message_sent=request.message,
            targets_sent=[],
            targets_failed=[],
            error_message="Message cannot be empty",
        )

    # If specific session requested, verify it exists
    if request.session and not tmux.has_session(request.session):
        return BroadcastMessageResult(
            success=False,
            session=request.session,
            message_sent=request.message,
            targets_sent=[],
            targets_failed=[],
            error_message=f"Session '{request.session}' not found",
        )

    targets_sent = []
    targets_failed = []

    try:
        # Determine which sessions to broadcast to
        sessions_to_process = []

        if request.session:
            # Specific session requested
            sessions_to_process = [request.session]
        else:
            # Broadcast to all sessions
            all_sessions = tmux.list_sessions()
            sessions_to_process = [s.get("name", "") for s in all_sessions if s.get("name")]

        # Process each session
        for session_name in sessions_to_process:
            if not tmux.has_session(session_name):
                continue

            # Get all windows in the session
            windows = tmux.list_windows(session_name)

            for window in windows:
                window_id = window.get("id", "")
                window_name = window.get("name", "").lower()
                target = f"{session_name}:{window_id}"

                # Skip if in exclude list
                if request.exclude_targets and target in request.exclude_targets:
                    continue

                # Determine agent type
                agent_type = _determine_agent_type(window_name)

                # Filter by role if specified (e.g., broadcast to all PMs)
                if request.role and agent_type != request.role:
                    continue

                # Filter by agent types if specified
                if request.agent_types and agent_type not in request.agent_types:
                    continue

                # Check if window contains a Claude agent
                if not _is_claude_window(tmux, target):
                    continue

                # Format message with urgency if needed
                message_to_send = request.message
                if request.urgent:
                    message_to_send = f"🚨 URGENT: {message_to_send}"

                # Send message to this target
                try:
                    success = tmux.send_message(target, message_to_send)
                    if success:
                        targets_sent.append(target)
                    else:
                        targets_failed.append(target)
                except Exception:
                    targets_failed.append(target)

        # Determine overall success
        overall_success = len(targets_sent) > 0

        return BroadcastMessageResult(
            success=overall_success,
            session=request.session or "all",
            message_sent=request.message,
            targets_sent=targets_sent,
            targets_failed=targets_failed,
            error_message=None if overall_success else "No agents found to broadcast to",
        )

    except Exception as e:
        return BroadcastMessageResult(
            success=False,
            session=request.session or "all",
            message_sent=request.message,
            targets_sent=targets_sent,
            targets_failed=targets_failed,
            error_message=f"Unexpected error broadcasting message: {str(e)}",
        )


def _determine_agent_type(window_name: str) -> str:
    """Determine agent type from window name."""
    window_name_lower = window_name.lower()

    # Check more specific types first
    if "orchestrator" in window_name_lower:
        return "orchestrator"
    elif "pm" in window_name_lower or "project-manager" in window_name_lower:
        return "pm"
    elif "devops" in window_name_lower:
        return "devops"
    elif "qa" in window_name_lower or "test" in window_name_lower:
        return "qa"
    # Check for developer variations (including frontend/backend dev)
    elif "developer" in window_name_lower or "-dev" in window_name_lower:
        return "developer"
    elif "frontend" in window_name_lower:
        return "frontend"
    elif "backend" in window_name_lower:
        return "backend"
    else:
        return "agent"


def _is_claude_window(tmux: TMUXManager, target: str) -> bool:
    """Check if a window contains a Claude agent."""
    try:
        content = tmux.capture_pane(target, lines=10)

        # Look for Claude interface indicators
        claude_indicators = ["│ >", "assistant:", "I'll help", "I can help", "Human:", "Claude:"]

        return any(indicator in content for indicator in claude_indicators)

    except Exception:
        return False
