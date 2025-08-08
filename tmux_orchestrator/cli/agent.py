"""Agent management commands."""

import subprocess
from typing import Any, Dict

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
@click.argument(
    'agent_type',
    type=click.Choice(['frontend', 'backend', 'testing', 'database', 'docs', 'devops'])
)
@click.argument('role', type=click.Choice(['developer', 'pm', 'qa', 'reviewer']))
@click.pass_context
def deploy(ctx: click.Context, agent_type: str, role: str) -> None:
    """Deploy an individual agent."""
    from tmux_orchestrator.core.agent_manager import AgentManager

    manager: AgentManager = AgentManager(ctx.obj['tmux'])
    session: str = manager.deploy_agent(agent_type, role)

    console.print(
        f"[green]✓ Deployed {agent_type} {role} in session: {session}[/green]"
    )


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


@agent.command()
@click.argument('target')
@click.pass_context
def kill(ctx: click.Context, target: str) -> None:
    """Kill a specific agent.

    TARGET: Target agent in format session:window
    """
    tmux: TMUXManager = ctx.obj['tmux']

    console.print(f"[yellow]Killing agent at {target}...[/yellow]")

    # Parse target to get session and window
    if ':' not in target:
        console.print("[red]✗ Invalid target format. Use session:window[/red]")
        return

    try:
        # Kill the specific window (using session kill as fallback)
        try:
            if hasattr(tmux, 'kill_window'):
                success = tmux.kill_window(target)
            else:
                # Fallback: kill entire session if method doesn't exist
                session = target.split(':')[0]
                success = tmux.kill_session(session)
        except Exception:
            success = False
            
        if success:
            console.print(f"[green]✓ Agent at {target} killed successfully[/green]")
        else:
            console.print(f"[red]✗ Failed to kill agent at {target}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error killing agent: {str(e)}[/red]")


@agent.command()
@click.argument('target')
@click.option('--json', is_flag=True, help='Output in JSON format')
@click.pass_context
def info(ctx: click.Context, target: str, json: bool) -> None:
    """Get detailed information about a specific agent.

    TARGET: Target agent in format session:window
    """
    tmux: TMUXManager = ctx.obj['tmux']

    # Get detailed agent information
    agent_info = {
        'target': target,
        'exists': tmux.has_session(target.split(':')[0]) if ':' in target else False,
        'pane_content': '',
        'status': 'unknown'
    }

    if agent_info['exists']:
        try:
            agent_info['pane_content'] = tmux.capture_pane(target, lines=20)
            agent_info['status'] = 'active' if agent_info['pane_content'] else 'inactive'
        except Exception as e:
            agent_info['status'] = f'error: {str(e)}'

    if json:
        import json as json_module
        console.print(json_module.dumps(agent_info, indent=2))
    else:
        console.print(f"[bold cyan]Agent Information: {target}[/bold cyan]")
        console.print(f"  Exists: {'✓' if agent_info['exists'] else '✗'}")
        console.print(f"  Status: {agent_info['status']}")
        if agent_info['pane_content'] and isinstance(agent_info['pane_content'], str):
            console.print("  Recent activity:")
            lines = str(agent_info['pane_content']).split('\n')[-5:]
            for line in lines:
                if line.strip():
                    console.print(f"    {line[:60]}..." if len(line) > 60 else f"    {line}")
