"""Agent state detection functionality."""

from .constants import AgentState
from .interface_detector import is_claude_interface_present


def detect_agent_state(content: str) -> AgentState:
    """Detect agent state from terminal content.

    Args:
        content: Terminal content to analyze

    Returns:
        AgentState enum value
    """
    # Check for rate limit first (it may not have Claude interface)
    # Be flexible - just check for the main error message
    if "claude usage limit reached" in content.lower():
        return AgentState.RATE_LIMITED

    # Check for crashes - no Claude interface present
    if not is_claude_interface_present(content):
        if _has_crash_indicators(content):
            return AgentState.CRASHED
        # Check for bash prompt specifically
        lines = content.strip().split("\n")
        last_few_lines = [line for line in lines[-5:] if line.strip()]
        for line in last_few_lines:
            # Check for shell prompt endings
            if line.strip().endswith(("$", "#", ">", "%", "$ ", "# ", "> ", "% ")):
                return AgentState.CRASHED
            # Check for specific shell prompt patterns (removed @ which was too broad)
            if any(indicator in line for indicator in ["vscode ➜", "bash-"]):
                return AgentState.CRASHED
        return AgentState.ERROR

    # Check for errors
    if _has_error_indicators(content):
        return AgentState.ERROR

    # Use the new Claude state detection to handle fresh instances
    claude_state = detect_claude_state(content)

    if claude_state == "fresh":
        return AgentState.FRESH
    elif claude_state == "unsubmitted":
        return AgentState.MESSAGE_QUEUED

    # Default to active (idle detection needs snapshots)
    return AgentState.ACTIVE


def detect_claude_state(content: str) -> str:
    """Detect the state of Claude interface.

    Returns:
        'fresh' - Fresh Claude instance with placeholder text
        'active' - Claude with context/conversation
        'unsubmitted' - Has actual unsubmitted user input
        'idle' - No input, no placeholder
    """

    # CRITICAL: Check for actual unsubmitted content FIRST
    # This prevents auto-submit on messages that look like placeholders
    if has_unsubmitted_message(content):
        return "unsubmitted"

    # Now check for fresh Claude instance indicators
    # Only check if the prompt is truly empty or has specific placeholder text
    lines = content.strip().split("\n")

    # Look for the actual Claude prompt box
    prompt_content = None
    for i, line in enumerate(lines):
        if "│ >" in line or "│\xa0>" in line:
            # Extract content after the prompt marker
            if "│ >" in line:
                prompt_content = line.split("│ >", 1)[1]
            elif "│\xa0>" in line:
                prompt_content = line.split("│\xa0>", 1)[1]

            # Remove closing │ if present
            if prompt_content and "│" in prompt_content:
                prompt_content = prompt_content.rsplit("│", 1)[0]
            if prompt_content:
                prompt_content = prompt_content.replace("\xa0", " ").strip()
            break

    # Check if we have a truly fresh instance
    if prompt_content is not None and prompt_content == "":
        # Empty prompt - check for fresh welcome message
        if "Welcome to Claude Code" in content and "What would you like me to help you with" in content:
            return "fresh"

    # More specific fresh patterns - only match exact help message
    if prompt_content == 'Try "help" for more information':
        return "fresh"

    # Check for active conversation
    if is_claude_interface_present(content):
        return "active"

    return "idle"


def is_pm_busy(content: str) -> bool:
    """Check if PM agent is busy and should not be interrupted.

    Args:
        content: Terminal content to analyze

    Returns:
        True if PM is busy, False otherwise
    """
    # Check for busy indicators
    busy_indicators = [
        "thinking",
        "processing",
        "working on",
        "analyzing",
        "reviewing",
    ]

    content_lower = content.lower()
    return any(indicator in content_lower for indicator in busy_indicators)


def has_unsubmitted_message(content: str) -> bool:
    """Check if there's an unsubmitted message in the Claude prompt.

    Args:
        content: Terminal content to analyze

    Returns:
        True if there's an unsubmitted message, False otherwise
    """
    lines = content.strip().split("\n")

    # Look for prompt content that appears to be actual user input
    for line in lines:
        if "│ >" in line or "│\xa0>" in line:
            # Extract content after prompt marker
            if "│ >" in line:
                prompt_content = line.split("│ >", 1)[1]
            else:
                prompt_content = line.split("│\xa0>", 1)[1]

            # Remove closing │ if present
            if prompt_content and "│" in prompt_content:
                prompt_content = prompt_content.rsplit("│", 1)[0]

            if prompt_content:
                prompt_content = prompt_content.replace("\xa0", " ").strip()

                # Check if this looks like real user input (not placeholder)
                if (
                    len(prompt_content) > 5
                    and not prompt_content.startswith("Try ")
                    and prompt_content != 'Try "help" for more information'
                ):
                    return True

    return False


def _has_crash_indicators(content: str) -> bool:
    """Check if content has crash indicators.

    Args:
        content: Terminal content to analyze

    Returns:
        True if crash indicators found, False otherwise
    """
    crash_indicators = [
        "command not found",
        "segmentation fault",
        "traceback",
        "error:",
        "exception:",
        "bash:",
        "zsh:",
    ]

    content_lower = content.lower()
    return any(indicator in content_lower for indicator in crash_indicators)


def _has_error_indicators(content: str) -> bool:
    """Check if content has error indicators.

    Args:
        content: Terminal content to analyze

    Returns:
        True if error indicators found, False otherwise
    """
    error_indicators = [
        "error",
        "failed",
        "exception",
        "timeout",
        "connection refused",
        "permission denied",
    ]

    content_lower = content.lower()
    return any(indicator in content_lower for indicator in error_indicators)
