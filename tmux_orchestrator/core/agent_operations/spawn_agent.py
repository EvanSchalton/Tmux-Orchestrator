"""Business logic for spawning new Claude agents."""

import subprocess
import time
from pathlib import Path

from tmux_orchestrator.utils.tmux import TMUXManager


def spawn_agent(
    tmux: TMUXManager,
    agent_type: str,
    session: str,
    window: str | None = None,
    briefing: str | None = None,
    context_file: str | None = None,
    start_directory: str | None = None,
) -> tuple[bool, str]:
    """Spawn a new Claude agent in a tmux session.

    Args:
        tmux: TMUXManager instance
        agent_type: Type of agent (pm, developer, qa, etc.)
        session: Target session name
        window: Window name/index (optional, defaults to agent_type)
        briefing: Initial briefing message for the agent
        context_file: Path to context file to load
        start_directory: Starting directory for the agent

    Returns:
        Tuple of (success, message/error)
    """
    # Validate inputs
    if not agent_type or not session:
        return False, "agent_type and session are required"

    # Default window name to agent type
    if not window:
        window = agent_type

    # Ensure session exists
    if not tmux.has_session(session):
        if not tmux.create_session(session, window, start_directory):
            return False, f"Failed to create session '{session}'"
    else:
        # Create new window in existing session
        if not tmux.create_window(session, window, start_directory):
            return False, f"Failed to create window '{window}' in session '{session}'"

    target = f"{session}:{window}"

    try:
        # Build Claude command with MCP configuration
        claude_cmd = "claude --dangerously-skip-permissions"

        # Check for MCP config file and add to command if present
        project_root = Path.cwd()
        mcp_config_path = project_root / ".mcp.json"
        if mcp_config_path.exists():
            claude_cmd += f" --mcp-config {mcp_config_path}"

        # Start Claude Code in the window
        if not tmux.send_keys(target, claude_cmd):
            return False, f"Failed to start Claude in {target}"

        time.sleep(0.5)

        if not tmux.press_enter(target):
            return False, f"Failed to submit Claude command in {target}"

        # Wait for Claude to start
        time.sleep(3.0)

        # Load context file if specified
        if context_file:
            context_path = Path(context_file)
            if context_path.exists():
                context_content = context_path.read_text()
                # Send context using the proven message method
                if not _send_agent_message(tmux, target, f"Context: {context_content}"):
                    return False, f"Failed to load context file for {target}"
                time.sleep(2.0)

        # Send initial briefing if provided
        if briefing:
            if not _send_agent_message(tmux, target, briefing):
                return False, f"Failed to send briefing to {target}"

        return True, f"Agent {agent_type} spawned successfully at {target}"

    except Exception as e:
        return False, f"Error spawning agent: {str(e)}"


def _send_agent_message(tmux: TMUXManager, target: str, message: str) -> bool:
    """Send a message to an agent using the established communication method.

    This uses the existing tmux-message script approach through TMUXManager.

    Args:
        tmux: TMUXManager instance
        target: Target pane (session:window)
        message: Message to send

    Returns:
        True if message was sent successfully
    """
    try:
        # Use the proven message sending method from TMUXManager
        return tmux.send_message(target, message)
    except Exception:
        # Fallback to the tmux-message script if available
        try:
            script_path = Path.cwd() / "bin" / "tmux-message"
            if script_path.exists():
                result = subprocess.run(
                    [str(script_path), target, message], capture_output=True, text=True, timeout=30, check=False
                )
                return result.returncode == 0
        except Exception:
            pass

        return False
