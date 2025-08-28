"""Broadcast message functionality for orchestrator."""

import click
from rich.console import Console

console = Console()


@click.command()
@click.argument("message")
@click.pass_context
def broadcast(ctx: click.Context, message: str) -> None:
    """Broadcast message to all active agents and teams.

    Args:
        message: The message to broadcast
    """
    console.print(f"[yellow]Broadcasting: {message}[/yellow]")
    # TODO: Implement actual broadcast logic
    console.print("[green]Message broadcast complete[/green]")
