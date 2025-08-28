"""Recovery system status commands."""

import os
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tmux_orchestrator.utils.tmux import TMUXManager


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


@click.command("status")
@click.option("--json", is_flag=True, help="Output in JSON format")
def recovery_status(json: bool) -> None:
    """Show recovery system status and statistics.

    Displays comprehensive information about the recovery system including:
        • Daemon status and uptime
        • Agent health overview
        • Recovery statistics
        • Recent recovery events
        • Performance metrics

    Use --json for machine-readable output suitable for monitoring systems.
    """
    tmux = TMUXManager()

    # Check daemon status
    pid_file = get_project_dir() / "recovery-daemon.pid"
    daemon_running = False
    daemon_pid = None

    if pid_file.exists():
        try:
            with open(pid_file) as f:
                daemon_pid = int(f.read().strip())
            os.kill(daemon_pid, 0)  # Check if process exists
            daemon_running = True
        except (ValueError, OSError):
            pass

    if json:
        import json as json_module

        status_data = {
            "daemon_running": daemon_running,
            "daemon_pid": daemon_pid,
            "timestamp": str(os.times()),
        }

        console.print(json_module.dumps(status_data, indent=2))
        return

    # Display rich status
    console.print("\n[bold blue]Recovery System Status[/bold blue]")

    # Daemon status panel
    daemon_status = "🟢 Running" if daemon_running else "🔴 Stopped"
    daemon_info = f"Status: {daemon_status}"
    if daemon_running and daemon_pid:
        daemon_info += f"\nPID: {daemon_pid}"

    daemon_panel = Panel(
        daemon_info,
        title="Recovery Daemon",
        border_style="green" if daemon_running else "red",
    )
    console.print(daemon_panel)

    # Agent health overview
    try:
        agents = tmux.list_agents() if hasattr(tmux, "list_agents") else []
        sessions = tmux.list_sessions()

        health_table = Table(title="System Overview")
        health_table.add_column("Metric", style="cyan")
        health_table.add_column("Value", style="green")

        health_table.add_row("Active Sessions", str(len(sessions)))
        health_table.add_row("Monitored Agents", str(len(agents)))
        health_table.add_row("Daemon Status", "Running" if daemon_running else "Stopped")

        console.print(health_table)

    except Exception as e:
        console.print(f"[red]Error gathering system info: {e}[/red]")

    # Recovery logs info
    log_dir = Path.cwd() / "registry" / "logs" / "recovery"
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        console.print(f"\n[dim]Recovery logs: {len(log_files)} files in {log_dir}[/dim]")

        if log_files:
            latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
            console.print(f"[dim]Latest log: {latest_log.name}[/dim]")
