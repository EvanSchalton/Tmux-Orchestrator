"""Team management commands."""

from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tmux_orchestrator.core.team_operations import (
    broadcast_to_team,
    get_team_status,
    list_all_teams,
)
from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


@click.group()
def team() -> None:
    """Manage teams and sessions."""
    pass


@team.command()
@click.argument('session')
@click.pass_context
def status(ctx: click.Context, session: str) -> None:
    """Show detailed team status for a session.

    SESSION: Session name to check
    """
    tmux: TMUXManager = ctx.obj['tmux']

    # Delegate to business logic
    team_status: Optional[Dict[str, Any]] = get_team_status(tmux, session)

    if not team_status:
        console.print(f"[red]✗ Session '{session}' not found[/red]")
        return

    # Display session header
    session_info: Dict[str, str] = team_status['session_info']
    attached: str = "Yes" if session_info.get('attached') == '1' else "No"
    header_text: str = (
        f"Session: {session} | "
        f"Created: {session_info.get('created', 'Unknown')} | "
        f"Attached: {attached}"
    )
    console.print(Panel(header_text, style="bold blue"))

    # Create team status table
    table: Table = Table(title=f"Team Status - {session}")
    table.add_column("Window", style="cyan", width=8)
    table.add_column("Name", style="magenta", width=20)
    table.add_column("Type", style="green", width=15)
    table.add_column("Status", style="yellow", width=12)
    table.add_column("Last Activity", style="blue", width=30)

    windows: List[Dict[str, Any]] = team_status['windows']
    for window in windows:
        table.add_row(
            window['index'],
            window['name'],
            window['type'],
            window['status'],
            window['last_activity']
        )

    # Display table
    console.print(table)

    # Show summary
    summary: Dict[str, int] = team_status['summary']
    summary_text: str = (
        f"Total Windows: {summary['total_windows']} | "
        f"Active Agents: {summary['active_agents']}"
    )
    console.print(f"\n[bold green]{summary_text}[/bold green]")


@team.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all team sessions."""
    tmux: TMUXManager = ctx.obj['tmux']

    # Delegate to business logic
    teams: List[Dict[str, Any]] = list_all_teams(tmux)

    if not teams:
        console.print("[yellow]No active sessions found[/yellow]")
        return

    table: Table = Table(title="All Team Sessions")
    table.add_column("Session", style="cyan")
    table.add_column("Windows", style="magenta")
    table.add_column("Agents", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Created", style="blue")

    for team in teams:
        table.add_row(
            team['name'],
            str(team['windows']),
            str(team['agents']),
            team['status'],
            team['created']
        )

    console.print(table)


@team.command()
@click.argument('session')
@click.argument('message')
@click.pass_context
def broadcast(ctx: click.Context, session: str, message: str) -> None:
    """Broadcast a message to all agents in a session.

    SESSION: Session name
    MESSAGE: Message to broadcast
    """
    tmux: TMUXManager = ctx.obj['tmux']

    # Delegate to business logic
    success, summary_message, results = broadcast_to_team(tmux, session, message)

    if not success:
        console.print(f"[red]✗ {summary_message}[/red]")
        return

    # Display detailed results
    for result in results:
        if result['success']:
            console.print(
                f"[green]✓ Message sent to {result['window_name']} "
                f"({result['target']})[/green]"
            )
        else:
            console.print(
                f"[red]✗ Failed to send message to {result['window_name']} "
                f"({result['target']})[/red]"
            )

    console.print(f"\n[bold]{summary_message}[/bold]")
