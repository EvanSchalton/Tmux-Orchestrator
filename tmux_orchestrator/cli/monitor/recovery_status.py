"""Show agent recovery daemon status and recent activity."""

import click
from rich.console import Console

console = Console()


def recovery_status_info(ctx: click.Context, verbose: bool) -> None:
    """Show agent recovery daemon status and recent activity."""
    from pathlib import Path

    # Check if recovery daemon is running
    pid_file = Path.home() / ".tmux_orchestrator" / "recovery-daemon.pid"
    log_file = Path.home() / ".tmux_orchestrator" / "logs" / "recovery.log"

    if pid_file.exists():
        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())

            # Check if process is actually running
            import psutil

            try:
                process = psutil.Process(pid)
                if process.is_running():
                    console.print("[green]Recovery daemon is running[/green]")
                    console.print(f"PID: {pid}")

                    if verbose and log_file.exists():
                        console.print("\n[bold]Recent recovery logs:[/bold]")
                        import subprocess

                        result = subprocess.run(["tail", "-n", "20", str(log_file)], capture_output=True, text=True)
                        if result.stdout:
                            console.print(result.stdout)
                else:
                    console.print("[yellow]Recovery daemon PID file exists but process not running[/yellow]")
            except psutil.NoSuchProcess:
                console.print("[yellow]Recovery daemon PID file exists but process not found[/yellow]")
        except Exception as e:
            console.print(f"[red]Error checking recovery daemon status: {e}[/red]")
    else:
        console.print("[yellow]Recovery daemon is not running[/yellow]")
        console.print("Start with: tmux-orc monitor recovery-start")
