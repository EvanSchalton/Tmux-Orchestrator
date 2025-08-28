"""Auto-restart mechanism with context preservation for failed agents.

Handles automatic recovery of failed agents while preserving their conversation context
and briefing information. Follows one-function-per-file pattern with comprehensive
type annotations.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tmux_orchestrator.core.recovery.briefing_manager import (
    restore_agent_briefing,
)
from tmux_orchestrator.core.recovery.restart_agent import restart_agent
from tmux_orchestrator.utils.tmux import TMUXManager


def auto_restart_agent(
    tmux: TMUXManager,
    target: str,
    logger: logging.Logger,
    max_retries: int = 3,
    preserve_context: bool = True,
    briefing_text: str | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """
    Automatically restart a failed agent with context preservation.

    Captures agent conversation history before restart, performs the restart,
    and restores briefing information. Implements comprehensive error handling
    and retry logic.

    Args:
        tmux: TMUX manager instance for session operations
        target: Target agent in format 'session:window' or 'session:window.pane'
        logger: Logger instance for recording recovery events
        max_retries: Maximum number of restart attempts (default: 3)
        preserve_context: Whether to capture context before restart (default: True)
        briefing_text: Custom briefing text to restore after restart

    Returns:
        Tuple of (success, message, context_data) where:
        - success: Boolean indicating if restart was successful
        - message: Human-readable result message
        - context_data: Dictionary containing preserved context information

    Raises:
        ValueError: If target format is invalid
        RuntimeError: If critical restart operations fail
    """
    # Validate target format
    if ":" not in target:
        raise ValueError(f"Invalid target format: {target}. Expected 'session:window'")

    session, window_part = target.split(":", 1)
    window = window_part.split(".")[0]  # Handle pane notation

    logger.info(f"Starting auto-restart for agent: {target}")

    # Initialize context data
    context_data: dict[str, Any] = {
        "target": target,
        "session": session,
        "window": window,
        "restart_time": datetime.now().isoformat(),
        "context_preserved": False,
        "briefing_restored": False,
        "conversation_history": [],
        "retry_attempts": 0,
    }

    # Step 1: Capture context if requested
    if preserve_context:
        try:
            history_lines: int = 500  # Capture last 500 lines
            conversation_content: str = tmux.capture_pane(target, lines=history_lines)

            if conversation_content:
                context_data["conversation_history"] = conversation_content.split("\n")
                context_data["context_preserved"] = True
                logger.info(f"Preserved {len(context_data['conversation_history'])} lines of context")

                # Save context to file for recovery logging
                context_file: Path = _save_context_to_file(target=target, content=conversation_content, logger=logger)
                context_data["context_file"] = str(context_file)
            else:
                logger.warning(f"No context content captured for {target}")

        except Exception as e:
            logger.error(f"Failed to preserve context for {target}: {str(e)}")
            # Don't fail the restart if context preservation fails
            context_data["context_error"] = str(e)

    # Step 2: Attempt restart with retry logic
    restart_success: bool = False
    restart_message: str = ""
    retry_delay: float = 2.0  # Delay between retries in seconds

    for attempt in range(1, max_retries + 1):
        context_data["retry_attempts"] = attempt
        logger.info(f"Restart attempt {attempt}/{max_retries} for {target}")

        try:
            restart_success, restart_message = restart_agent(target, logger)

            if restart_success:
                logger.info(f"Agent {target} restarted successfully on attempt {attempt}")
                break
            else:
                logger.warning(f"Restart attempt {attempt} failed: {restart_message}")

        except Exception as e:
            error_message: str = f"Restart attempt {attempt} exception: {str(e)}"
            logger.error(error_message)
            restart_message = error_message

        # Wait before retry (except on last attempt)
        if attempt < max_retries:
            time.sleep(retry_delay)

    # Update context data with restart results
    context_data["restart_successful"] = restart_success
    context_data["restart_message"] = restart_message

    if not restart_success:
        final_message: str = f"Auto-restart failed for {target} after {max_retries} attempts: {restart_message}"
        logger.error(final_message)
        return False, final_message, context_data

    # Step 3: Restore briefing if agent restarted successfully
    if restart_success:
        try:
            # Determine agent role from target
            agent_role: str = _determine_agent_role(target)

            # Use custom briefing or role-based briefing
            briefing_success: bool
            briefing_message: str
            briefing_data: dict[str, Any]

            briefing_success, briefing_message, briefing_data = restore_agent_briefing(
                tmux=tmux,
                target=target,
                agent_role=agent_role,
                custom_briefing=briefing_text,  # Will use this if provided, else role template
                logger=logger,
            )

            context_data["briefing_restored"] = briefing_success
            context_data["briefing_data"] = briefing_data
            context_data["agent_role"] = agent_role

            if briefing_success:
                logger.info(f"Agent briefing restored for {target}: {briefing_message}")
            else:
                logger.warning(f"Failed to restore briefing for {target}: {briefing_message}")

        except Exception as e:
            logger.error(f"Briefing restoration failed for {target}: {str(e)}")
            context_data["briefing_error"] = str(e)
            context_data["briefing_restored"] = False

    # Final success message
    success_message: str = (
        f"Agent {target} auto-restarted successfully (attempt {context_data['retry_attempts']}/{max_retries})"
    )

    if context_data["context_preserved"]:
        success_message += f", context preserved ({len(context_data['conversation_history'])} lines)"

    if context_data["briefing_restored"]:
        success_message += ", briefing restored"

    logger.info(success_message)
    return True, success_message, context_data


def _save_context_to_file(target: str, content: str, logger: logging.Logger) -> Path:
    """Save agent context to recovery log file."""
    # Create recovery logs directory
    log_dir: Path = Path.cwd() / "registry" / "logs" / "recovery"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_target: str = target.replace(":", "_").replace(".", "_")
    filename: str = f"context_{safe_target}_{timestamp}.log"

    context_file: Path = log_dir / filename

    try:
        # Write context with metadata header
        with open(context_file, "w", encoding="utf-8") as f:
            f.write("=== Agent Context Recovery Log ===\n")
            f.write(f"Target: {target}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Context Lines: {len(content.split())}\n")
            f.write("=" * 50 + "\n\n")
            f.write(content)

        logger.info(f"Context saved to: {context_file}")
        return context_file

    except Exception as e:
        logger.error(f"Failed to save context to file: {str(e)}")
        raise


def _determine_agent_role(target: str) -> str:
    """Determine agent role from target session and window information."""
    session_name: str = target.split(":")[0].lower()
    window_part: str = target.split(":")[1].lower()

    # Role mapping based on session names
    if "pm" in session_name or "project-manager" in session_name:
        return "pm"
    elif "frontend" in session_name:
        return "developer"
    elif "backend" in session_name:
        return "developer"
    elif "testing" in session_name or "qa" in session_name:
        return "qa"
    elif "devops" in session_name or "infra" in session_name:
        return "devops"
    elif "orchestrator" in session_name or session_name == "tmux-orc":
        return "orchestrator"

    # Role mapping based on window names/numbers for tmux-orc-dev
    if session_name == "tmux-orc-dev":
        window_num = window_part.split(".")[0]  # Remove pane if present
        role_map = {
            "1": "orchestrator",
            "2": "developer",
            "3": "developer",
            "4": "developer",
            "5": "pm",
        }
        return role_map.get(window_num, "developer")

    # Check for role indicators in window name/number
    if "pm" in window_part or "manager" in window_part:
        return "pm"
    elif "qa" in window_part or "test" in window_part:
        return "qa"
    elif "dev" in window_part or "developer" in window_part:
        return "developer"
    elif "ops" in window_part or "infra" in window_part:
        return "devops"

    # Default to developer role
    return "developer"
