"""Attempt to restart Claude Code if it's running."""

import platform
import subprocess

from rich.console import Console

console = Console()


def restart_claude_if_running() -> bool:
    """Attempt to restart Claude Code if it's running.

    Returns:
        True if restart was attempted, False if Claude not found running
    """
    system = platform.system().lower()

    try:
        if system == "windows":
            # Check if Claude process is running
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Claude.exe"], capture_output=True, text=True, timeout=5
            )
            if "Claude.exe" in result.stdout:
                # Kill Claude process
                subprocess.run(["taskkill", "/F", "/IM", "Claude.exe"], capture_output=True, timeout=5)
                console.print("[yellow]Terminated Claude Code process[/yellow]")
                return True

        elif system in ["darwin", "linux"]:
            # Check if Claude process is running (generic approach)
            result = subprocess.run(["pgrep", "-f", "[Cc]laude"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        subprocess.run(["kill", pid], capture_output=True, timeout=5)
                    except Exception:
                        pass
                console.print("[yellow]Terminated Claude Code process[/yellow]")
                return True

    except Exception as e:
        console.print(f"[dim]Could not check/restart Claude: {e}[/dim]")

    return False
