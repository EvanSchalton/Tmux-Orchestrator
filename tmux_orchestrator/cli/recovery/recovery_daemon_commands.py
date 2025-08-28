"""Recovery system daemon management commands."""

import asyncio
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from tmux_orchestrator.core.recovery.recovery_daemon import run_recovery_daemon


def get_project_dir() -> Path:
    """Get project directory, creating it only when needed."""
    project_dir = Path.cwd() / ".tmux_orchestrator"
    try:
        project_dir.mkdir(exist_ok=True)
        return project_dir
    except PermissionError:
        # Fallback to user home directory if current directory is not writable
        return Path.home() / ".tmux_orchestrator"


console = Console()


@click.command("start")
@click.option("--interval", "-i", default=30, help="Monitoring interval in seconds")
@click.option("--max-concurrent", "-c", default=3, help="Maximum concurrent recoveries")
@click.option("--failure-threshold", "-f", default=3, help="Failures before triggering recovery")
@click.option("--cooldown", "-cd", default=300, help="Recovery cooldown in seconds")
@click.option("--dry-run", is_flag=True, help="Monitor only, do not perform recovery")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--daemon", "-d", is_flag=True, help="Run as background daemon")
def start_recovery(
    interval: int,
    max_concurrent: int,
    failure_threshold: int,
    cooldown: int,
    dry_run: bool,
    verbose: bool,
    daemon: bool,
) -> None:
    """Start the recovery daemon for continuous agent monitoring.

    The recovery daemon continuously monitors all Claude agents and
    automatically recovers failed agents using the integrated recovery system.

    Examples:
        tmux-orc recovery start                    # Start with defaults
        tmux-orc recovery start --interval 15     # Check every 15 seconds
        tmux-orc recovery start --dry-run         # Monitor only, no recovery
        tmux-orc recovery start --daemon          # Run in background
        tmux-orc recovery start --verbose         # Debug logging

    Configuration:
        --interval: How often to check agent health (default: 30s)
        --max-concurrent: Max simultaneous recoveries (default: 3)
        --failure-threshold: Failures before recovery (default: 3)
        --cooldown: Wait time between recovery attempts (default: 300s)

    The daemon will run until stopped with Ctrl+C or 'tmux-orc recovery stop'.
    """
    log_level = logging.DEBUG if verbose else logging.INFO

    console.print("[blue]Starting recovery daemon...[/blue]")
    console.print(f"  Monitoring interval: {interval}s")
    console.print(f"  Recovery enabled: {'No (dry-run)' if dry_run else 'Yes'}")
    console.print(f"  Max concurrent recoveries: {max_concurrent}")
    console.print(f"  Failure threshold: {failure_threshold}")
    console.print(f"  Recovery cooldown: {cooldown}s")

    if daemon:
        _start_daemon_background(
            interval=interval,
            max_concurrent=max_concurrent,
            failure_threshold=failure_threshold,
            cooldown=cooldown,
            recovery_enabled=not dry_run,
            verbose=verbose,
        )
    else:
        # Run in foreground
        console.print("\n[yellow]Press Ctrl+C to stop the daemon[/yellow]\n")

        try:
            asyncio.run(
                run_recovery_daemon(
                    monitor_interval=interval,
                    recovery_enabled=not dry_run,
                    max_concurrent_recoveries=max_concurrent,
                    failure_threshold=failure_threshold,
                    recovery_cooldown=cooldown,
                    log_level=log_level,
                )
            )
        except KeyboardInterrupt:
            console.print("\n[green]Recovery daemon stopped[/green]")


@click.command("stop")
def stop_recovery() -> None:
    """Stop the running recovery daemon.

    Gracefully stops the background recovery daemon, allowing active
    recovery operations to complete before shutdown.

    The daemon will wait up to 2 minutes for active recoveries to finish.
    """
    pid_file = get_project_dir() / "recovery-daemon.pid"

    if not pid_file.exists():
        console.print("[yellow]No recovery daemon PID file found[/yellow]")
        return

    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())

        console.print(f"[blue]Stopping recovery daemon (PID: {pid})...[/blue]")

        # Send graceful shutdown signal
        os.kill(pid, signal.SIGTERM)

        # Wait for process to exit
        import time

        for _ in range(30):  # Wait up to 30 seconds
            try:
                os.kill(pid, 0)  # Check if process still exists
                time.sleep(1)
            except OSError:
                break

        # Check if process is still running
        try:
            os.kill(pid, 0)
            console.print("[yellow]Daemon still running, sending SIGKILL...[/yellow]")
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

        # Remove PID file
        pid_file.unlink()
        console.print("[green]Recovery daemon stopped[/green]")

    except (ValueError, OSError, FileNotFoundError) as e:
        console.print(f"[red]Error stopping daemon: {e}[/red]")


def _start_daemon_background(
    interval: int,
    max_concurrent: int,
    failure_threshold: int,
    cooldown: int,
    recovery_enabled: bool,
    verbose: bool,
) -> None:
    """Start the recovery daemon in background mode."""
    pid_file = get_project_dir() / "recovery-daemon.pid"

    if pid_file.exists():
        try:
            with open(pid_file) as f:
                existing_pid = int(f.read().strip())
            os.kill(existing_pid, 0)  # Check if process exists
            console.print("[yellow]Recovery daemon is already running[/yellow]")
            return
        except (OSError, ValueError):
            # PID file exists but process is dead, remove it
            pid_file.unlink()

    # Start daemon as subprocess
    cmd = [
        sys.executable,
        "-m",
        "tmux_orchestrator.cli.main",
        "recovery",
        "start",
        "--interval",
        str(interval),
        "--max-concurrent",
        str(max_concurrent),
        "--failure-threshold",
        str(failure_threshold),
        "--cooldown",
        str(cooldown),
    ]

    if not recovery_enabled:
        cmd.append("--dry-run")
    if verbose:
        cmd.append("--verbose")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    # Write PID file
    with open(pid_file, "w") as f:
        f.write(str(process.pid))

    console.print(f"[green]Recovery daemon started in background (PID: {process.pid})[/green]")
    console.print(f"  Log file: {get_project_dir() / 'logs' / 'recovery.log'}")
