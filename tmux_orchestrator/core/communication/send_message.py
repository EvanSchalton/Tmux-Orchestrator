"""Business logic for sending messages to individual agents."""

import subprocess
from pathlib import Path

from tmux_orchestrator.utils.tmux import TMUXManager


def send_message(
    tmux: TMUXManager,
    target: str,
    message: str,
    timeout: float | None = None,
) -> tuple[bool, str]:
    """Send a message to a specific Claude agent.

    Args:
        tmux: TMUXManager instance
        target: Target agent in format session:window
        message: Message content to send
        timeout: Optional timeout for the operation

    Returns:
        Tuple of (success, message/error)
    """
    # Validate inputs
    if not target or not message:
        return False, "target and message are required"

    # Parse target format
    try:
        session, window = target.split(":")
        if not session or not window:
            return False, f"Invalid target format '{target}'. Use session:window"
    except ValueError:
        return False, f"Invalid target format '{target}'. Use session:window"

    # Validate session exists
    if not tmux.has_session(session):
        return False, f"Session '{session}' not found"

    try:
        # Use TMUXManager's proven message sending method
        success = tmux.send_message(target, message, delay=0.5)

        if success:
            return True, f"Message sent to {target}"
        else:
            # Try fallback method using the tmux-message script
            script_path = Path("/workspaces/Tmux-Orchestrator/bin/tmux-message")
            if script_path.exists():
                result = subprocess.run(
                    [str(script_path), target, message],
                    capture_output=True,
                    text=True,
                    timeout=timeout or 30,
                    check=False,
                )
                if result.returncode == 0:
                    return True, f"Message sent to {target} via fallback method"
                else:
                    return False, f"Fallback send failed: {result.stderr}"
            else:
                return False, "Primary send method failed and no fallback script available"

    except subprocess.TimeoutExpired:
        return False, f"Timeout sending message to {target}"
    except Exception as e:
        return False, f"Error sending message to {target}: {str(e)}"
