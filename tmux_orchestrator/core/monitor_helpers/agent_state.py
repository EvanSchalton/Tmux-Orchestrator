"""Agent state detection and analysis functions."""

from datetime import datetime

from .claude_detection import (
    detect_claude_state,
    has_crash_indicators,
    has_error_indicators,
    is_claude_interface_present,
)
from .state_types import AgentState


def detect_agent_state(content: str) -> AgentState:
    """Analyze pane content to determine agent state.

    Implements comprehensive state detection with priority ordering:
    1. Rate limit (highest priority - blocks all operations)
    2. Crashed (needs immediate recovery)
    3. Error (needs investigation)
    4. Message queued (user action pending)
    5. Fresh (needs initialization)
    6. Idle (available but inactive)
    7. Active (working normally)

    Args:
        content: Terminal/pane content to analyze

    Returns:
        AgentState enum value representing detected state
    """
    if not content:
        return AgentState.CRASHED

    content_lower = content.lower()

    # Priority 1: Rate limit detection
    rate_limit_indicators = [
        "rate limit",
        "rate_limit",
        "quota exceeded",
        "too many requests",
        "429",  # HTTP status code for rate limit
        "rate-limited",
        "api limit",
    ]
    if any(indicator in content_lower for indicator in rate_limit_indicators):
        return AgentState.RATE_LIMITED

    # Priority 2: Crash detection
    if has_crash_indicators(content) or not is_claude_interface_present(content):
        # Double-check: might just be a cleared screen
        if len(content.strip()) < 50 and not any(word in content_lower for word in ["error", "failed", "crash"]):
            # Might be fresh/cleared, not crashed
            return AgentState.FRESH
        return AgentState.CRASHED

    # Priority 3: Error detection
    if has_error_indicators(content):
        return AgentState.ERROR

    # Priority 4: Unsubmitted message detection
    if has_unsubmitted_message(content):
        return AgentState.MESSAGE_QUEUED

    # Priority 5: Fresh instance detection
    claude_state = detect_claude_state(content)
    if claude_state == "loading" or "welcome to claude" in content_lower:
        return AgentState.FRESH

    # Priority 6: Idle detection
    if claude_state == "waiting":
        # Check if actually idle (no recent activity)
        idle_indicators = [
            "waiting for",
            "ready for",
            "awaiting",
            "standing by",
            "no current task",
            "task complete",
            "what would you like",
        ]
        if any(indicator in content_lower for indicator in idle_indicators):
            return AgentState.IDLE

        # Check for Claude Code idle state (at prompt with no pending work)
        if "│" in content and content.strip().endswith("│"):
            return AgentState.IDLE

    # Default: Active state
    return AgentState.ACTIVE


def has_unsubmitted_message(content: str) -> bool:
    """Check if there's an unsubmitted message in the input area.

    Detects when a user has typed a message but hasn't submitted it yet.
    This is important to avoid interfering with user input.

    Patterns detected:
    - Text after 'Human:' prompt (Claude AI)
    - Text after '│ >' prompt (Claude Code)
    - Multi-line input in progress
    - Partial commands or messages

    Args:
        content: Pane content to check

    Returns:
        True if unsubmitted message is detected
    """
    if not content:
        return False

    lines = content.strip().split("\n")
    if not lines:
        return False

    last_line = lines[-1]

    # Claude AI text interface - check for text after Human: prompt
    if "Human:" in last_line:
        after_prompt = last_line.split("Human:")[-1].strip()
        if after_prompt and after_prompt not in ["", " ", ">"]:
            return True

    # Claude Code interface - check for text after prompt
    if "│" in last_line:
        # Extract content between │ characters
        parts = last_line.split("│")
        if len(parts) >= 2:
            # Get the content area (usually the middle part)
            content_area = parts[1] if len(parts) > 2 else parts[-1]
            # Remove the prompt character and check for content
            content_area = content_area.replace(">", "").strip()
            if content_area:
                return True

    # Check for multi-line input indicators
    multiline_indicators = ["...", ">>>", "```", '"""', "'''"]
    for indicator in multiline_indicators:
        if indicator in content:
            # Might be in the middle of multi-line input
            return True

    return False


def is_terminal_idle(snapshots: list[str]) -> bool:
    """Check if terminal appears idle based on multiple snapshots.

    Compares multiple snapshots to detect if the terminal is truly idle
    or just appears idle momentarily.

    Args:
        snapshots: List of pane content snapshots over time

    Returns:
        True if terminal appears consistently idle
    """
    if len(snapshots) < 2:
        return False

    # Check if all snapshots show idle state
    idle_count = 0
    for snapshot in snapshots:
        state = detect_agent_state(snapshot)
        if state in [AgentState.IDLE, AgentState.FRESH]:
            idle_count += 1

    # Consider idle if majority of snapshots show idle
    return idle_count >= len(snapshots) * 0.7


def needs_recovery(state: AgentState) -> bool:
    """Determine if an agent state requires recovery action.

    Args:
        state: Current agent state

    Returns:
        True if recovery action is needed
    """
    recovery_states = [AgentState.CRASHED, AgentState.ERROR, AgentState.RATE_LIMITED]
    return state in recovery_states


def should_notify_pm(state: AgentState, target: str, notification_history: dict[str, datetime]) -> bool:
    """Determine if PM should be notified about agent state.

    Implements notification throttling to prevent spam while ensuring
    critical issues are communicated promptly.

    Args:
        state: Current agent state
        target: Agent identifier (session:window)
        notification_history: Dictionary tracking last notification times

    Returns:
        True if PM should be notified
    """
    from datetime import timedelta

    # States that require notification
    notify_states = [AgentState.CRASHED, AgentState.ERROR, AgentState.RATE_LIMITED]

    if state not in notify_states:
        return False

    # Check notification history for throttling
    last_notification = notification_history.get(target)
    if last_notification:
        time_since = datetime.now() - last_notification

        # Different cooldowns for different states
        if state == AgentState.CRASHED:
            cooldown = timedelta(minutes=5)
        elif state == AgentState.ERROR:
            cooldown = timedelta(minutes=10)
        elif state == AgentState.RATE_LIMITED:
            cooldown = timedelta(minutes=30)
        else:
            cooldown = timedelta(minutes=15)

        if time_since < cooldown:
            return False

    return True


def should_notify_continuously_idle(target: str, notification_history: dict[str, datetime]) -> bool:
    """Check if continuous idle state warrants PM notification.

    Args:
        target: Agent identifier
        notification_history: Notification tracking dictionary

    Returns:
        True if PM should be notified about continuous idleness
    """
    from datetime import timedelta

    last_idle_notification = notification_history.get(f"{target}_idle")
    if last_idle_notification:
        time_since = datetime.now() - last_idle_notification
        # Notify every 30 minutes about continuous idleness
        return time_since >= timedelta(minutes=30)

    # First idle detection - notify immediately
    return True
