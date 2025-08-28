"""Claude interface detection functionality."""


def is_claude_interface_present(content: str) -> bool:
    """Check if Claude Code interface is ACTIVELY present (not just history).

    Args:
        content: Terminal content to analyze

    Returns:
        True if Claude interface is active, False otherwise
    """
    lines = content.strip().split("\n")

    # First check for ACTIVE Claude UI indicators (not just history)
    active_claude_indicators = [
        "? for shortcuts",
        "Welcome to Claude Code",
        "╭─",
        "╰─",
        "│ >",
        "Bypassing Permissions",
        "@anthropic-ai/claude-code",
    ]

    # Check for active Claude UI elements
    has_active_indicators = False
    for indicator in active_claude_indicators:
        if any(indicator in line for line in lines):
            has_active_indicators = True
            break

    # Also check for conversation patterns that indicate active Claude
    # Look for recent assistant/human exchanges with prompt boxes
    has_conversation_ui = False
    for i, line in enumerate(lines):
        if ("assistant:" in line.lower() or "human:" in line.lower()) and i < len(lines) - 3:
            # Check if there are UI elements after the conversation
            remaining_lines = lines[i + 1 :]
            if any(ui in " ".join(remaining_lines) for ui in ["╭─", "╰─", "│"]):
                has_conversation_ui = True
                break

    # If we have active indicators or conversation UI, Claude is running
    if has_active_indicators or has_conversation_ui:
        return True

    # Now check for bash prompts ONLY if no Claude indicators found
    last_few_lines = [line for line in lines[-5:] if line.strip()]
    bash_indicators = ["vscode ➜", "$ ", "# ", "bash-"]

    for line in last_few_lines:
        # Skip lines that look like Claude output showing commands
        if line.strip().startswith(">") and "claude" in line.lower():
            continue

        if line.strip().endswith(("$", "#", "%")):
            return False
        if any(indicator in line for indicator in bash_indicators):
            return False
        # Check for user@host pattern more specifically
        if "@" in line and ":" in line and line.strip().endswith(("$", "#", "~")):
            return False
    return False  # No active Claude interface detected
