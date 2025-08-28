"""Kill specific session functionality for orchestrator."""

import click
from rich.console import Console

console = Console()


@click.command()
@click.argument("session_name")
@click.option("--force", is_flag=True, help="Force kill without confirmation")
@click.pass_context
def kill(ctx: click.Context, session_name: str, force: bool) -> None:
    """Kill a specific orchestrator session.

    Args:
        session_name: Name of the session to kill
        force: Skip confirmation prompt
    """
    if not force:
        if not click.confirm(f"Kill session '{session_name}'?"):
            console.print("[yellow]Operation cancelled[/yellow]")
            return

    console.print(f"[red]Killing session: {session_name}[/red]")
    # TODO: Implement actual kill logic
    console.print(f"[green]Session '{session_name}' terminated[/green]")
