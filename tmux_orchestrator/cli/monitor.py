"""Monitoring commands."""

import click
from rich.console import Console
import subprocess
import os
import signal

console = Console()
PID_FILE = "/tmp/tmux-orchestrator-idle-monitor.pid"
LOG_FILE = "/tmp/tmux-orchestrator-idle-monitor.log"


@click.group()
def monitor():
    """Manage the idle agent monitor."""
    pass


@monitor.command()
@click.option('--interval', default=10, help='Check interval in seconds')
@click.pass_context
def start(ctx, interval):
    """Start the idle monitor daemon."""
    from tmux_orchestrator.core.monitor import IdleMonitor
    
    monitor = IdleMonitor(ctx.obj['tmux'])
    
    if monitor.is_running():
        console.print("[yellow]Monitor is already running[/yellow]")
        monitor.status()
        return
    
    pid = monitor.start(interval)
    console.print(f"[green]✓ Idle monitor started (PID: {pid})[/green]")
    console.print(f"  Check interval: {interval} seconds")
    console.print(f"  Log file: {LOG_FILE}")


@monitor.command()
@click.pass_context
def stop(ctx):
    """Stop the idle monitor daemon."""
    from tmux_orchestrator.core.monitor import IdleMonitor
    
    monitor = IdleMonitor(ctx.obj['tmux'])
    
    if not monitor.is_running():
        console.print("[yellow]Monitor is not running[/yellow]")
        return
    
    if monitor.stop():
        console.print("[green]✓ Monitor stopped successfully[/green]")
    else:
        console.print("[red]✗ Failed to stop monitor[/red]")


@monitor.command()
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--lines', '-n', default=20, help='Number of lines to show')
def logs(follow, lines):
    """View monitor logs."""
    if not os.path.exists(LOG_FILE):
        console.print("[yellow]No log file found[/yellow]")
        return
    
    if follow:
        try:
            subprocess.run(['tail', '-f', LOG_FILE])
        except KeyboardInterrupt:
            pass
    else:
        subprocess.run(['tail', f'-{lines}', LOG_FILE])


@monitor.command()
@click.pass_context
def status(ctx):
    """Check monitor status."""
    from tmux_orchestrator.core.monitor import IdleMonitor
    
    monitor = IdleMonitor(ctx.obj['tmux'])
    monitor.status()