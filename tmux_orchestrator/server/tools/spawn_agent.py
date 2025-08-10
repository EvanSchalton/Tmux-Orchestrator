"""Business logic for spawning new Claude agents."""

from dataclasses import dataclass
from typing import Optional

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class SpawnAgentRequest:
    """Request parameters for spawning an agent."""

    session_name: str
    agent_type: str
    project_path: Optional[str] = None
    briefing_message: Optional[str] = None


@dataclass
class SpawnAgentResult:
    """Result of spawning an agent operation."""

    success: bool
    session: str
    window: str
    target: str
    error_message: Optional[str] = None


def spawn_agent(tmux: TMUXManager, request: SpawnAgentRequest) -> SpawnAgentResult:
    """
    Spawn a new Claude agent in a tmux session.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: SpawnAgentRequest with agent configuration

    Returns:
        SpawnAgentResult indicating success/failure and created target

    Raises:
        ValueError: If session_name is empty or agent_type is invalid
        RuntimeError: If tmux operations fail
    """
    if not request.session_name.strip():
        return SpawnAgentResult(
            success=False,
            session=request.session_name,
            window="",
            target="",
            error_message="Session name cannot be empty",
        )

    valid_agent_types = [
        "developer",
        "pm",
        "qa",
        "devops",
        "reviewer",
        "researcher",
        "docs",
    ]
    if request.agent_type not in valid_agent_types:
        return SpawnAgentResult(
            success=False,
            session=request.session_name,
            window="",
            target="",
            error_message=f"Invalid agent type. Must be one of: {', '.join(valid_agent_types)}",
        )

    try:
        window_name = f"Claude-{request.agent_type}"

        # Create session or window
        if tmux.has_session(request.session_name):
            success = tmux.create_window(request.session_name, window_name, request.project_path)
            if not success:
                return SpawnAgentResult(
                    success=False,
                    session=request.session_name,
                    window=window_name,
                    target="",
                    error_message="Failed to create window in existing session",
                )
        else:
            success = tmux.create_session(request.session_name, window_name, request.project_path)
            if not success:
                return SpawnAgentResult(
                    success=False,
                    session=request.session_name,
                    window=window_name,
                    target="",
                    error_message="Failed to create new session",
                )

        # Start Claude in the new window
        target = f"{request.session_name}:{window_name}"

        start_success = tmux.send_keys(target, "claude --dangerously-skip-permissions")
        if not start_success:
            return SpawnAgentResult(
                success=False,
                session=request.session_name,
                window=window_name,
                target=target,
                error_message="Failed to start Claude command",
            )

        enter_success = tmux.send_keys(target, "Enter")
        if not enter_success:
            return SpawnAgentResult(
                success=False,
                session=request.session_name,
                window=window_name,
                target=target,
                error_message="Failed to send Enter key",
            )

        # CRITICAL: Wait for Claude to fully initialize before allowing messages
        # This prevents Ctrl+C interruption during startup
        import time

        time.sleep(8)  # Give Claude sufficient time to load completely

        return SpawnAgentResult(
            success=True,
            session=request.session_name,
            window=window_name,
            target=target,
        )

    except Exception as e:
        return SpawnAgentResult(
            success=False,
            session=request.session_name,
            window="",
            target="",
            error_message=f"Unexpected error during agent spawn: {str(e)}",
        )
