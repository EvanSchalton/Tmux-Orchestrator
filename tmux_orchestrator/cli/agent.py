"""Agent management commands."""

from typing import Any, Dict
import subprocess

import click
from rich.console import Console

from tmux_orchestrator.core.agent_operations import restart_agent
from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


@click.group()
def agent() -> None:
    """Manage individual agents."""
    pass


@agent.command()
@click.argument('agent_type', type=click.Choice(['frontend', 'backend', 'testing', 'database', 'docs', 'devops']))
@click.argument('role', type=click.Choice(['developer', 'pm', 'qa', 'reviewer']))
@click.pass_context
def deploy(ctx: click.Context, agent_type: str, role: str) -> None:
    """Deploy an individual agent."""
    from tmux_orchestrator.core.agent_manager import AgentManager
    
    manager: AgentManager = AgentManager(ctx.obj['tmux'])
    session: str = manager.deploy_agent(agent_type, role)
    
    console.print(f"[green]✓ Deployed {agent_type} {role} in session: {session}[/green]")


@agent.command()
@click.argument('target')
@click.argument('message')
@click.pass_context
def message(ctx: click.Context, target: str, message: str) -> None:
    """Send a message to an agent.
    
    TARGET: Target in format session:window
    MESSAGE: The message to send
    """
    tmux: TMUXManager = ctx.obj['tmux']
    
    if tmux.send_message(target, message):
        console.print(f"[green]✓ Message sent to {target}[/green]")
    else:
        console.print(f"[red]✗ Failed to send message to {target}[/red]")


@agent.command()
@click.argument('target')
@click.pass_context
def attach(ctx: click.Context, target: str) -> None:
    """Attach to an agent's terminal.
    
    TARGET: Target in format session:window
    """
    try:
        subprocess.run(['tmux', 'attach', '-t', target], check=True)
    except subprocess.CalledProcessError:
        console.print(f"[red]✗ Failed to attach to {target}[/red]")


@agent.command()
@click.argument('target')
@click.pass_context
def restart(ctx: click.Context, target: str) -> None:
    """Restart a specific agent.
    
    TARGET: Target agent in format session:window
    """
    tmux: TMUXManager = ctx.obj['tmux']
    
    console.print(f"[yellow]Restarting agent at {target}...[/yellow]")
    
    # Delegate to business logic
    success, result_message = restart_agent(tmux, target)
    
    if success:
        console.print(f"[green]✓ {result_message}[/green]")
    else:
        console.print(f"[red]✗ {result_message}[/red]")


@agent.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show status of all agents."""
    from tmux_orchestrator.core.agent_manager import AgentManager
    
    manager: AgentManager = AgentManager(ctx.obj['tmux'])
    statuses: Dict[str, Any] = manager.get_all_status()
    
    for agent_id, status in statuses.items():
        console.print(f"\n[bold cyan]{agent_id}[/bold cyan]")
        console.print(f"  Status: {status['state']}")
        console.print(f"  Last Activity: {status['last_activity']}")
        if status.get('current_task'):
            console.print(f"  Current Task: {status['current_task']}")