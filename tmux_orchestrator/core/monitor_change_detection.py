"""Change detection algorithms for monitoring agent terminal states.

This module implements the change detection algorithms proposed in planning/change-detection.md
for more accurate agent state detection.
"""

import logging
import re
import time
from typing import Any, Callable, List


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate the Levenshtein distance between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        The minimum number of single-character edits (insertions, deletions, substitutions)
        required to change s1 into s2
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    # Create distance matrix
    previous_row = list(range(len(s2) + 1))

    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row are one character longer than s2
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def detect_active_state_levenshtein(snapshots: List[str], threshold: int = 1) -> bool:
    """Detect if terminal is actively changing using Levenshtein distance.

    Based on planning/change-detection.md:
    - Poll every 300ms for 1.2s (4 snapshots)
    - Calculate Levenshtein distance between successive polls
    - If distance > threshold, terminal is actively thinking

    Args:
        snapshots: List of terminal snapshots taken at 300ms intervals
        threshold: Minimum distance to consider as active (default: 1)

    Returns:
        True if terminal is actively changing, False otherwise
    """
    if len(snapshots) < 2:
        return False

    # Check for "Compacting conversation" indicator
    for snapshot in snapshots:
        if "Compacting conversation" in snapshot:
            return True

    # Calculate distances between successive snapshots
    for i in range(1, len(snapshots)):
        distance = levenshtein_distance(snapshots[i - 1], snapshots[i])
        if distance > threshold:
            return True

    return False


def detect_idle_with_empty_prompt(content: str) -> bool:
    """Detect if agent is idle with empty input box.

    From planning/change-detection.md:
    - Not Active (#1) & contains empty input box
    - Regex pattern: ╭─*╮\n│\\s>\\s*│\n╰─*╯

    Args:
        content: Terminal content to check

    Returns:
        True if idle with empty prompt, False otherwise
    """
    # Pattern for empty prompt box (with flexibility for box drawing chars)
    empty_prompt_pattern = r"╭[─\s]*╮\s*\n\s*│\s*>\s*│\s*\n\s*╰[─\s]*╯"
    return bool(re.search(empty_prompt_pattern, content, re.MULTILINE))


def detect_message_queued(content: str) -> bool:
    """Detect if agent has a queued/unsubmitted message.

    From planning/change-detection.md:
    - Pattern like ╭─*╮\n│\\s>\\s(.*?)│ where the group != \\s*

    Args:
        content: Terminal content to check

    Returns:
        True if message is queued, False otherwise
    """
    # Pattern for prompt box with content
    prompt_pattern = r"╭[─\s]*╮\s*\n\s*│\s*>\s*(.*?)\s*│"
    match = re.search(prompt_pattern, content, re.MULTILINE | re.DOTALL)

    if match:
        prompt_content = match.group(1).strip()
        # If there's any non-whitespace content, message is queued
        return len(prompt_content) > 0

    return False


def capture_snapshots_with_timing(
    capture_func: Callable[..., Any], target: str, count: int = 4, interval: float = 0.3
) -> List[str]:
    """Capture multiple snapshots with precise timing.

    Args:
        capture_func: Function to capture terminal content (e.g., tmux.capture_pane)
        target: Target identifier for capture
        count: Number of snapshots to capture (default: 4)
        interval: Interval between snapshots in seconds (default: 0.3)

    Returns:
        List of captured snapshots
    """
    snapshots = []
    for i in range(count):
        snapshot = capture_func(target, lines=50)
        snapshots.append(snapshot)
        if i < count - 1:
            time.sleep(interval)
    return snapshots


def compare_detection_methods(snapshots: List[str], logger: logging.Logger | None = None) -> dict[str, Any]:
    """Compare different change detection methods on the same data.

    Args:
        snapshots: List of terminal snapshots
        logger: Optional logger for debug output

    Returns:
        Dictionary with results from each method
    """
    # Current simple method (character counting)
    simple_active = False
    for i in range(1, len(snapshots)):
        if snapshots[i - 1] != snapshots[i]:
            changes = sum(1 for a, b in zip(snapshots[i - 1], snapshots[i]) if a != b)
            if changes > 1:
                simple_active = True
                break

    # Levenshtein method
    levenshtein_active = detect_active_state_levenshtein(snapshots)

    # Calculate actual distances for logging
    distances = []
    for i in range(1, len(snapshots)):
        dist = levenshtein_distance(snapshots[i - 1], snapshots[i])
        distances.append(dist)

    results = {
        "simple_method": simple_active,
        "levenshtein_method": levenshtein_active,
        "levenshtein_distances": distances,
        "methods_agree": simple_active == levenshtein_active,
    }

    if logger:
        logger.debug(f"Detection comparison: {results}")

    return results
