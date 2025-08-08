"""Business logic for broadcasting messages to team agents."""

from typing import Dict, List, Tuple, Union

from tmux_orchestrator.utils.tmux import TMUXManager


def broadcast_to_team(
    tmux: TMUXManager, session: str, message: str
) -> Tuple[bool, str, List[Dict[str, Union[str, bool]]]]:
    """Broadcast a message to all agents in a session.

    Args:
        tmux: TMUXManager instance
        session: Session name
        message: Message to broadcast

    Returns:
        Tuple of (success, summary_message, detailed_results)
    """
    if not tmux.has_session(session):
        return False, f"Session '{session}' not found", []

    windows: List[Dict[str, str]] = tmux.list_windows(session)
    agent_windows: List[Dict[str, str]] = []

    # Find agent windows
    for window in windows:
        window_name_lower: str = window['name'].lower()
        if 'claude' in window_name_lower or 'pm' in window_name_lower:
            agent_windows.append(window)

    if not agent_windows:
        return False, f"No agent windows found in session '{session}'", []

    # Send message to each agent
    results: List[Dict[str, Union[str, bool]]] = []
    success_count: int = 0

    for window in agent_windows:
        target: str = f"{session}:{window['index']}"
        success: bool = tmux.send_message(target, message)

        results.append({
            'target': target,
            'window_name': window['name'],
            'success': success
        })

        if success:
            success_count += 1

    total_agents: int = len(agent_windows)
    summary: str = f"Broadcast complete: {success_count}/{total_agents} agents reached"

    return success_count > 0, summary, results
