"""Terminal content analysis functionality."""


def is_terminal_idle(snapshots: list[str]) -> bool:
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
        distance = calculate_change_distance(snapshots[0], snapshots[i])
        if distance > 1:  # Meaningful change detected
            return False

    return True


def calculate_change_distance(text1: str, text2: str) -> int:
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


def has_crash_indicators(content: str) -> bool:
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


def has_error_indicators(content: str) -> bool:
    """Check for error indicators in content.

    Args:
        content: Terminal content to analyze

    Returns:
        True if error indicators are found, False otherwise
    """
    error_indicators = [
        "Error:",
        "error occurred",
        "failed to",
        "connection refused",
        "timeout",
        "permission denied",
        "no such file",
        "cannot find",
        "invalid",
        "unexpected",
        "authentication failed",
        "network error",
    ]

    content_lower = content.lower()
    return any(indicator.lower() in content_lower for indicator in error_indicators)
