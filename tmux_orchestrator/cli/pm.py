"""Project Manager specific commands."""

import click
from rich.console import Console

console = Console()


@click.group()
def pm():
    """Project Manager operations."""
    pass


@pm.command()
@click.pass_context
def checkin(ctx):
    """Trigger PM status review of all agents."""
    from tmux_orchestrator.core.pm_manager import PMManager
    
    manager = PMManager(ctx.obj['tmux'])
    manager.trigger_status_review()
    
    console.print("[green]✓ PM status review triggered[/green]")


@pm.command()
@click.argument('message')
@click.pass_context
def message(ctx, message):
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
def broadcast(ctx, message):
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
def custom_checkin(ctx, custom_message):
    """Send custom check-in message to all agents."""
    from tmux_orchestrator.core.pm_manager import PMManager
    
    if not custom_message:
        custom_message = "Please provide a status update on your current work."
    
    manager = PMManager(ctx.obj['tmux'])
    results = manager.custom_checkin(custom_message)
    
    console.print(f"[green]✓ Custom check-in sent to {len(results)} agents[/green]")