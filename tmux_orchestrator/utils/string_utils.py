"""String utility functions for tmux-orchestrator.

Provides reusable string manipulation and comparison functions
used across different components of the system.
"""


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
            # Cost of insertions, deletions, and substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)

            current_row.append(min(insertions, deletions, substitutions))

        previous_row = current_row

    return previous_row[-1]


def efficient_change_score(text1: str, text2: str) -> int:
    """Calculate efficient change score between two texts for terminal monitoring.

    Optimized for terminal content where changes typically happen at the end.
    Uses line count differences and character changes in recent content.

    Args:
        text1: Earlier text content
        text2: Later text content

    Returns:
        Change score (higher = more changes)
    """
    lines1 = text1.strip().split("\n")
    lines2 = text2.strip().split("\n")

    score = 0

    # 1. Line count difference (new output adds lines)
    line_diff = abs(len(lines1) - len(lines2))
    score += line_diff * 2  # Weight line changes heavily

    # 2. Last few lines comparison (where new activity appears)
    last_5_text1 = "\n".join(lines1[-5:]) if lines1 else ""
    last_5_text2 = "\n".join(lines2[-5:]) if lines2 else ""

    if last_5_text1 != last_5_text2:
        # Simple character difference count
        char_diff = abs(len(last_5_text1) - len(last_5_text2))
        char_diff += sum(1 for a, b in zip(last_5_text1, last_5_text2) if a != b)
        score += char_diff

    return score
