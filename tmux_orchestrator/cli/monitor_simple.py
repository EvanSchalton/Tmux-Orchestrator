#!/usr/bin/env python3
"""Simple monitoring command that works reliably."""

import os
import signal
import subprocess
import time
from pathlib import Path

import click
from rich.console import Console

console = Console()

# Use secure project directory instead of /tmp
PROJECT_DIR = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")
PROJECT_DIR.mkdir(exist_ok=True)
LOGS_DIR = PROJECT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


@click.group()
def monitor_simple():
    """Simple but reliable monitoring commands."""
    pass


@monitor_simple.command("start")
@click.option("--interval", default=10, help="Check interval in seconds")
def start(interval: int):
    """Start the simple monitoring daemon."""
    pid_file = PROJECT_DIR / "simple-monitor.pid"

    # Check if already running
    if pid_file.exists():
        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            console.print(f"[yellow]Monitor already running (PID: {pid})[/yellow]")
            return
        except (ProcessLookupError, ValueError):
            # Stale PID file
            pid_file.unlink()

    # Start monitor in background

    from tmux_orchestrator.core.monitor_fix import SimpleMonitor

    monitor = SimpleMonitor()

    # Fork process
    pid = os.fork()
    if pid == 0:
        # Child process - run daemon
        monitor.run_daemon(interval)
    else:
        # Parent process
        time.sleep(1)  # Give daemon time to start
        console.print(f"[green]✓ Simple monitor started (PID: {pid})[/green]")
        console.print(f"  Check interval: {interval} seconds")
        console.print(f"  Log file: {LOGS_DIR / 'simple-monitor.log'}")


@monitor_simple.command("stop")
def stop():
    """Stop the monitoring daemon."""
    pid_file = PROJECT_DIR / "simple-monitor.pid"

    if not pid_file.exists():
        console.print("[yellow]Monitor is not running[/yellow]")
        return

    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]✓ Monitor stopped (PID: {pid})[/green]")
    except Exception as e:
        console.print(f"[red]Error stopping monitor: {e}[/red]")


@monitor_simple.command("status")
def status():
    """Check monitor status."""
    pid_file = PROJECT_DIR / "simple-monitor.pid"

    if not pid_file.exists():
        console.print("[red]✗ Monitor is not running[/red]")
        return

    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        console.print(f"[green]✓ Monitor is running (PID: {pid})[/green]")

        # Show recent log entries
        log_file = LOGS_DIR / "simple-monitor.log"
        if log_file.exists():
            result = subprocess.run(["tail", "-5", str(log_file)], capture_output=True, text=True)
            if result.stdout:
                console.print("\nRecent activity:")
                console.print(result.stdout)
    except (ProcessLookupError, ValueError):
        console.print("[red]✗ Monitor process not found (stale PID file)[/red]")


@monitor_simple.command("logs")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--lines", "-n", default=20, help="Number of lines to show")
def logs(follow: bool, lines: int):
    """View monitor logs."""
    log_file = LOGS_DIR / "simple-monitor.log"

    if not log_file.exists():
        console.print("[yellow]No log file found[/yellow]")
        return

    if follow:
        try:
            subprocess.run(["tail", "-f", str(log_file)])
        except KeyboardInterrupt:
            pass
    else:
        subprocess.run(["tail", f"-{lines}", str(log_file)])


if __name__ == "__main__":
    monitor_simple()
