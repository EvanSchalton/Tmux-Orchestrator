"""Business logic for killing agents and sessions."""

import time
from datetime import datetime
from typing import Any, Dict, List

from tmux_orchestrator.utils.tmux import TMUXManager


def kill_agent(
    tmux: TMUXManager,
    target: str,
    force: bool = False,
    save_state: bool = True,
    kill_session: bool = False,
    graceful_timeout: int = 5,
) -> tuple[bool, str, Dict[str, Any]]:
    """Kill a specific agent window or entire session.

    Args:
        tmux: TMUXManager instance
        target: Target in format session:window or just session name
        force: Force kill without graceful shutdown
        save_state: Save agent state before killing
        kill_session: Kill entire session instead of just window
        graceful_timeout: Seconds to wait for graceful shutdown

    Returns:
        Tuple of (success, message, details)
    """
    time.time()
    details = {
        "target": target,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "force": force,
        "save_state": save_state,
        "kill_session": kill_session,
        "saved_state": None,
        "windows_killed": [],
    }

    # Parse target
    if ":" in target:
        session, window = target.split(":", 1)
        if kill_session:
            details["warning"] = "Session kill requested but window specified, killing entire session"
    else:
        session = target
        window = None
        kill_session = True  # If no window specified, kill session

    # Check if session exists
    if not tmux.has_session(session):
        details["error"] = "Session not found"
        return False, f"Session '{session}' not found", details

    # Get session information
    windows = tmux.list_windows(session)
    details["total_windows"] = len(windows)

    if kill_session:
        # Kill entire session
        return _kill_session(tmux, session, windows, force, save_state, graceful_timeout, details)
    else:
        # Kill specific window
        return _kill_window(tmux, session, window, windows, force, save_state, graceful_timeout, details)


def _kill_session(
    tmux: TMUXManager,
    session: str,
    windows: List[Dict[str, str]],
    force: bool,
    save_state: bool,
    graceful_timeout: int,
    details: Dict[str, Any],
) -> tuple[bool, str, Dict[str, Any]]:
    """Kill an entire session."""

    # Save state if requested
    if save_state and not force:
        session_state = _save_session_state(tmux, session, windows)
        details["saved_state"] = session_state

    # Graceful shutdown attempt if not forced
    if not force:
        # Send exit commands to all agent windows
        for window in windows:
            window_name = window.get("name", "").lower()
            if "claude" in window_name or "pm" in window_name:
                target = f"{session}:{window['index']}"
                tmux.send_keys(target, "exit")
                details["windows_killed"].append(
                    {"window": window["name"], "index": window["index"], "method": "graceful"}
                )

        # Wait for graceful shutdown
        time.sleep(graceful_timeout)

    # Kill the session
    try:
        success = tmux.kill_session(session)
        if success:
            details["kill_duration"] = time.time() - details.get("start_time", time.time())
            return True, f"Session '{session}' killed successfully", details
        else:
            details["error"] = "Failed to kill session"
            return False, f"Failed to kill session '{session}'", details
    except Exception as e:
        details["error"] = str(e)
        return False, f"Error killing session '{session}': {e}", details


def _kill_window(
    tmux: TMUXManager,
    session: str,
    window: str,
    windows: List[Dict[str, str]],
    force: bool,
    save_state: bool,
    graceful_timeout: int,
    details: Dict[str, Any],
) -> tuple[bool, str, Dict[str, Any]]:
    """Kill a specific window."""

    # Find window info
    window_info = next((w for w in windows if w["index"] == window), None)
    if not window_info:
        details["error"] = "Window not found"
        return False, f"Window '{window}' not found in session '{session}'", details

    details["window_info"] = window_info
    target = f"{session}:{window}"

    # Save state if requested
    if save_state and not force:
        window_state = _save_window_state(tmux, target, window_info)
        details["saved_state"] = window_state

    # Graceful shutdown attempt if not forced
    if not force:
        window_name = window_info.get("name", "").lower()
        if "claude" in window_name or "pm" in window_name:
            # Send exit command
            tmux.send_keys(target, "exit")
            time.sleep(graceful_timeout)

    # Kill the window
    try:
        success = tmux.kill_window(target)
        if success:
            details["windows_killed"].append(
                {
                    "window": window_info["name"],
                    "index": window_info["index"],
                    "method": "forced" if force else "graceful",
                }
            )
            details["kill_duration"] = time.time() - details.get("start_time", time.time())
            return True, f"Window '{window}' in session '{session}' killed successfully", details
        else:
            details["error"] = "Failed to kill window"
            return False, f"Failed to kill window '{window}' in session '{session}'", details
    except Exception as e:
        details["error"] = str(e)
        return False, f"Error killing window '{window}': {e}", details


def _save_session_state(tmux: TMUXManager, session: str, windows: List[Dict[str, str]]) -> Dict[str, Any]:
    """Save session state before killing.

    Args:
        tmux: TMUXManager instance
        session: Session name
        windows: List of windows in session

    Returns:
        Session state dictionary
    """
    state = {"session": session, "timestamp": datetime.utcnow().isoformat() + "Z", "windows": []}

    for window in windows:
        window_name = window.get("name", "").lower()
        if "claude" in window_name or "pm" in window_name:
            target = f"{session}:{window['index']}"
            pane_content = tmux.capture_pane(target, lines=100)

            window_state = {
                "index": window["index"],
                "name": window["name"],
                "last_content": pane_content[-500:] if len(pane_content) > 500 else pane_content,
                "agent_type": _determine_agent_type_from_name(window["name"]),
            }
            state["windows"].append(window_state)

    return state


def _save_window_state(tmux: TMUXManager, target: str, window_info: Dict[str, str]) -> Dict[str, Any]:
    """Save window state before killing.

    Args:
        tmux: TMUXManager instance
        target: Target window
        window_info: Window information

    Returns:
        Window state dictionary
    """
    pane_content = tmux.capture_pane(target, lines=100)

    return {
        "window": window_info["name"],
        "index": window_info["index"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "last_content": pane_content[-500:] if len(pane_content) > 500 else pane_content,
        "agent_type": _determine_agent_type_from_name(window_info["name"]),
    }


def _determine_agent_type_from_name(window_name: str) -> str:
    """Determine agent type from window name.

    Args:
        window_name: Window name

    Returns:
        Agent type string
    """
    window_name_lower = window_name.lower()

    if "pm" in window_name_lower:
        return "project_manager"
    elif "qa" in window_name_lower:
        return "qa_engineer"
    elif "frontend" in window_name_lower:
        return "frontend_developer"
    elif "backend" in window_name_lower:
        return "backend_developer"
    elif "devops" in window_name_lower:
        return "devops_engineer"
    elif "reviewer" in window_name_lower:
        return "code_reviewer"
    elif "claude" in window_name_lower:
        return "developer"
    else:
        return "unknown"
