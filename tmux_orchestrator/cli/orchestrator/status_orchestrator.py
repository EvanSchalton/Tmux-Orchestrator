"""Status functionality for orchestrator."""

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
@click.option("--detailed", is_flag=True, help="Show detailed status")
@click.pass_context
def status(ctx: click.Context, detailed: bool) -> None:
    """Display orchestrator status.

    Args:
        detailed: Show detailed status information
    """
    status_text = """[green]● Orchestrator Active[/green]
Sessions: 1
Agents: 5
Status: Operational"""

    if detailed:
        status_text += """

Detailed Information:
- Session: refactor-focused
- PM: Active
- Developers: 2
- QA: 2
- DevOps: 1"""

    panel = Panel(status_text, title="Orchestrator Status", border_style="green")
    console.print(panel)
