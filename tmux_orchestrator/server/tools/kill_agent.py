"""Business logic for terminating Claude agents."""

import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class KillAgentRequest:
    """Request parameters for killing an agent."""

    target: str
    reason: str
    force: bool = False  # Whether to force kill without graceful shutdown
    notify_pm: bool = True  # Whether to notify PM about termination


@dataclass
class KillAgentResult:
    """Result of killing an agent operation."""

    success: bool
    target: str
    reason: str
    termination_time: datetime
    graceful_shutdown: bool
    pm_notified: bool
    error_message: Optional[str] = None


def kill_agent(tmux: TMUXManager, request: KillAgentRequest) -> KillAgentResult:
    """
    Terminate a Claude agent with proper cleanup and notifications.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: KillAgentRequest with target and termination details

    Returns:
        KillAgentResult indicating success/failure and cleanup status

    Raises:
        ValueError: If target format is invalid
    """
    termination_time = datetime.now()
    graceful_shutdown = False
    pm_notified = False

    try:
        # Validate target format
        if ":" not in request.target:
            return KillAgentResult(
                success=False,
                target=request.target,
                reason=request.reason,
                termination_time=termination_time,
                graceful_shutdown=False,
                pm_notified=False,
                error_message="Target must be in format 'session:window' or 'session:window.pane'",
            )

        # Extract session name and validate it exists
        session_name = request.target.split(":")[0]
        if not tmux.has_session(session_name):
            return KillAgentResult(
                success=False,
                target=request.target,
                reason=request.reason,
                termination_time=termination_time,
                graceful_shutdown=False,
                pm_notified=False,
                error_message=f"Session '{session_name}' not found",
            )
        # Step 1: Log termination reason
        _log_termination(request.target, request.reason, termination_time)

        # Step 2: Attempt graceful shutdown if not forced
        if not request.force:
            graceful_success = _attempt_graceful_shutdown(tmux, request.target)
            if graceful_success:
                graceful_shutdown = True
                # Graceful shutdown succeeded, no need to force kill
                success = True
            else:
                # If graceful shutdown failed, proceed with force kill
                success = _kill_target(tmux, request.target)
        else:
            # Force kill requested
            success = _kill_target(tmux, request.target)

        if not success:
            return KillAgentResult(
                success=False,
                target=request.target,
                reason=request.reason,
                termination_time=termination_time,
                graceful_shutdown=graceful_shutdown,
                pm_notified=False,
                error_message="Failed to kill target pane/window",
            )

        # Step 3: Notify PM if requested
        if request.notify_pm:
            pm_notified = _notify_pm_about_termination(tmux, request.target, request.reason, termination_time)

        # Step 4: Clean up any associated resources
        _cleanup_agent_resources(request.target)

        return KillAgentResult(
            success=True,
            target=request.target,
            reason=request.reason,
            termination_time=termination_time,
            graceful_shutdown=graceful_shutdown,
            pm_notified=pm_notified,
        )

    except Exception as e:
        return KillAgentResult(
            success=False,
            target=request.target,
            reason=request.reason,
            termination_time=termination_time,
            graceful_shutdown=graceful_shutdown,
            pm_notified=pm_notified,
            error_message=f"Unexpected error killing agent: {str(e)}",
        )


def _log_termination(target: str, reason: str, timestamp: datetime) -> None:
    """Log agent termination for audit trail."""
    import logging

    logger = logging.getLogger("agent_termination")
    logger.info(f"Agent termination: target={target}, reason={reason}, timestamp={timestamp.isoformat()}")


def _attempt_graceful_shutdown(tmux: TMUXManager, target: str) -> bool:
    """Attempt to gracefully shut down the agent."""
    try:
        # Send exit command to Claude
        tmux.send_keys(target, "exit")

        # Wait briefly for graceful exit
        time.sleep(2)

        # Check if pane still exists
        try:
            tmux.capture_pane(target, lines=1)
            # If we can still capture, graceful shutdown failed
            return False
        except Exception:
            # If capture fails, pane is gone (graceful shutdown succeeded)
            return True

    except Exception:
        return False


def _kill_target(tmux: TMUXManager, target: str) -> bool:
    """Force kill the target pane or window."""
    try:
        # Determine if target is a window or pane
        parts = target.split(":")
        if len(parts) == 2 and "." not in parts[1]:
            # It's a window reference (session:window)
            result = subprocess.run(
                ["tmux", "kill-window", "-t", target],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        else:
            # It's a pane reference (session:window.pane)
            result = subprocess.run(
                ["tmux", "kill-pane", "-t", target],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0

    except Exception:
        return False


def _notify_pm_about_termination(tmux: TMUXManager, target: str, reason: str, timestamp: datetime) -> bool:
    """Notify the PM about agent termination."""
    try:
        # Find PM session
        pm_target = _find_pm_target(tmux)
        if not pm_target:
            return False

        # Format notification message
        message = (
            f"🛑 AGENT TERMINATED\n\n"
            f"**Target**: {target}\n"
            f"**Time**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**Reason**: {reason}\n\n"
            f"This agent has been terminated and will need replacement if the work continues."
        )

        # Send notification
        success = tmux.send_message(pm_target, message)
        return success

    except Exception:
        return False


def _find_pm_target(tmux: TMUXManager) -> Optional[str]:
    """Find PM session for notifications."""
    try:
        # Check common PM locations
        if tmux.has_session("tmux-orc-dev"):
            windows = tmux.list_windows("tmux-orc-dev")
            for window in windows:
                if "project-manager" in window.get("name", "").lower() or window.get("id") == "5":
                    return "tmux-orc-dev:5"

        # Search other sessions
        sessions = tmux.list_sessions()
        for session in sessions:
            session_name = session.get("name", "")
            if "pm" in session_name.lower() or "project-manager" in session_name.lower():
                return f"{session_name}:0"

        return None

    except Exception:
        return None


def _cleanup_agent_resources(target: str) -> None:
    """Clean up any resources associated with the terminated agent."""
    # This could include:
    # - Removing from monitoring systems
    # - Cleaning up temporary files
    # - Updating team rosters
    # - Archiving conversation logs

    # For now, just log the cleanup
    import logging

    logger = logging.getLogger("agent_cleanup")
    logger.info(f"Cleaned up resources for terminated agent: {target}")
