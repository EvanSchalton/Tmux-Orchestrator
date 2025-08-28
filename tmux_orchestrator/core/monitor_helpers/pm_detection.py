"""PM-specific detection and busy state analysis."""

import re


def is_pm_busy(content: str) -> bool:
    """Check if PM appears busy based on pane content.

    Detection strategy:
    1. Check for active command execution
    2. Look for ongoing operations
    3. Detect interactive sessions
    4. Identify processing indicators

    Args:
        content: PM pane content to analyze

    Returns:
        True if PM appears busy
    """
    if not content:
        return False

    content_lower = content.lower()

    # Active command indicators
    command_indicators = [
        "spawning",
        "executing",
        "running",
        "processing",
        "building",
        "compiling",
        "deploying",
        "installing",
        "downloading",
        "uploading",
    ]

    if any(indicator in content_lower for indicator in command_indicators):
        return True

    # Check for active tmux-orc commands
    tmux_orc_active = [
        "tmux-orc spawn",
        "tmux-orc execute",
        "tmux-orc deploy",
        "tmux-orc team",
        "monitoring daemon",
        "recovery in progress",
    ]

    if any(cmd in content_lower for cmd in tmux_orc_active):
        return True

    # Interactive session indicators
    interactive_indicators = [
        ">>> ",  # Python REPL
        "ipython",
        "jupyter",
        "debugger",
        "pdb",
        "(y/n)",
        "[y/n]",
        "continue?",
        "confirm",
        "password:",
    ]

    if any(indicator in content_lower for indicator in interactive_indicators):
        return True

    # Progress indicators
    progress_patterns = [
        r"\d+%",  # Percentage progress
        r"\[\s*=+\s*\]",  # Progress bar
        r"step \d+ of \d+",
        r"\d+/\d+",  # X of Y pattern
        "eta:",
        "elapsed:",
        "remaining:",
    ]

    if any(re.search(pattern, content_lower) for pattern in progress_patterns):
        return True

    # Check for unfinished operations
    unfinished_patterns = [
        r"\.\.\.$",  # Ellipsis at end
        r"waiting for",
        r"in progress",
        r"pending",
        r"queued",
    ]

    if any(re.search(pattern, content_lower) for pattern in unfinished_patterns):
        return True

    return False


def calculate_change_distance(text1: str, text2: str) -> int:
    """Calculate a simple change distance between two texts.

    Uses line-based comparison for efficiency with terminal output.

    Args:
        text1: First text snapshot
        text2: Second text snapshot

    Returns:
        Number of changed lines
    """
    if not text1 or not text2:
        return max(len(text1), len(text2))

    lines1 = text1.strip().split("\n")
    lines2 = text2.strip().split("\n")

    # Quick check for identical content
    if lines1 == lines2:
        return 0

    # Count different lines
    max_lines = max(len(lines1), len(lines2))
    min_lines = min(len(lines1), len(lines2))

    changes = 0

    # Count differences in overlapping lines
    for i in range(min_lines):
        if lines1[i] != lines2[i]:
            changes += 1

    # Count additional lines as changes
    changes += max_lines - min_lines

    return changes
