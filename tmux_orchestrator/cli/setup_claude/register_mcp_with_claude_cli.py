"""Register MCP server with Claude Code CLI."""

import subprocess


def register_mcp_with_claude_cli():
    """Register MCP server with Claude Code CLI."""
    try:
        # Correct Claude Code CLI syntax for adding MCP server
        cmd = [
            "claude",
            "mcp",
            "add",
            "tmux-orchestrator",
            "tmux-orc",
            "server",
            "start",
            "--scope",
            "user",
            "--env",
            "TMUX_ORC_MCP_MODE=claude_code",
            "--env",
            "PYTHONUNBUFFERED=1",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return True, f"MCP server registered with Claude Code CLI (project scope)\nOutput: {result.stdout}"
        else:
            return (
                False,
                f"Registration failed (code {result.returncode})\nStderr: {result.stderr}\nStdout: {result.stdout}\nCommand: {' '.join(cmd)}",
            )
    except Exception as e:
        return False, f"CLI registration error: {e}"
