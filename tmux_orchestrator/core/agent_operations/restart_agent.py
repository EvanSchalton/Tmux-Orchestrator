"""Business logic for restarting individual agents."""

import time
from typing import Tuple

from tmux_orchestrator.utils.tmux import TMUXManager


def restart_agent(tmux: TMUXManager, target: str) -> Tuple[bool, str]:
    """Restart a specific Claude agent.

    Args:
        tmux: TMUXManager instance
        target: Target agent in format session:window

    Returns:
        Tuple of (success, message)
    """
    # Parse target
    try:
        session, window = target.split(':')
        if not session or not window:
            return False, f"Invalid target format '{target}'. Use session:window"
    except ValueError:
        return False, f"Invalid target format '{target}'. Use session:window"

    # Check if target exists
    if not tmux.has_session(session):
        return False, f"Session '{session}' not found"

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
