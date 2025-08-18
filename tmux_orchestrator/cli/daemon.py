#!/usr/bin/env python3
"""Daemon management commands for high-performance messaging."""

import asyncio
import json
import signal
import sys
import time
from pathlib import Path

import click
import psutil
from rich.console import Console

from tmux_orchestrator.core.messaging_daemon import HighPerformanceMessagingDaemon

console = Console()

DAEMON_PID_FILE = Path("/tmp/tmux-orc-msgd.pid")
DAEMON_SOCKET = "/tmp/tmux-orc-msgd.sock"


@click.group()
def daemon() -> None:
    """Manage high-performance messaging daemon.

    The daemon provides sub-100ms message delivery vs 5000ms CLI overhead.
    Essential for real-time agent communication.

    Examples:
        tmux-orc daemon start       # Start daemon
        tmux-orc daemon stop        # Stop daemon
        tmux-orc daemon status      # Check status
        tmux-orc daemon restart     # Restart daemon
    """
    pass


@daemon.command()
@click.option("--detach/--no-detach", default=True, help="Run daemon in background")
@click.option("--socket", default=DAEMON_SOCKET, help="Unix socket path")
def start(detach: bool, socket: str) -> None:
    """Start the high-performance messaging daemon."""

    # Check if already running
    if _is_daemon_running():
        console.print("[yellow]⚠️  Daemon already running[/yellow]")
        return

    if detach:
        # Fork daemon process
        pid = _start_daemon_process(socket)
        if pid:
            console.print(f"[green]✓ Daemon started (PID: {pid})[/green]")
            console.print(f"Socket: {socket}")
            console.print("Use 'tmux-orc daemon status' to check health")
        else:
            console.print("[red]✗ Failed to start daemon[/red]")
            sys.exit(1)
    else:
        # Run in foreground (for debugging)
        console.print("[blue]Starting daemon in foreground mode...[/blue]")
        console.print("Press Ctrl+C to stop")

        daemon_instance = HighPerformanceMessagingDaemon(socket)
        try:
            asyncio.run(daemon_instance.start())
        except KeyboardInterrupt:
            console.print("\n[yellow]Daemon stopped by user[/yellow]")
            daemon_instance.stop()


@daemon.command()
def stop() -> None:
    """Stop the messaging daemon."""

    if not _is_daemon_running():
        console.print("[yellow]⚠️  Daemon not running[/yellow]")
        return

    try:
        # Read PID file
        with open(DAEMON_PID_FILE) as f:
            pid = int(f.read().strip())

        # Send SIGTERM
        import os

        os.kill(pid, signal.SIGTERM)

        # Wait for shutdown
        for _ in range(10):  # Wait up to 5 seconds
            if not _is_daemon_running():
                break
            time.sleep(0.5)

        if _is_daemon_running():
            # Force kill if still running
            os.kill(pid, signal.SIGKILL)
            console.print("[yellow]⚠️  Daemon force-killed[/yellow]")
        else:
            console.print("[green]✓ Daemon stopped gracefully[/green]")

        # Clean up PID file
        try:
            DAEMON_PID_FILE.unlink()
        except FileNotFoundError:
            pass

    except Exception as e:
        console.print(f"[red]✗ Error stopping daemon: {e}[/red]")
        sys.exit(1)


