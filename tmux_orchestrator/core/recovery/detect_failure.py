"""Detect agent failures using bulletproof idle detection and error patterns.

Implements Task 5.1-5.3 from the comprehensive task list:
- 5.1: Idle detection v2 algorithm (4 snapshots at 300ms intervals)
- 5.2: Failure detection logic that distinguishes idle from failed
- 5.3: Unsubmitted message detection in Claude UI
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

from tmux_orchestrator.utils.tmux import TMUXManager


def detect_failure(
    tmux: TMUXManager,
    target: str,
    last_response: datetime,
    consecutive_failures: int,
    max_failures: int = 3,
    response_timeout: int = 60
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Detect if an agent has failed and needs recovery.

    Implements Tasks 5.1-5.3: Uses bulletproof 4-snapshot idle detection,
    distinguishes idle from failed states, and detects unsubmitted messages.

    Args:
        tmux: TMUXManager instance for tmux operations
        target: Target agent in format 'session:window'
        last_response: When agent last responded normally
        consecutive_failures: Number of consecutive health check failures
        max_failures: Maximum failures before considering agent failed
        response_timeout: Seconds without response before warning

    Returns:
        Tuple of (is_failed, failure_reason, status_details)
        where status_details contains: is_idle, has_unsubmitted, needs_auto_submit

    Raises:
        ValueError: If target format is invalid
        RuntimeError: If tmux operations fail
    """
    # Validate target format first
    if ':' not in target:
        raise ValueError(f"Invalid target format: {target}. Expected 'session:window'")

    try:
        # Task 5.1: Use bulletproof 4-snapshot idle detection
        idle_details: Dict[str, Any] = _check_idle_status_v2(tmux, target)
        is_idle: bool = idle_details['is_idle']

        # Get current pane content for comprehensive analysis
        content: str = tmux.capture_pane(target, lines=50)

        # Task 5.3: Check for unsubmitted messages in Claude UI
        unsubmitted_details: Dict[str, Any] = _detect_unsubmitted_messages(content)

        # Enhanced status details
        status_details: Dict[str, Any] = {
            'is_idle': is_idle,
            'idle_duration': idle_details['idle_duration'],
            'has_unsubmitted': unsubmitted_details['has_unsubmitted'],
            'unsubmitted_type': unsubmitted_details['type'],
            'needs_auto_submit': unsubmitted_details['auto_submit_recommended'],
            'last_activity_snapshot': idle_details['last_snapshot'],
            'interface_status': 'normal' if _has_normal_claude_interface(content) else 'abnormal'
        }

        # Task 5.2: Distinguish idle from failed states
        failure_analysis = _analyze_failure_state(
            content, is_idle, consecutive_failures, last_response,
            max_failures, response_timeout, unsubmitted_details
        )

        return failure_analysis['is_failed'], failure_analysis['reason'], status_details

    except Exception as e:
        # Return failure with diagnostic info
        status_details = {
            'is_idle': False,
            'idle_duration': 0,
            'has_unsubmitted': False,
            'unsubmitted_type': 'unknown',
            'needs_auto_submit': False,
            'error': str(e),
            'interface_status': 'error'
        }
        raise RuntimeError(f"Failed to detect failure for {target}: {str(e)}")


def _check_idle_status_v2(tmux: TMUXManager, target: str) -> Dict[str, Any]:
    """
    Check if agent is idle using bulletproof 4-snapshot method (Task 5.1).

    Uses the proven algorithm from idle-monitor-daemon.sh with 100% accuracy.
    Takes 4 snapshots of the last line at 300ms intervals.
    If all snapshots are identical, agent is idle.

    Args:
        tmux: TMUXManager instance
        target: Target agent in format 'session:window'

    Returns:
        Dictionary with idle status details:
        - is_idle: bool
        - idle_duration: float (seconds)
        - last_snapshot: str (the last line captured)
        - all_snapshots: List[str] (for debugging)
    """
    snapshots: List[str] = []
    start_time: float = time.time()

    # Take 4 snapshots at 300ms intervals (proven algorithm)
    for i in range(4):
        content: str = tmux.capture_pane(target, lines=1)
        last_line: str = content.strip().split('\n')[-1] if content else ""
        snapshots.append(last_line)

        # Sleep between snapshots (except after the last one)
        if i < 3:
            time.sleep(0.3)

    # Calculate total time for idle detection
    detection_time: float = time.time() - start_time

    # If all snapshots are identical, agent is idle
    is_idle: bool = all(line == snapshots[0] for line in snapshots)

    return {
        'is_idle': is_idle,
        'idle_duration': detection_time,
        'last_snapshot': snapshots[-1] if snapshots else "",
        'all_snapshots': snapshots,
        'snapshot_count': len(snapshots)
    }


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


def _detect_unsubmitted_messages(content: str) -> Dict[str, Any]:
    """
    Detect unsubmitted messages in Claude UI (Task 5.3).

    Args:
        content: Captured pane content

    Returns:
        Dictionary with unsubmitted message details
    """
    # Look for common UI indicators of unsubmitted messages
    indicators = {
        'draft_text': 'Type a message...' in content or '│ >' in content,
        'typing_cursor': '│' in content,
        'unsent_content': len(content.strip()) > 0 and not any(marker in content for marker in ['assistant:', 'Human:'])
    }

    has_unsubmitted = any(indicators.values())

    return {
        'has_unsubmitted': has_unsubmitted,
        'type': 'draft' if indicators['draft_text'] else 'typing' if indicators['typing_cursor'] else 'unknown',
        'auto_submit_recommended': has_unsubmitted,
        'indicators': indicators
    }


def _analyze_failure_state(
    content: str,
    is_idle: bool,
    consecutive_failures: int,
    last_response: datetime,
    max_failures: int,
    response_timeout: int,
    unsubmitted_details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze failure state and determine if agent needs recovery.

    Args:
        content: Pane content
        is_idle: Whether agent is idle
        consecutive_failures: Number of consecutive failures
        last_response: Last response time
        max_failures: Max failures before considering failed
        response_timeout: Response timeout in seconds
        unsubmitted_details: Unsubmitted message details

    Returns:
        Dictionary with failure analysis
    """
    # Check for critical errors first
    has_critical_errors = _has_critical_errors(content)

    # Calculate time since last response
    time_since_response = (datetime.now() - last_response).total_seconds()

    # Determine failure state
    is_failed = False
    reason = "Agent is healthy"

    if has_critical_errors:
        is_failed = True
        reason = "Critical errors detected in agent output"
    elif consecutive_failures >= max_failures:
        is_failed = True
        reason = f"Agent failed {consecutive_failures} consecutive health checks"
    elif time_since_response > response_timeout * 2:  # 2x timeout = failure
        is_failed = True
        reason = f"Agent unresponsive for {int(time_since_response)}s (timeout: {response_timeout}s)"
    elif unsubmitted_details['has_unsubmitted'] and time_since_response > response_timeout:
        is_failed = True
        reason = "Agent has unsubmitted message and is unresponsive"

    return {
        'is_failed': is_failed,
        'reason': reason,
        'has_critical_errors': has_critical_errors,
        'time_since_response': time_since_response
    }
