"""Context commands for standardized agent briefings."""

from pathlib import Path

import click
import pkg_resources  # noqa: E402
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()

try:
    # Try to use package data first
    CONTEXTS_DIR = Path(pkg_resources.resource_filename("tmux_orchestrator", "data/contexts"))
except Exception:
    # Fallback for development
    CONTEXTS_DIR = Path(__file__).parent.parent / "data" / "contexts"


def get_available_contexts():
    """Get list of available context files."""
    if not CONTEXTS_DIR.exists():
        return {}

    contexts = {}
    for file in CONTEXTS_DIR.glob("*.md"):
        role = file.stem
        contexts[role] = file

    return contexts


def load_context(role: str) -> str:
    """Load context from file."""
    contexts = get_available_contexts()
    if role not in contexts:
        raise click.ClickException(f"Context '{role}' not found. Available: {', '.join(contexts.keys())}")

    return contexts[role].read_text()


@click.group()
def context():
    """Provide standardized context briefings for common agent roles.

    These contexts serve as starting points that can be extended with
    project-specific details when spawning agents.

    Examples:
        tmux-orc context orchestrator    # Show orchestrator briefing
        tmux-orc context pm              # Show PM briefing
        tmux-orc context list            # List all available contexts
    """
    pass


@context.command()
@click.argument("role")
@click.option("--raw", is_flag=True, help="Output raw markdown without formatting")
def show(role: str, raw: bool):
    """Display context briefing for a specific role.

    ROLE: The agent role to show context for

    Examples:
        tmux-orc context show orchestrator
        tmux-orc context show pm --raw  # For copying into briefings
    """
    try:
        content = load_context(role)
    except click.ClickException as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\nUse 'tmux-orc context list' to see available contexts")
        return

    if raw:
        console.print(content)
    else:
        md = Markdown(content)
        console.print(Panel(md, title=f"{role.title()} Context", border_style="blue"))


@context.command()
def list():
    """List all available context templates."""
    contexts = get_available_contexts()

    if not contexts:
        console.print("[yellow]No context files found in tmux_orchestrator/data/contexts/[/yellow]")
        return

    console.print("\n[bold]Available System Role Contexts:[/bold]\n")

    for role, path in contexts.items():
        # Read first meaningful line as description
        content = path.read_text()
        lines = content.strip().split("\n")
        description = next((line.strip() for line in lines if line.strip() and not line.startswith("#")), "")
        console.print(f"  [cyan]{role:15}[/cyan] {description}")

    console.print("\n[dim]Use 'tmux-orc context show <role>' to view full context[/dim]")
    console.print("\n[bold]Note:[/bold] Other agent types (developer, qa, etc.) should have")
    console.print("custom briefings defined in your team plan documents.")


@context.command()
@click.argument("role")
@click.option("--session", required=True, help="Target session:window")
@click.option("--extend", help="Additional project-specific context")
def spawn(role: str, session: str, extend: str = None):
    """Spawn an agent with standardized context (orchestrator/pm only).

    For other agent types, use custom briefings from your team plan.

    Examples:
        tmux-orc context spawn pm --session project:1
        tmux-orc context spawn orchestrator --session main:0 --extend "Working on API project"
    """
    from tmux_orchestrator.utils.tmux import TMUXManager

    try:
        briefing = load_context(role)
    except click.ClickException as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Note:[/yellow] Only system roles (orchestrator, pm) have standard contexts.")
        console.print("Other agents should be spawned with custom briefings from your team plan.")
        return

    tmux = TMUXManager()

    # Add extension if provided
    if extend:
        briefing += f"\n\n## Project-Specific Context\n\n{extend}"

    # Spawn the agent
    success = tmux.spawn_agent(session, role, briefing)

    if success:
        console.print(f"[green]✓ Spawned {role} agent at {session}[/green]")
    else:
        console.print(f"[red]✗ Failed to spawn {role} agent[/red]")


@context.command()
@click.argument("output_file", type=click.Path())
@click.option("--role", required=True, help="System role (orchestrator/pm) to export")
@click.option("--project", help="Project name for customization")
def export(output_file: str, role: str, project: str = None):
    """Export a system role context to a file for customization.

    Only orchestrator and PM have standard contexts. All other agents
    (developers, writers, engineers, artists, etc.) should have custom
    briefings defined in your team plan.

    Examples:
        tmux-orc context export my-pm-briefing.md --role pm
        tmux-orc context export orchestrator-api.md --role orchestrator --project "API Service"
    """
    try:
        content = load_context(role)
    except click.ClickException as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    if project:
        content += f"\n\n## Project: {project}\n\n[Add project-specific details here]\n"

    Path(output_file).write_text(content)
    console.print(f"[green]✓ Exported {role} context to {output_file}[/green]")
