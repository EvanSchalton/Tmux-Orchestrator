"""List sessions functionality for orchestrator."""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.command()
@click.option("--all-sessions", is_flag=True, help="Show all sessions")
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def list_sessions(ctx: click.Context, all_sessions: bool, format: str) -> None:
    """List orchestrator sessions.

    Args:
        all_sessions: Show all sessions including inactive
        format: Output format (table or json)
    """
    if format == "json":
        # TODO: Implement JSON output
        console.print("{}")
    else:
        table = Table(title="Orchestrator Sessions")
        table.add_column("Session", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Agents", style="yellow")

        # TODO: Implement actual session listing
        table.add_row("example-session", "active", "3")

        console.print(table)
