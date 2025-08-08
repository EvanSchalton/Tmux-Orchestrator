"""Project Manager specific commands."""

from typing import Optional

import click
from rich.console import Console

from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


@click.group()
def pm() -> None:
    """Project Manager operations."""
    pass


@pm.command()
@click.pass_context
def checkin(ctx: click.Context) -> None:
    """Trigger PM status review of all agents."""
    from tmux_orchestrator.core.pm_manager import PMManager

    manager = PMManager(ctx.obj['tmux'])
    manager.trigger_status_review()

    console.print("[green]✓ PM status review triggered[/green]")


@pm.command()
@click.argument('message')
@click.pass_context
def message(ctx: click.Context, message: str) -> None:
    """Send a direct message to the PM."""
    from tmux_orchestrator.core.pm_manager import PMManager

    manager = PMManager(ctx.obj['tmux'])
    target = manager.find_pm_session()

    if not target:
        console.print("[red]✗ No PM session found[/red]")
        return

    if ctx.obj['tmux'].send_message(target, message):
        console.print(f"[green]✓ Message sent to PM at {target}[/green]")
    else:
        console.print("[red]✗ Failed to send message to PM[/red]")


@pm.command()
@click.argument('message')
@click.pass_context
def broadcast(ctx: click.Context, message: str) -> None:
    """PM broadcasts a message to all agents."""
    from tmux_orchestrator.core.pm_manager import PMManager

    manager = PMManager(ctx.obj['tmux'])
    results = manager.broadcast_to_all_agents(message)

    console.print(f"[green]✓ Broadcast sent to {len(results)} agents[/green]")
    for agent, success in results.items():
        status = "✓" if success else "✗"
        color = "green" if success else "red"
        console.print(f"  [{color}]{status} {agent}[/{color}]")


@pm.command()
@click.option('--custom-message', help='Custom check-in message')
@click.pass_context
def custom_checkin(ctx: click.Context, custom_message: Optional[str]) -> None:
    """Send custom check-in message to all agents."""
    from tmux_orchestrator.core.pm_manager import PMManager

    if not custom_message:
        custom_message = "Please provide a status update on your current work."

    manager = PMManager(ctx.obj['tmux'])
    results = manager.custom_checkin(custom_message)

    console.print(f"[green]✓ Custom check-in sent to {len(results)} agents[/green]")


@pm.command()
@click.option('--json', is_flag=True, help='Output in JSON format')
@click.pass_context
def status(ctx: click.Context, json: bool) -> None:
    """Show PM status and team overview."""
    from rich.table import Table

    from tmux_orchestrator.core.pm_manager import PMManager

    manager = PMManager(ctx.obj['tmux'])
    pm_target = manager.find_pm_session()

    if not pm_target:
        console.print("[red]✗ No PM session found[/red]")
        console.print("\nTo create a PM, use: [bold]tmux-orc pm create <session>[/bold]")
        return

    # Get PM status
    pm_status = {
        'target': pm_target,
        'active': True,
        'session': pm_target.split(':')[0],
        'window': pm_target.split(':')[1] if ':' in pm_target else '0'
    }

    # Get team overview (using tmux directly since get_team_agents may not exist)
    try:
        team_agents = manager.get_team_agents(pm_status['session'])
    except AttributeError:
        # Fallback: get agents from tmux directly
        team_agents = ctx.obj['tmux'].list_agents()

    if json:
        import json as json_module
        status_data = {
            'pm_status': pm_status,
            'team_agents': team_agents,
            'summary': {
                'total_agents': len(team_agents),
                'active_agents': len([a for a in team_agents if a.get('status') == 'active'])
            }
        }
        console.print(json_module.dumps(status_data, indent=2))
        return

    # Display rich status
    console.print("[bold blue]Project Manager Status[/bold blue]")
    console.print(f"  Target: {pm_target}")
    console.print(f"  Session: {pm_status['session']}")
    console.print(f"  Window: {pm_status['window']}")
    console.print("  Status: [green]Active[/green]")

    if team_agents:
        console.print(f"\n[bold]Team Overview ({len(team_agents)} agents):[/bold]")

        table = Table()
        table.add_column("Agent", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Last Activity", style="blue")

        for agent in team_agents:
            table.add_row(
                f"{agent.get('session', 'unknown')}:{agent.get('window', '0')}",
                agent.get('type', 'unknown'),
                agent.get('status', 'unknown'),
                agent.get('last_activity', 'Unknown')
            )

        console.print(table)
    else:
        console.print("\n[yellow]No team agents found in this session[/yellow]")


@pm.command()
@click.argument('session')
@click.option('--project-dir', help='Project directory (defaults to current)')
@click.pass_context
def create(ctx: click.Context, session: str, project_dir: Optional[str]) -> None:
    """Create a new Project Manager in specified session.

    SESSION: Session name where PM will be created
    """
    from pathlib import Path

    if not project_dir:
        project_dir = str(Path.cwd())

    tmux: TMUXManager = ctx.obj['tmux']

    # Check if session exists, create if not
    if not tmux.has_session(session):
        console.print(f"[blue]Creating new session: {session}[/blue]")
        if not tmux.create_session(session, "Project-Manager", project_dir):
            console.print(f"[red]✗ Failed to create session {session}[/red]")
            return

    # Create PM window
    pm_window = "Project-Manager"
    if not tmux.create_window(session, pm_window, project_dir):
        console.print(f"[red]✗ Failed to create PM window in {session}[/red]")
        return

    # Start Claude PM
    target = f"{session}:{pm_window}"
    console.print(f"[blue]Starting Project Manager at {target}...[/blue]")

    # Start Claude
    if not tmux.send_keys(target, 'claude --dangerously-skip-permissions'):
        console.print(f"[red]✗ Failed to start Claude in {target}[/red]")
        return

    import time
    time.sleep(0.5)
    tmux.send_keys(target, 'Enter')
    time.sleep(3)  # Wait for Claude to start

    # Send PM briefing
    pm_briefing = """You are the Project Manager for this development team. Your responsibilities:

1. Coordinate team activities and maintain project timeline
2. Ensure quality standards are met across all deliverables
3. Monitor progress and identify blockers quickly
4. Facilitate communication between team members
5. Report status updates to the orchestrator

Begin by analyzing the project structure and creating an initial project plan."""

    if tmux.send_message(target, pm_briefing):
        console.print(f"[green]✓ Project Manager created successfully at {target}[/green]")
        console.print(f"  Session: {session}")
        console.print(f"  Window: {pm_window}")
        console.print(f"  Directory: {project_dir}")
    else:
        console.print("[yellow]⚠ PM created but briefing may have failed[/yellow]")
