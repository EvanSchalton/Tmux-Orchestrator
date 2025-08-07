"""Orchestrator specific commands."""

import click
from rich.console import Console
from pathlib import Path

console = Console()


@click.group()
def orchestrator():
    """Orchestrator operations."""
    pass


@orchestrator.command()
@click.pass_context
def start(ctx):
    """Start the orchestrator session."""
    from tmux_orchestrator.core.orchestrator_manager import OrchestratorManager
    
    manager = OrchestratorManager(ctx.obj['tmux'])
    
    if manager.is_running():
        console.print("[yellow]Orchestrator is already running[/yellow]")
        return
    
    manager.start()
    console.print("[green]✓ Orchestrator started[/green]")


@orchestrator.command()
@click.argument('minutes', type=int)
@click.argument('message')
@click.option('--target', default='orchestrator:1', help='Target window')
@click.pass_context
def schedule(ctx, minutes, message, target):
    """Schedule a check-in message."""
    from tmux_orchestrator.core.scheduler import Scheduler
    
    scheduler = Scheduler(ctx.obj['tmux'])
    scheduler.schedule_checkin(minutes, message, target)
    
    console.print(f"[green]✓ Scheduled check-in in {minutes} minutes[/green]")
    console.print(f"  Target: {target}")
    console.print(f"  Message: {message}")


@orchestrator.command()
@click.pass_context
def status(ctx):
    """Show orchestrator status."""
    from tmux_orchestrator.core.orchestrator_manager import OrchestratorManager
    
    manager = OrchestratorManager(ctx.obj['tmux'])
    status = manager.get_status()
    
    if not status['running']:
        console.print("[yellow]Orchestrator is not running[/yellow]")
        return
    
    console.print("[bold]Orchestrator Status[/bold]")
    console.print(f"  Session: {status['session']}")
    console.print(f"  Running: {status['running']}")
    console.print(f"  Uptime: {status['uptime']}")
    console.print(f"  Active Projects: {', '.join(status['projects'])}")