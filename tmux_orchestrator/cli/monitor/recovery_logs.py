"""Show agent recovery daemon logs."""

import os
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()

# Use project directory for storage
PROJECT_DIR = str(Path.cwd() / ".tmux_orchestrator")
LOGS_DIR = f"{PROJECT_DIR}/logs"
RECOVERY_LOG_FILE = f"{LOGS_DIR}/recovery.log"


def show_recovery_logs(follow: bool, lines: int) -> None:
    """Show agent recovery daemon logs."""
    if not os.path.exists(RECOVERY_LOG_FILE):
        console.print("[yellow]No recovery logs found[/yellow]")
        console.print(f"[dim]Expected location: {RECOVERY_LOG_FILE}[/dim]")
        console.print("[dim]Start recovery with: tmux-orc monitor recovery-start[/dim]")
        return

    try:
        if follow:
            subprocess.run(["tail", "-f", f"-{lines}", RECOVERY_LOG_FILE])
        else:
            subprocess.run(["tail", f"-{lines}", RECOVERY_LOG_FILE])
    except KeyboardInterrupt:
        console.print("\n[dim]Log following stopped[/dim]")
    except Exception as e:
        console.print(f"[red]Error reading recovery logs: {e}[/red]")
