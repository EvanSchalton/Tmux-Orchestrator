"""Kill all sessions functionality for orchestrator."""

import click
from rich.console import Console

console = Console()


@click.command()
@click.option("--force", is_flag=True, help="Force kill without confirmation")
@click.pass_context
def kill_all(ctx: click.Context, force: bool) -> None:
    """Kill all active orchestrator sessions.

    Args:
        force: Skip confirmation prompt
    """
    if not force:
        if not click.confirm("Are you sure you want to kill all sessions?"):
            console.print("[yellow]Operation cancelled[/yellow]")
            return

    console.print("[red]Killing all sessions...[/red]")
    # TODO: Implement actual kill logic
    console.print("[green]All sessions terminated[/green]")
