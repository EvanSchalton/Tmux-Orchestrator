"""Agent management commands."""

import click
from rich.console import Console

console = Console()


@click.group()
def agent():
    """Manage individual agents."""
    pass


@agent.command()
@click.argument('agent_type', type=click.Choice(['frontend', 'backend', 'testing', 'database', 'docs', 'devops']))
@click.argument('role', type=click.Choice(['developer', 'pm', 'qa', 'reviewer']))
@click.pass_context
def deploy(ctx, agent_type, role):
    """Deploy an individual agent."""
    from tmux_orchestrator.core.agent_manager import AgentManager
    
    manager = AgentManager(ctx.obj['tmux'])
    session = manager.deploy_agent(agent_type, role)
    
    console.print(f"[green]✓ Deployed {agent_type} {role} in session: {session}[/green]")


@agent.command()
@click.argument('target', help='Target in format session:window')
@click.argument('message')
@click.pass_context
def message(ctx, target, message):
    """Send a message to an agent."""
    tmux = ctx.obj['tmux']
    
    if tmux.send_message(target, message):
        console.print(f"[green]✓ Message sent to {target}[/green]")
    else:
        console.print(f"[red]✗ Failed to send message to {target}[/red]")


@agent.command()
@click.argument('target', help='Target in format session:window')
@click.pass_context
def attach(ctx, target):
    """Attach to an agent's terminal."""
    import subprocess
    
    try:
        subprocess.run(['tmux', 'attach', '-t', target], check=True)
    except subprocess.CalledProcessError:
        console.print(f"[red]✗ Failed to attach to {target}[/red]")


@agent.command()
@click.pass_context
def status(ctx):
    """Show status of all agents."""
    from tmux_orchestrator.core.agent_manager import AgentManager
    
    manager = AgentManager(ctx.obj['tmux'])
    statuses = manager.get_all_status()
    
    for agent_id, status in statuses.items():
        console.print(f"\n[bold cyan]{agent_id}[/bold cyan]")
        console.print(f"  Status: {status['state']}")
        console.print(f"  Last Activity: {status['last_activity']}")
        if status.get('current_task'):
            console.print(f"  Current Task: {status['current_task']}")