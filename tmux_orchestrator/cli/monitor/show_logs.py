"""Show monitoring daemon logs with enhanced formatting."""

import os
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()

# Use project directory for storage
PROJECT_DIR = str(Path.cwd() / ".tmux_orchestrator")
LOGS_DIR = f"{PROJECT_DIR}/logs"
LOG_FILE = f"{LOGS_DIR}/idle-monitor.log"


def show_logs(follow: bool, lines: int) -> None:
    """Show monitoring daemon logs with enhanced formatting."""
    if not os.path.exists(LOG_FILE):
        console.print("[yellow]No monitoring logs found[/yellow]")
        console.print(f"[dim]Expected location: {LOG_FILE}[/dim]")
        console.print("[dim]Start monitoring with: tmux-orc monitor start[/dim]")
        return

    try:
        if follow:
            subprocess.run(["tail", "-f", f"-{lines}", LOG_FILE])
        else:
            subprocess.run(["tail", f"-{lines}", LOG_FILE])
    except KeyboardInterrupt:
        console.print("\n[dim]Log following stopped[/dim]")
    except Exception as e:
        console.print(f"[red]Error reading logs: {e}[/red]")
