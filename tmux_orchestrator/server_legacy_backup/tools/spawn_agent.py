"""Business logic for spawning new Claude agents."""

import asyncio
from dataclasses import dataclass
from typing import Optional

from tmux_orchestrator.core.agent_operations.spawn_agent import spawn_agent as core_spawn_agent
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


async def spawn_agent(tmux: TMUXManager, request: SpawnAgentRequest) -> SpawnAgentResult:
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
    try:
        # Delegate to core business logic (sync function)
        success, message = core_spawn_agent(
            tmux=tmux,
            agent_type=request.agent_type,
            session=request.session_name,
            briefing=request.briefing_message,
            start_directory=request.project_path,
        )

        # Extract window info from success message if available
        window_name = f"Claude-{request.agent_type}"
        target = f"{request.session_name}:{window_name}"

        if success:
            # Add async delay for Claude initialization
            await asyncio.sleep(8)  # Give Claude sufficient time to load completely

        return SpawnAgentResult(
            success=success,
            session=request.session_name,
            window=window_name if success else "",
            target=target if success else "",
            error_message=message if not success else None,
        )

    except Exception as e:
        return SpawnAgentResult(
            success=False,
            session=request.session_name,
            window="",
            target="",
            error_message=f"Unexpected error during agent spawn: {str(e)}",
        )
