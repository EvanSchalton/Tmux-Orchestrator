"""TMUX Orchestrator CLI."""

import click
from rich.console import Console
from rich.table import Table
from pathlib import Path
import os
import sys

from tmux_orchestrator.cli import (
    agent,
    deploy,
    monitor,
    orchestrator,
    pm,
    team,
)
from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


@click.group()
@click.version_option()
@click.pass_context
def cli(ctx):
    """TMUX Orchestrator - AI-powered tmux session management."""
    ctx.ensure_object(dict)
    ctx.obj['config'] = Config.load()
    ctx.obj['tmux'] = TMUXManager()
    ctx.obj['console'] = console


@cli.command()
@click.pass_context
def list(ctx):
    """List all active agents."""
    tmux = ctx.obj['tmux']
    agents = tmux.list_agents()
    
    if not agents:
        console.print("[yellow]No active agents found.[/yellow]")
        return
    
    table = Table(title="Active Agents")
    table.add_column("Session", style="cyan")
    table.add_column("Window", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")
    
    for agent in agents:
        table.add_row(
            agent['session'],
            str(agent['window']),
            agent['type'],
            agent['status']
        )
    
    console.print(table)


@cli.command()
@click.pass_context
def status(ctx):
    """Show detailed agent status dashboard."""
    from tmux_orchestrator.core.status import StatusDashboard
    
    dashboard = StatusDashboard(ctx.obj['tmux'])
    dashboard.display()


@cli.command()
@click.argument('task_file', type=click.Path(exists=True))
@click.option('--project-name', help='Project name (defaults to current directory)')
@click.pass_context
def deploy(ctx, task_file, project_name):
    """Deploy a new team with the given task file."""
    from tmux_orchestrator.core.deployer import TeamDeployer
    
    if not project_name:
        project_name = Path.cwd().name
    
    deployer = TeamDeployer(ctx.obj['tmux'], ctx.obj['config'])
    deployer.deploy(task_file, project_name)


@cli.command()
@click.argument('task_file', type=click.Path(exists=True))
@click.pass_context
def restart(ctx, task_file):
    """Restart the team with the given task file."""
    from tmux_orchestrator.core.deployer import TeamDeployer
    
    project_name = Path.cwd().name
    tmux = ctx.obj['tmux']
    
    # Kill existing sessions
    console.print("[yellow]Killing existing sessions...[/yellow]")
    tmux.kill_project_sessions(project_name)
    
    # Deploy fresh
    deployer = TeamDeployer(tmux, ctx.obj['config'])
    deployer.deploy(task_file, project_name)


@cli.command()
@click.pass_context
def recover(ctx):
    """Recover missing agents."""
    from tmux_orchestrator.core.recovery import AgentRecovery
    
    recovery = AgentRecovery(ctx.obj['tmux'], ctx.obj['config'])
    recovery.recover_missing_agents()


# Add subcommand groups
cli.add_command(agent.agent)
cli.add_command(monitor.monitor)
cli.add_command(orchestrator.orchestrator)
cli.add_command(pm.pm)
cli.add_command(team.team)


if __name__ == '__main__':
    cli()