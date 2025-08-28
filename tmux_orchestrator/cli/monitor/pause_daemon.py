"""Temporarily pause monitoring daemon for specified seconds."""

import os
import subprocess
from pathlib import Path

import click
from rich.console import Console

console = Console()


def pause_daemon(ctx: click.Context, seconds: int) -> None:
    """Temporarily pause monitoring daemon for specified seconds."""
    if seconds <= 0 or seconds > 300:
        console.print("[red]Invalid pause duration. Must be between 1-300 seconds.[/red]")
        return

    # Check if daemon is running by looking for PID file
    project_dir = Path.cwd() / ".tmux_orchestrator"
    pid_file = project_dir / "idle-monitor.pid"

    if not pid_file.exists():
        console.print("[yellow]Monitor daemon is not running[/yellow]")
        return

    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())

        # Create pause file that the idle monitor checks for
        pause_file = project_dir / "idle-monitor.pause"
        pause_file.write_text(f"paused for {seconds}s at {os.getpid()}")

        console.print(f"[green]✓ Monitor daemon (PID {pid}) paused for {seconds} seconds[/green]")

        # Schedule removal of pause file after the specified time
        # Use sh -c to run the sleep and rm command sequence
        subprocess.Popen(
            ["sh", "-c", f"sleep {seconds} && rm -f {pause_file}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    except (ProcessLookupError, ValueError, OSError) as e:
        console.print(f"[red]✗ Failed to pause monitoring daemon: {e}[/red]")
