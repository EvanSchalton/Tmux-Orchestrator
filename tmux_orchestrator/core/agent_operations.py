"""Agent operations business logic."""

import time
from typing import Tuple

from tmux_orchestrator.utils.tmux import TMUXManager


def restart_agent(tmux: TMUXManager, target: str) -> Tuple[bool, str]:
    """
    Restart a specific agent using tmux operations.

    Args:
        tmux: TMUXManager instance for tmux operations
        target: Target agent in format 'session:window'

    Returns:
        Tuple of (success, message)

    Raises:
        ValueError: If target format is invalid
    """
    # Parse and validate target
    try:
        session, window = target.split(':')
    except ValueError:
        return False, "Invalid target format. Use session:window"

    # Check if target exists
    if not tmux.has_session(session):
        return False, f"Session '{session}' not found"

    try:
        # Kill the current Claude process
        tmux.send_keys(target, 'C-c')
        time.sleep(1)

        # Clear any remaining input
        tmux.send_keys(target, 'C-u')
        time.sleep(0.5)

        # Start new Claude instance
        tmux.send_keys(target, 'claude --dangerously-skip-permissions')
        time.sleep(0.5)
        tmux.send_keys(target, 'Enter')

        return True, f"Agent at {target} restarted successfully"

    except Exception as e:
        return False, f"Failed to restart agent: {str(e)}"
