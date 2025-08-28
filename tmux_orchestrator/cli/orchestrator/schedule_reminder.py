"""Schedule reminder functionality for orchestrator."""

import click
from rich.console import Console

console = Console()


@click.command()
@click.argument("delay", type=int)
@click.argument("message")
@click.pass_context
def schedule(ctx: click.Context, delay: int, message: str) -> None:
    """Schedule a reminder message.

    Args:
        delay: Delay in minutes before sending the reminder
        message: The reminder message to send
    """
    console.print(f"[yellow]Scheduling reminder in {delay} minutes: {message}[/yellow]")
    # TODO: Implement actual scheduling logic
    console.print("[green]Reminder scheduled[/green]")