@daemon.command()
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
def status(format: str) -> None:
    """Check daemon status and performance."""

    if not _is_daemon_running():
        if format == "json":
            console.print(json.dumps({"status": "stopped", "running": False}))
        else:
            console.print("[red]✗ Daemon not running[/red]")
            console.print("Start with: tmux-orc daemon start")
        return

    # Get daemon stats via socket
    try:

        async def _get_stats():
            from tmux_orchestrator.core.messaging_daemon import DaemonClient

            client = DaemonClient(DAEMON_SOCKET)
            return await client.get_status()

        stats = asyncio.run(_get_stats())

        if format == "json":
            console.print(json.dumps(stats, indent=2))
        else:
            console.print("[bold]🚀 High-Performance Messaging Daemon[/bold]")
            console.print(f"Status: [green]{stats['status']}[/green]")
            console.print(f"Uptime: {stats['uptime_seconds']:.1f}s")
            console.print(f"Messages Processed: {stats['messages_processed']}")
            console.print(f"Queue Size: {stats['queue_size']}")
            console.print(f"Avg Delivery: {stats['avg_delivery_time_ms']:.1f}ms")

            perf = stats["current_performance"]
            if perf == "OK":
                console.print(f"Performance: [green]{perf}[/green] (< 100ms target)")
            else:
                console.print(f"Performance: [red]{perf}[/red] (exceeds 100ms target)")

    except Exception as e:
        if format == "json":
            console.print(json.dumps({"status": "error", "message": str(e)}))
        else:
            console.print(f"[red]✗ Error getting daemon status: {e}[/red]")


@daemon.command()
def restart() -> None:
    """Restart the messaging daemon."""
    console.print("[blue]Restarting daemon...[/blue]")

    # Stop if running
    if _is_daemon_running():
        console.print("Stopping current daemon...")
        ctx = click.get_current_context()
        ctx.invoke(stop)
        time.sleep(1)

    # Start new instance
    console.print("Starting new daemon...")
    ctx = click.get_current_context()
    ctx.invoke(start)


@daemon.command()
def logs() -> None:
    """Show daemon logs (last 50 lines)."""
    log_file = Path("/tmp/tmux-orc-msgd.log")

    if not log_file.exists():
        console.print("[yellow]⚠️  No log file found[/yellow]")
        return

    try:
        with open(log_file) as f:
            lines = f.readlines()

        # Show last 50 lines
        recent_lines = lines[-50:] if len(lines) > 50 else lines

        console.print("[bold]📋 Daemon Logs (last 50 lines)[/bold]")
        console.print("=" * 50)

        for line in recent_lines:
            # Color-code log levels
            if "ERROR" in line:
                console.print(f"[red]{line.rstrip()}[/red]")
            elif "WARNING" in line:
                console.print(f"[yellow]{line.rstrip()}[/yellow]")
            elif "INFO" in line:
                console.print(f"[blue]{line.rstrip()}[/blue]")
            else:
                console.print(line.rstrip())

    except Exception as e:
        console.print(f"[red]✗ Error reading logs: {e}[/red]")


def _is_daemon_running() -> bool:
    """Check if daemon process is running."""
    try:
        if not DAEMON_PID_FILE.exists():
            return False

        with open(DAEMON_PID_FILE) as f:
            pid = int(f.read().strip())

        # Check if process exists
        return bool(psutil.pid_exists(pid))

    except (FileNotFoundError, ValueError, PermissionError):
        return False


def _start_daemon_process(socket_path: str) -> int | None:
    """Start daemon as background process."""
    import subprocess

    try:
        # Start daemon process
        cmd = [
            sys.executable,
            "-c",
            f"""
import asyncio
import os
import sys
from pathlib import Path

# Write PID file
with open('{DAEMON_PID_FILE}', 'w') as f:
    f.write(str(os.getpid()))

# Setup logging
import logging
logging.basicConfig(
    filename='/tmp/tmux-orc-msgd.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import and start daemon
sys.path.insert(0, '/workspaces/Tmux-Orchestrator')
from tmux_orchestrator.core.messaging_daemon import HighPerformanceMessagingDaemon

daemon = HighPerformanceMessagingDaemon('{socket_path}')
asyncio.run(daemon.start())
""",
        ]

        # Start in background with stdout/stderr redirected
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

        # Give it a moment to start
        time.sleep(2)

        # Check if it's running
        if _is_daemon_running():
            return proc.pid
        else:
            return None

    except Exception as e:
        console.print(f"[red]Error starting daemon: {e}[/red]")
        return None


if __name__ == "__main__":
    daemon()
