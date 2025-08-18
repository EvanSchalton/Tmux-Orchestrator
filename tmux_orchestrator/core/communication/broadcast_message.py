"""Business logic for broadcasting messages to multiple agents."""

from tmux_orchestrator.core.communication.send_message import send_message
from tmux_orchestrator.utils.tmux import TMUXManager


def broadcast_message(
    tmux: TMUXManager,
    session: str,
    message: str,
    agent_types: list[str | None] = None,
    exclude_windows: list[str | None] = None,
) -> tuple[bool, str]:
    """Broadcast a message to all or selected agents in a session.

    Args:
        tmux: TMUXManager instance
        session: Target session name
        message: Message content to broadcast
        agent_types: Optional list of agent types to target (filters by window name)
        exclude_windows: Optional list of window names/indices to exclude

    Returns:
        Tuple of (success, summary_message)
    """
    # Validate inputs
    if not session or not message:
        return False, "session and message are required"

    # Validate session exists
    if not tmux.has_session(session):
        return False, f"Session '{session}' not found"

    try:
        # Get all windows in the session
        windows = tmux.list_windows(session)
        if not windows:
            return False, f"No windows found in session '{session}'"

        # Filter windows based on criteria
        target_windows = []
        exclude_list = exclude_windows or []

        for window in windows:
            window_name = window.get("name", "")
            window_index = window.get("index", "")

            # Skip excluded windows
            if window_name in exclude_list or window_index in exclude_list:
                continue

            # Filter by agent types if specified
            if agent_types:
                # Check if window name matches any of the specified agent types
                matches_type = any(agent_type.lower() in window_name.lower() for agent_type in agent_types)
                if not matches_type:
                    continue

            target_windows.append(window)

        if not target_windows:
            return False, f"No target windows found matching criteria in session '{session}'"

        # Send message to each target window
        success_count = 0
        failed_targets = []

        for window in target_windows:
            window_index = window.get("index", "")
            target = f"{session}:{window_index}"

            success, error_msg = send_message(tmux, target, message)
            if success:
                success_count += 1
            else:
                failed_targets.append(f"{target}: {error_msg}")

        # Generate summary
        total_targets = len(target_windows)
        if success_count == total_targets:
            return True, f"Message broadcast to {success_count} agents in session '{session}'"
        elif success_count > 0:
            failed_summary = "; ".join(failed_targets[:3])  # Show first 3 failures
            if len(failed_targets) > 3:
                failed_summary += f" and {len(failed_targets) - 3} more"
            return False, f"Partial success: {success_count}/{total_targets} agents reached. Failures: {failed_summary}"
        else:
            return False, f"Broadcast failed: No agents reached in session '{session}'"

    except Exception as e:
        return False, f"Error broadcasting message: {str(e)}"
