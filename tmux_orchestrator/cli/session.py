"""Session management commands for the orchestrator.

This module provides commands for managing tmux sessions used by the orchestrator.
"""

import json as json_module
import os
import subprocess

import click
from rich.console import Console
from rich.table import Table

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


@click.group()
def session() -> None:
    """Manage tmux sessions for the orchestrator.

    Sessions are the top-level containers in tmux that contain one or more windows.
    The orchestrator uses sessions to organize different agents and their workspaces.

    Examples:
        List all tmux sessions:
        $ tmux-orc session list

        List sessions in JSON format:
        $ tmux-orc session list --json

        Attach to an existing session:
        $ tmux-orc session attach my-session

        Attach to a session in read-only mode:
        $ tmux-orc session attach my-session --read-only
    """
    pass


@session.command()
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def list(ctx: click.Context, json_output: bool) -> None:
    """List all tmux sessions with details.

    Shows all tmux sessions including their name, number of windows,
    attached status, and creation time.

    Examples:
        List all sessions:
        $ tmux-orc session list

        Get machine-readable output:
        $ tmux-orc session list --json
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    try:
        sessions = tmux.list_sessions()

        if not sessions:
            if json_output:
                console.print(json_module.dumps({"sessions": [], "count": 0}, indent=2))
            else:
                console.print("[yellow]No tmux sessions found[/yellow]")
            return

        if json_output:
            # Add window count for each session
            for session in sessions:
                windows = tmux.list_windows(session["name"])
                session["window_count"] = str(len(windows))  # Convert to string to match dict type

            result = {"sessions": sessions, "count": len(sessions)}
            console.print(json_module.dumps(result, indent=2))
            return

        # Create rich table for display
        table = Table(title="Tmux Sessions")
        table.add_column("Session Name", style="cyan", no_wrap=True)
        table.add_column("Windows", justify="right")
        table.add_column("Attached", justify="center")
        table.add_column("Created", style="dim")

        for session_info in sessions:
            session_name = session_info["name"]
            windows = tmux.list_windows(session_name)
            window_count = str(len(windows))  # Convert to string for table display
            attached = "[green]✓[/green]" if session_info.get("attached", False) else "[dim]✗[/dim]"
            created = session_info.get("created", "Unknown")

            table.add_row(session_name, window_count, attached, created)

        console.print(table)
        console.print(f"\n[blue]Total sessions: {len(sessions)}[/blue]")

    except Exception as e:
        error_msg = f"Failed to list sessions: {str(e)}"
        if json_output:
            console.print(json_module.dumps({"error": error_msg}, indent=2))
        else:
            console.print(f"[red]✗ {error_msg}[/red]")


@session.command()
@click.argument("session_name")
@click.option("--read-only", is_flag=True, help="Attach in read-only mode")
@click.pass_context
def attach(ctx: click.Context, session_name: str, read_only: bool) -> None:
    """Attach to an existing tmux session.

    Attaches to the specified tmux session. If the session doesn't exist,
    an error will be displayed.

    Arguments:
        SESSION_NAME: Name of the tmux session to attach to

    Examples:
        Attach to a session:
        $ tmux-orc session attach my-session

        Attach in read-only mode:
        $ tmux-orc session attach my-session --read-only
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Check if session exists
    if not tmux.has_session(session_name):
        console.print(f"[red]✗ Session '{session_name}' does not exist[/red]")
        console.print("\n[yellow]Available sessions:[/yellow]")

        sessions = tmux.list_sessions()
        if sessions:
            for session in sessions:
                console.print(f"  - {session['name']}")
        else:
            console.print("  [dim]No sessions available[/dim]")
        return

    # Build attach command
    cmd = ["tmux", "attach-session", "-t", session_name]
    if read_only:
        cmd.extend(["-r"])

    try:
        # Check if we're already in a tmux session
        in_tmux = os.environ.get("TMUX") is not None

        if in_tmux:
            console.print(
                f"[yellow]Already inside a tmux session. Use 'tmux switch-client -t {session_name}' instead[/yellow]"
            )
            return

        console.print(f"[green]✓ Attaching to session '{session_name}'...[/green]")

        # Use subprocess to attach (this will replace the current process)
        subprocess.run(cmd)

    except Exception as e:
        console.print(f"[red]✗ Failed to attach to session: {str(e)}[/red]")
