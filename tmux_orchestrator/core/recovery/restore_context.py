"""Restore context for recovered agents."""

import logging
from datetime import datetime
from typing import Any, Optional

from tmux_orchestrator.utils.tmux import TMUXManager


def restore_context(
    tmux: TMUXManager,
    target: str,
    logger: logging.Logger,
    context_data: Optional[dict[str, Any]] = None,
) -> bool:
    """
    Restore context for a recovered agent.

    Provides context restoration after agent restart to help the agent
    understand its current situation and continue work effectively.

    Args:
        tmux: TMUXManager instance for tmux operations
        target: Target agent in format 'session:window'
        logger: Logger instance for recording context restoration
        context_data: Optional context data to restore

    Returns:
        True if context restoration succeeded, False otherwise

    Raises:
        ValueError: If target format is invalid
        RuntimeError: If context restoration fails
    """
    # Validate target format
    if ":" not in target:
        raise ValueError(f"Invalid target format: {target}. Expected 'session:window'")

    logger.info(f"Restoring context for recovered agent: {target}")

    try:
        # Wait for agent to fully restart
        import time

        time.sleep(2)

        # Build context restoration message
        restore_message: str = _build_context_message(target, context_data)

        # Send context restoration message
        success: bool = tmux.send_message(target, restore_message)

        if success:
            logger.info(f"Context restoration message sent to {target}")
            return True
        else:
            logger.error(f"Failed to send context restoration message to {target}")
            return False

    except Exception as e:
        error_message: str = f"Failed to restore context for {target}: {str(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message)


def _build_context_message(target: str, context_data: Optional[dict[str, Any]] = None) -> str:
    """
    Build context restoration message for recovered agent.

    Args:
        target: Target agent identifier
        context_data: Optional context data

    Returns:
        Context restoration message string
    """
    timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    base_message: str = (
        f"RECOVERY NOTICE: You have been automatically restarted at {timestamp}.\n\n"
        f"You are an agent in the Tmux Orchestrator system working on: {target}\n\n"
        "RECOVERY CONTEXT:\n"
        "- Your previous session was terminated due to unresponsiveness\n"
        "- This is an automatic recovery to restore your functionality\n"
        "- Please resume your assigned tasks and report your status\n\n"
        "IMMEDIATE ACTIONS:\n"
        "1. Confirm you are operational by responding to this message\n"
        "2. Review any recent work that may have been interrupted\n"
        "3. Continue with your assigned responsibilities\n"
        "4. Report any issues or context you need restored\n\n"
        "The orchestrator is monitoring your health and will assist if needed."
    )

    # Add specific context data if provided
    if context_data:
        context_section: str = "\n\nADDITIONAL CONTEXT:\n"
        for key, value in context_data.items():
            context_section += f"- {key}: {value}\n"
        base_message += context_section

    return base_message
