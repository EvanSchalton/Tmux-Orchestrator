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


def get_available_contexts() -> dict[str, Path]:
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
def context() -> None:
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
def show(role: str, raw: bool) -> None:
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
def list() -> None:
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
def spawn(role: str, session: str, extend: str | None = None) -> None:
    """Spawn an agent with standardized context (orchestrator/pm only).

    This command creates a complete agent setup:
    1. Creates the window if needed
    2. Starts Claude with appropriate permissions
    3. Waits for initialization
    4. Sends the role context

    For other agent types, use custom briefings from your team plan.

    Examples:
        tmux-orc context spawn pm --session project:1
        tmux-orc context spawn orchestrator --session main:0 --extend "Working on API project"
    """
    import subprocess
    import time

    from tmux_orchestrator.utils.tmux import TMUXManager

    try:
        load_context(role)
    except click.ClickException as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Note:[/yellow] Only system roles (orchestrator, pm) have standard contexts.")
        console.print("Other agents should be spawned with custom briefings from your team plan.")
        return

    tmux = TMUXManager()

    # Parse session:window format
    try:
        session_name, window_idx_str = session.split(":")
        window_idx = int(window_idx_str)
    except ValueError:
        console.print(f"[red]Error: Invalid session format '{session}'. Use 'session:window' (e.g., project:1)[/red]")
        return

    # Check if session exists, create if needed
    sessions = tmux.list_sessions()
    if not any(s["name"] == session_name for s in sessions):
        console.print(f"[yellow]Creating new session: {session_name}[/yellow]")
        subprocess.run(["tmux", "new-session", "-d", "-s", session_name], check=True)

    # Create window with appropriate name
    window_name = f"Claude-{role}"
    try:
        # Check if window already exists
        windows = tmux.list_windows(session_name)
        window_exists = any(w.get("index") == str(window_idx) for w in windows)

        if window_exists:
            console.print(f"[yellow]Window {session} already exists - using existing window[/yellow]")
            # Rename the window to match our convention
            subprocess.run(["tmux", "rename-window", "-t", session, window_name], check=False)
        else:
            # Create new window
            subprocess.run(["tmux", "new-window", "-t", session, "-n", window_name], check=True)
            console.print(f"[green]Created window: {session} ({window_name})[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error creating window: {e}[/red]")
        return

    # Start Claude in the window
    console.print(f"[blue]Starting Claude in {session}...[/blue]")
    tmux.send_keys(session, "claude --dangerously-skip-permissions", literal=True)
    tmux.send_keys(session, "Enter")

    # Wait for Claude to initialize
    console.print("[dim]Waiting for Claude to initialize...[/dim]")
    time.sleep(8)

    # Send instruction message instead of full context
    if role == "pm":
        message = (
            "You're the PM for our team, please run 'tmux-orc context show pm' for more information about your role"
        )
    else:
        message = f"You're the {role} for our team, please run 'tmux-orc context show {role}' for more information about your role"

    # Add extension if provided
    if extend:
        message += f"\n\n## Additional Instructions\n\n{extend}"

    console.print(f"[blue]Sending {role} instruction...[/blue]")
    success = tmux.send_message(session, message)

    if success:
        console.print(f"[green]✓ Successfully spawned {role} agent at {session}[/green]")
        console.print(f"  Window name: {window_name}")
        console.print("  Claude started: Yes")
        console.print("  Context sent: Yes")
    else:
        console.print(f"[red]✗ Failed to send context to {role} agent[/red]")
        console.print("[yellow]Claude may have started but context sending failed[/yellow]")


@context.command()
@click.argument("output_file", type=click.Path())
@click.option("--role", required=True, help="System role (orchestrator/pm) to export")
@click.option("--project", help="Project name for customization")
def export(output_file: str, role: str, project: str | None = None) -> None:
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
