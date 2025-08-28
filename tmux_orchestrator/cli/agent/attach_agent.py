"""Attach to an agent's terminal for direct interaction."""

import subprocess

import click
from rich.console import Console

console = Console()


def attach_agent(ctx: click.Context, target: str) -> None:
    """Attach to an agent's terminal for direct interaction."""
    try:
        # Parse target to get session and window
        session_window = target.split(".")
        session_window_part = session_window[0]

        # Execute tmux attach
        subprocess.run(["tmux", "attach-session", "-t", session_window_part], check=True)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to attach to {target}: {e}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error attaching to {target}: {e}[/red]")
