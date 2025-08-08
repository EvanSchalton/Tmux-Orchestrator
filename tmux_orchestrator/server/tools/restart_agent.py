"""Business logic for restarting failed or stuck agents."""

import asyncio
from dataclasses import dataclass
from typing import Optional

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class RestartAgentRequest:
    """Request parameters for restarting an agent."""
    session: str
    window: str
    clear_terminal: bool = True
    restart_delay_seconds: float = 2.0


@dataclass
class RestartAgentResult:
    """Result of restarting an agent operation."""
    success: bool
    target: str
    error_message: Optional[str] = None


async def restart_agent(tmux: TMUXManager, request: RestartAgentRequest) -> RestartAgentResult:
    """
    Restart a failed or stuck Claude agent.
    
    Args:
        tmux: TMUXManager instance for tmux operations
        request: RestartAgentRequest with session and window info
        
    Returns:
        RestartAgentResult indicating success/failure
        
    Raises:
        ValueError: If session or window names are empty
    """
    if not request.session.strip():
        return RestartAgentResult(
            success=False,
            target="",
            error_message="Session name cannot be empty"
        )

    if not request.window.strip():
        return RestartAgentResult(
            success=False,
            target=f"{request.session}:",
            error_message="Window name cannot be empty"
        )

    target = f"{request.session}:{request.window}"

    # Validate session exists
    if not tmux.has_session(request.session):
        return RestartAgentResult(
            success=False,
            target=target,
            error_message=f"Session '{request.session}' not found"
        )

    try:
        # Kill current Claude process with double Ctrl+C
        interrupt_success = tmux.send_keys(target, "C-c")
        if not interrupt_success:
            return RestartAgentResult(
                success=False,
                target=target,
                error_message="Failed to send first interrupt signal"
            )

        await asyncio.sleep(1)

        second_interrupt_success = tmux.send_keys(target, "C-c")
        if not second_interrupt_success:
            return RestartAgentResult(
                success=False,
                target=target,
                error_message="Failed to send second interrupt signal"
            )

        await asyncio.sleep(1)

        # Clear terminal if requested
        if request.clear_terminal:
            clear_success = tmux.send_keys(target, "clear")
            if not clear_success:
                return RestartAgentResult(
                    success=False,
                    target=target,
                    error_message="Failed to clear terminal"
                )

            enter_success = tmux.send_keys(target, "Enter")
            if not enter_success:
                return RestartAgentResult(
                    success=False,
                    target=target,
                    error_message="Failed to send Enter after clear"
                )

        # Wait before restarting
        await asyncio.sleep(request.restart_delay_seconds)

        # Restart Claude
        start_success = tmux.send_keys(target, "claude --dangerously-skip-permissions")
        if not start_success:
            return RestartAgentResult(
                success=False,
                target=target,
                error_message="Failed to start Claude command"
            )

        final_enter_success = tmux.send_keys(target, "Enter")
        if not final_enter_success:
            return RestartAgentResult(
                success=False,
                target=target,
                error_message="Failed to send Enter to start Claude"
            )

        return RestartAgentResult(
            success=True,
            target=target
        )

    except Exception as e:
        return RestartAgentResult(
            success=False,
            target=target,
            error_message=f"Unexpected error during agent restart: {str(e)}"
        )
