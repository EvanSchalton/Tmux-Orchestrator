"""Detect agent failures using bulletproof idle detection and error patterns."""

import time
from datetime import datetime, timedelta
from typing import List, Tuple

from tmux_orchestrator.utils.tmux import TMUXManager


def detect_failure(
    tmux: TMUXManager,
    target: str,
    last_response: datetime,
    consecutive_failures: int,
    max_failures: int = 3,
    response_timeout: int = 60
) -> Tuple[bool, str, bool]:
    """
    Detect if an agent has failed and needs recovery.

    Uses the bulletproof 4-snapshot idle detection method combined with
    error pattern analysis to determine if an agent is unresponsive.

    Args:
        tmux: TMUXManager instance for tmux operations
        target: Target agent in format 'session:window'
        last_response: When agent last responded normally
        consecutive_failures: Number of consecutive health check failures
        max_failures: Maximum failures before considering agent failed
        response_timeout: Seconds without response before warning

    Returns:
        Tuple of (is_failed, failure_reason, is_idle)

    Raises:
        ValueError: If target format is invalid
        RuntimeError: If tmux operations fail
    """
    # Validate target format first
    if ':' not in target:
        raise ValueError(f"Invalid target format: {target}. Expected 'session:window'")

    try:
        # Use bulletproof 4-snapshot idle detection
        is_idle: bool = _check_idle_status(tmux, target)

        # Get current pane content for error analysis
        content: str = tmux.capture_pane(target, lines=50)

        # Check for critical errors first
        has_critical_errors: bool = _has_critical_errors(content)
        if has_critical_errors:
            return True, "critical_error_detected", is_idle

        # Check response timeout
        now: datetime = datetime.now()
        time_since_response: timedelta = now - last_response

        # Multiple failure conditions
        if consecutive_failures >= max_failures:
            return True, "max_consecutive_failures_reached", is_idle

        if time_since_response > timedelta(seconds=response_timeout * 3):
            return True, "extended_unresponsiveness", is_idle

        # Check if agent has normal interface but is stuck
        if not _has_normal_claude_interface(content) and not is_idle:
            return True, "abnormal_interface_state", is_idle

        return False, "healthy", is_idle

    except Exception as e:
        raise RuntimeError(f"Failed to detect failure for {target}: {str(e)}")


def _check_idle_status(tmux: TMUXManager, target: str) -> bool:
    """
    Check if agent is idle using 4-snapshot method.

    Takes 4 snapshots of the last line at 300ms intervals.
    If all snapshots are identical, agent is idle.

    Args:
        tmux: TMUXManager instance
        target: Target agent in format 'session:window'

    Returns:
        True if agent is idle, False if active
    """
    snapshots: List[str] = []

    for _ in range(4):
        content: str = tmux.capture_pane(target, lines=1)
        last_line: str = content.strip().split('\n')[-1] if content else ""
        snapshots.append(last_line)
        time.sleep(0.3)

    # If all snapshots are identical, agent is idle
    return all(line == snapshots[0] for line in snapshots)


def _has_critical_errors(content: str) -> bool:
    """
    Check for critical error patterns in agent output.

    Args:
        content: Captured pane content

    Returns:
        True if critical errors detected
    """
    critical_errors: List[str] = [
        "connection lost",
        "network error",
        "timeout",
        "crashed",
        "killed",
        "segmentation fault",
        "permission denied",
        "command not found",
        "python: can't open file",
        "ModuleNotFoundError",
        "ImportError",
        "SyntaxError",
        "claude: command not found",
        "authentication failed",
        "access denied"
    ]

    content_lower: str = content.lower()
    return any(error in content_lower for error in critical_errors)


def _has_normal_claude_interface(content: str) -> bool:
    """
    Check if content shows normal Claude interface elements.

    Args:
        content: Captured pane content

    Returns:
        True if normal Claude interface detected
    """
    claude_indicators: List[str] = [
        "│ >",           # Claude prompt box
        "assistant:",    # Claude response marker
        "I'll help",     # Common Claude response
        "I can help",    # Common Claude response
        "Let me",        # Common Claude response start
        "Human:",        # Human input marker
        "Claude:"        # Claude label
    ]

    return any(indicator in content for indicator in claude_indicators)
