"""Monitoring commands with enhanced idle detection."""

import os
import signal
import subprocess

import click
from rich.console import Console

console = Console()
PID_FILE = "/tmp/tmux-orchestrator-idle-monitor.pid"
LOG_FILE = "/tmp/tmux-orchestrator-idle-monitor.log"
RECOVERY_PID_FILE = "/tmp/tmux-orchestrator-recovery.pid"
RECOVERY_LOG_FILE = "/tmp/tmux-orchestrator-recovery.log"


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


@monitor.command('recovery-start')
@click.option('--config', '-c', help='Configuration file path')
@click.pass_context
def recovery_start(ctx, config):
    """Start the recovery daemon with bulletproof idle detection."""
    from tmux_orchestrator.core.recovery_daemon import RecoveryDaemon

    daemon = RecoveryDaemon(config)

    if daemon.is_running():
        console.print("[yellow]Recovery daemon is already running[/yellow]")
        return

    console.print("[blue]Starting recovery daemon with enhanced detection...[/blue]")

    # Start daemon in background
    import threading
    def run_daemon():
        daemon.start()

    daemon_thread = threading.Thread(target=run_daemon, daemon=True)
    daemon_thread.start()

    # Give daemon time to start
    import time
    time.sleep(2)

    if daemon.is_running():
        status = daemon.get_status()
        console.print(f"[green]✓ Recovery daemon started (PID: {status['pid']})[/green]")
        console.print(f"  Check interval: {status['check_interval']}s")
        console.print(f"  Auto-discovery: {status['auto_discover']}")
        console.print(f"  Enhanced detection: {status['enhanced_detection']}")
        console.print(f"  Log file: {status['log_file']}")
    else:
        console.print("[red]✗ Failed to start recovery daemon[/red]")


@monitor.command('recovery-stop')
def recovery_stop():
    """Stop the recovery daemon."""
    if not os.path.exists(RECOVERY_PID_FILE):
        console.print("[yellow]Recovery daemon is not running[/yellow]")
        return

    try:
        with open(RECOVERY_PID_FILE) as f:
            pid = int(f.read().strip())

        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]✓ Recovery daemon stopped (PID: {pid})[/green]")

    except (ProcessLookupError, ValueError):
        console.print("[yellow]Recovery daemon process not found[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Failed to stop recovery daemon: {e}[/red]")


@monitor.command('recovery-status')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.pass_context
def recovery_status(ctx, verbose):
    """Show recovery daemon status with enhanced monitoring details."""
    from rich.panel import Panel
    from rich.table import Table

    from tmux_orchestrator.core.config import Config
    from tmux_orchestrator.core.monitor import AgentMonitor
    from tmux_orchestrator.core.recovery_daemon import RecoveryDaemon

    daemon = RecoveryDaemon()
    status = daemon.get_status()

    # Show daemon status
    if status['running']:
        console.print(f"[green]✓ Recovery daemon is running (PID: {status['pid']})[/green]")
        console.print("  Using bulletproof 4-snapshot idle detection")
    else:
        console.print("[red]✗ Recovery daemon is not running[/red]")

    if verbose:
        console.print(Panel(f"Check interval: {status['check_interval']}s\n"
                          f"Auto-discovery: {status['auto_discover']}\n"
                          f"Enhanced detection: {status['enhanced_detection']}\n"
                          f"Log file: {status['log_file']}\n"
                          f"PID file: {status['pid_file']}",
                          title="Recovery Daemon Config", style="blue"))

    # Show agent health if daemon is running
    if status['running']:
        try:
            tmux = ctx.obj['tmux']
            config = Config()
            monitor = AgentMonitor(config, tmux)

            summary = monitor.get_monitoring_summary()

            if summary['total_agents'] > 0:
                console.print("\n[bold]Enhanced Agent Health Summary:[/bold]")
                console.print(f"  Total agents: {summary['total_agents']}")
                console.print(f"  [green]Healthy: {summary['healthy']}[/green]")
                console.print(f"  [yellow]Warning: {summary['warning']}[/yellow]")
                console.print(f"  [red]Critical: {summary['critical']}[/red]")
                console.print(f"  [red]Unresponsive: {summary['unresponsive']}[/red]")
                console.print(f"  [blue]Idle: {summary['idle']}[/blue]")
                console.print(f"  Recent recoveries: {summary['recent_recoveries']}")

                # Show detailed agent status
                if verbose:
                    unhealthy = monitor.get_unhealthy_agents()
                    if unhealthy:
                        table = Table(title="Detailed Agent Status")
                        table.add_column("Target", style="cyan")
                        table.add_column("Status", style="red")
                        table.add_column("Idle", style="blue")
                        table.add_column("Failures", style="yellow")
                        table.add_column("Activity", style="green")
                        table.add_column("Last Response", style="white")

                        for target, agent_status in unhealthy:
                            idle_status = "✓" if agent_status.is_idle else "✗"
                            table.add_row(
                                target,
                                agent_status.status,
                                idle_status,
                                str(agent_status.consecutive_failures),
                                str(agent_status.activity_changes),
                                agent_status.last_response.strftime("%H:%M:%S")
                            )

                        console.print("\n")
                        console.print(table)
            else:
                console.print("\n[yellow]No agents currently registered for monitoring[/yellow]")

        except Exception as e:
            console.print(f"\n[red]Error getting agent health status: {e}[/red]")


@monitor.command('recovery-logs')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--lines', '-n', default=20, help='Number of lines to show')
def recovery_logs(follow, lines):
    """View recovery daemon logs."""
    if not os.path.exists(RECOVERY_LOG_FILE):
        console.print("[yellow]No recovery log file found[/yellow]")
        return

    if follow:
        try:
            subprocess.run(['tail', '-f', RECOVERY_LOG_FILE])
        except KeyboardInterrupt:
            pass
    else:
        subprocess.run(['tail', f'-{lines}', RECOVERY_LOG_FILE])
