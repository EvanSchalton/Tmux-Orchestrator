"""Detect whether Claude Desktop or Claude Code CLI is available."""

import shutil


def detect_claude_environment():
    """Detect whether Claude Desktop or Claude Code CLI is available."""
    # Check for Claude CLI in PATH
    claude_cli_available = shutil.which("claude") is not None

    # Check for Claude Desktop using existing function
    from tmux_orchestrator.utils.claude_config import check_claude_installation

    claude_desktop_available = check_claude_installation()[0]

    return {
        "cli_available": claude_cli_available,
        "desktop_available": claude_desktop_available,
        "preferred": "cli" if claude_cli_available else "desktop",
    }
