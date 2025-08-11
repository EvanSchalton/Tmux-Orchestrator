"""Helper functions for agent status monitoring.

This module contains extracted helper functions from the monitor._check_agent_status
method to improve testability and maintainability.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List


class AgentState(Enum):
    """Enumeration of possible agent states."""

    ACTIVE = "active"  # Working normally (was healthy/active/starting)
    CRASHED = "crashed"  # Claude not running
    ERROR = "error"  # Has error indicators
    IDLE = "idle"  # Claude running but not doing anything
    MESSAGE_QUEUED = "message_queued"  # Has unsubmitted message


def is_claude_interface_present(content: str) -> bool:
    """Check if Claude Code interface is ACTIVELY present (not just history).

    Args:
        content: Terminal content to analyze

    Returns:
        True if Claude interface is active, False otherwise
    """
    # Check for bash prompt indicators (Claude crashed)
    lines = content.strip().split("\n")
    last_few_lines = [line for line in lines[-5:] if line.strip()]

    # Bash prompt patterns indicate Claude is NOT running
    bash_indicators = ["vscode ➜", "$ ", "# ", "bash-"]
    for line in last_few_lines:
        if line.strip().endswith(("$", "#", ">", "%")):
            return False
        if any(indicator in line for indicator in bash_indicators):
            return False
        # Check for user@host pattern more specifically
        if "@" in line and ":" in line and line.strip().endswith(("$", "#", "~")):
            return False

    # Claude UI indicators mean Claude IS running
    claude_indicators = [
        "? for shortcuts",
        "Welcome to Claude Code",
        "╭─",
        "╰─",
        "│ >",
        "assistant:",
        "Human:",
        "Bypassing Permissions",
        "@anthropic-ai/claude-code",
    ]
    return any(indicator in content for indicator in claude_indicators)


def detect_agent_state(content: str) -> AgentState:
    """Detect agent state from terminal content.

    Args:
        content: Terminal content to analyze

    Returns:
        AgentState enum value
    """
    # Check for crashes - no Claude interface present
    if not is_claude_interface_present(content):
        if _has_crash_indicators(content):
            return AgentState.CRASHED
        # Check for bash prompt specifically
        lines = content.strip().split("\n")
        last_few_lines = [line for line in lines[-5:] if line.strip()]
        for line in last_few_lines:
            if line.strip().endswith(("$", "#", ">", "%")):
                return AgentState.CRASHED
            if any(indicator in line for indicator in ["vscode ➜", "$ ", "# ", "bash-", "@"]):
                return AgentState.CRASHED
        return AgentState.ERROR

    # Check for errors
    if _has_error_indicators(content):
        return AgentState.ERROR

    # Check for queued messages
    if has_unsubmitted_message(content):
        return AgentState.MESSAGE_QUEUED

    # Default to active (idle detection needs snapshots)
    return AgentState.ACTIVE


def has_unsubmitted_message(content: str) -> bool:
    """Check if agent has unsubmitted message in Claude prompt.

    Args:
        content: Terminal content to analyze

    Returns:
        True if there's an unsubmitted message, False otherwise
    """
    lines = content.strip().split("\n")

    # Look for thinking indicators - if Claude is thinking, there's no unsubmitted message
    # Common patterns: "· Thinking...", "· Divining...", "· Pondering...", etc.
    for line in lines:
        if "💭 Thinking..." in line or "Thinking..." in line:
            return False
        # Check for the "· Word..." pattern that indicates active processing
        if "·" in line and "…" in line:
            return False

    # Find the last prompt box (most recent one)
    last_prompt_start = -1
    last_prompt_end = -1

    for i, line in enumerate(lines):
        if "╭─" in line:  # Any box that starts with this
            last_prompt_start = i
        elif "╰─" in line and last_prompt_start != -1:
            last_prompt_end = i

    # If we found a complete prompt box, check only within it
    if last_prompt_start != -1 and last_prompt_end != -1:
        for i in range(last_prompt_start, last_prompt_end + 1):
            line = lines[i]
            if "│ >" in line or "│\xa0>" in line:
                # Extract content after the prompt marker
                if "│ >" in line:
                    prompt_content = line.split("│ >", 1)[1]
                elif "│\xa0>" in line:
                    prompt_content = line.split("│\xa0>", 1)[1]
                else:
                    continue

                # Remove the closing │ if present
                if "│" in prompt_content:
                    prompt_content = prompt_content.rsplit("│", 1)[0]
                # Also handle non-breaking spaces in content
                prompt_content = prompt_content.replace("\xa0", " ")

                if prompt_content.strip():
                    return True

    return False


def is_terminal_idle(snapshots: List[str]) -> bool:
    """Check if terminal is idle based on multiple snapshots.

    DEPRECATED: This functionality is now integrated into _check_agent_status

    Args:
        snapshots: List of terminal content snapshots taken over time

    Returns:
        True if terminal content is effectively unchanged, False otherwise
    """
    if len(snapshots) < 2:
        return False

    # Compare each snapshot to the first one
    for i in range(1, len(snapshots)):
        distance = _calculate_change_distance(snapshots[0], snapshots[i])
        if distance > 1:  # Meaningful change detected
            return False

    return True


def needs_recovery(state: AgentState) -> bool:
    """Determine if agent needs recovery based on state.

    Args:
        state: Current agent state

    Returns:
        True if recovery is needed, False otherwise
    """
    return state in [AgentState.CRASHED, AgentState.ERROR]


def should_notify_pm(state: AgentState, target: str, notification_history: Dict[str, datetime]) -> bool:
    """Determine if PM should be notified about agent state.

    Args:
        state: Current agent state
        target: Agent target identifier
        notification_history: History of notifications sent

    Returns:
        True if PM should be notified, False otherwise
    """
    # Always notify for crashes and errors (with cooldown)
    if state in [AgentState.CRASHED, AgentState.ERROR]:
        # 5 minute cooldown for crash/error notifications
        last_notified = notification_history.get(f"crash_{target}")
        if last_notified:
            time_since = datetime.now() - last_notified
            if time_since < timedelta(minutes=5):
                return False
        return True

    # Notify for idle agents with cooldown
    if state == AgentState.IDLE:
        # 10 minute cooldown for idle notifications
        last_notified = notification_history.get(target)
        if last_notified:
            time_since = datetime.now() - last_notified
            if time_since < timedelta(minutes=10):
                return False
        return True

    # Don't notify for healthy/active agents or messages queued
    return False


# Private helper functions


def _calculate_change_distance(text1: str, text2: str) -> int:
    """Calculate simple change distance between two texts.

    Args:
        text1: First text to compare
        text2: Second text to compare

    Returns:
        Number of character differences
    """
    if abs(len(text1) - len(text2)) > 1:
        return 999

    differences = 0
    for i, (c1, c2) in enumerate(zip(text1, text2)):
        if c1 != c2:
            differences += 1
            if differences > 1:
                return differences

    differences += abs(len(text1) - len(text2))
    return differences


def _has_crash_indicators(content: str) -> bool:
    """Check for crash indicators in content.

    Args:
        content: Terminal content to analyze

    Returns:
        True if crash indicators are found, False otherwise
    """
    crash_indicators = [
        "claude: command not found",
        "segmentation fault",
        "core dumped",
        "killed",
        "Traceback (most recent call last)",
        "ModuleNotFoundError",
        "Process finished with exit code",
        "[Process completed]",
        "Terminated",
    ]
    content_lower = content.lower()
    return any(indicator.lower() in content_lower for indicator in crash_indicators)


def _has_error_indicators(content: str) -> bool:
    """Check for error indicators in content.

    Args:
        content: Terminal content to analyze

    Returns:
        True if error indicators are found, False otherwise
    """
    error_indicators = [
        "network error occurred",
        "timeout error occurred",
        "permission denied",
        "Error:",
        "connection lost",
    ]
    content_lower = content.lower()
    return any(indicator.lower() in content_lower for indicator in error_indicators)
