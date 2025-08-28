"""Claude interface detection utilities."""

import re


def is_claude_interface_present(content: str) -> bool:
    """Check if Claude interface is present in the pane content.

    This function detects:
    1. Claude AI text interface (Human:/Assistant: prompts)
    2. Claude Code interface (│ prompt with box drawing)
    3. Claude interface loading states
    4. Claude-specific UI elements

    Args:
        content: Pane content to check

    Returns:
        True if Claude interface is detected
    """
    if not content:
        return False

    # Claude AI text interface patterns
    if any(pattern in content for pattern in ["Human:", "Assistant:", "H:", "A:"]):
        return True

    # Claude Code interface patterns (box drawing characters)
    claude_code_patterns = [
        "│",  # Box drawing character used in Claude Code
        "├",  # Left junction
        "└",  # Bottom corner
        "┌",  # Top corner
        "─",  # Horizontal line
        "Welcome to Claude",  # Welcome message
        "Claude 3",  # Model identifier
        "Anthropic",  # Company name
    ]

    if any(pattern in content for pattern in claude_code_patterns):
        # Additional check: Claude Code has a specific prompt pattern
        if "│" in content and (">" in content or "..." in content):
            return True
        # Check for welcome/initialization messages
        if "Welcome" in content or "Claude" in content:
            return True

    # Check for Claude-specific error messages or states
    claude_states = [
        "Rate limit",
        "quota exceeded",
        "API error",
        "Claude is thinking",
        "Processing",
        "Generating response",
    ]

    if any(state.lower() in content.lower() for state in claude_states):
        return True

    return False


def detect_claude_state(content: str) -> str:
    """Detect specific Claude interface state.

    Returns more specific state information about Claude interface:
    - 'active': Actively processing or recently responded
    - 'waiting': At prompt, waiting for input
    - 'loading': Interface loading or initializing
    - 'error': Error state detected
    - 'absent': No Claude interface detected

    Args:
        content: Pane content to analyze

    Returns:
        String indicating Claude state
    """
    if not content:
        return "absent"

    content_lower = content.lower()

    # Check for error states first (highest priority)
    error_indicators = ["error", "failed", "exception", "traceback", "rate limit", "quota exceeded"]
    if any(indicator in content_lower for indicator in error_indicators):
        return "error"

    # Check for loading/initializing states
    loading_indicators = ["loading", "initializing", "starting", "connecting", "welcome to claude"]
    if any(indicator in content_lower for indicator in loading_indicators):
        return "loading"

    # Check for active processing
    active_indicators = [
        "generating",
        "processing",
        "thinking",
        "assistant:",
        "a:",
        "│ assistant",
        "├─",  # Active response in Claude Code
    ]
    if any(indicator in content_lower for indicator in active_indicators):
        return "active"

    # Check for waiting at prompt
    if is_claude_interface_present(content):
        # Claude AI text interface waiting
        if content.strip().endswith("Human:") or content.strip().endswith("H:"):
            return "waiting"

        # Claude Code interface waiting
        if "│" in content and content.strip().endswith("│"):
            # Check if there's a prompt indicator
            lines = content.strip().split("\n")
            if lines and "│" in lines[-1] and (">" in lines[-1] or lines[-1].strip().endswith("│")):
                return "waiting"

    # If Claude interface is present but no specific state detected
    if is_claude_interface_present(content):
        return "waiting"

    return "absent"


def has_crash_indicators(content: str) -> bool:
    """Check if content contains crash indicators.

    Args:
        content: Pane content to check

    Returns:
        True if crash indicators are present
    """
    crash_patterns = [
        r"killed.*claude",
        r"terminated.*claude",
        r"process.*died",
        r"segmentation fault",
        r"core dumped",
        r"fatal error",
        r"panic:",
        r"crashed",
        r"connection.*lost",
        r"session.*ended",
    ]

    content_lower = content.lower()
    return any(re.search(pattern, content_lower) for pattern in crash_patterns)


def has_error_indicators(content: str) -> bool:
    """Check if content contains error indicators.

    Detects various error states including:
    - Python tracebacks and exceptions
    - API errors and rate limits
    - System errors
    - Application-specific errors

    Args:
        content: Pane content to check

    Returns:
        True if error indicators are present
    """
    # Simple string patterns
    error_keywords = [
        "error:",
        "error ",
        "failed:",
        "failed ",
        "failure:",
        "failure ",
        "exception:",
        "exception ",
        "traceback",
        "fatal:",
        "fatal ",
        "critical:",
        "critical ",
        "api error",
        "rate limit",
        "quota exceeded",
        "permission denied",
        "access denied",
        "not found:",
        "404:",
        "500:",
        "503:",
    ]

    content_lower = content.lower()
    if any(keyword in content_lower for keyword in error_keywords):
        return True

    # Regex patterns for more complex error detection
    error_patterns = [
        r"error\s*:",
        r"failed\s*:",
        r"exception\s*:",
        r"\w+Error:",  # Python errors like ValueError:
        r"\w+Exception:",  # Python exceptions
        r"line\s+\d+.*error",  # Line number errors
        r"at\s+line\s+\d+",  # Stack trace patterns
        r"file\s+.*line\s+\d+",  # Python traceback
        r"\[\s*error\s*\]",  # [error] log format
        r"\[\s*fatal\s*\]",  # [fatal] log format
        r"\[\s*critical\s*\]",  # [critical] log format
    ]

    return any(re.search(pattern, content_lower) for pattern in error_patterns)
