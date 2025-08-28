"""Monitoring commands with enhanced idle detection."""

from pathlib import Path

import click
from rich.console import Console

from .daemon_status import daemon_status
from .dashboard import show_dashboard
from .models import ConfigPath
from .pause_daemon import pause_daemon
from .performance import performance_monitor
from .recovery_logs import show_recovery_logs
from .recovery_start import recovery_start_daemon
from .recovery_status import recovery_status_info
from .recovery_stop import recovery_stop_daemon
from .show_logs import show_logs
from .start_daemon import start_daemon
from .stop_daemon import stop_daemon

console: Console = Console()

# Use project directory for storage
PROJECT_DIR = str(Path.cwd() / ".tmux_orchestrator")
LOGS_DIR = f"{PROJECT_DIR}/logs"
PID_FILE = f"{PROJECT_DIR}/idle-monitor.pid"
LOG_FILE = f"{LOGS_DIR}/idle-monitor.log"
RECOVERY_PID_FILE = f"{PROJECT_DIR}/recovery.pid"
RECOVERY_LOG_FILE = f"{LOGS_DIR}/recovery.log"

# Re-export for backwards compatibility
__all__ = [
    "monitor",  # Main CLI group
    "ConfigPath",
]


@click.group()
def monitor() -> None:
    """Advanced monitoring and health management for agent systems.

    Provides comprehensive monitoring capabilities for tmux-orchestrator,
    including daemon management, recovery systems, performance monitoring,
    and real-time dashboard views.

    Key Features:
    - Automated agent health monitoring with customizable intervals
    - Intelligent recovery daemon with failure detection
    - Real-time performance analysis and optimization
    - Interactive dashboard with session filtering
    - Comprehensive logging and status reporting

    Examples:
        tmux-orc monitor start              # Start monitoring daemon
        tmux-orc monitor dashboard          # Open monitoring dashboard
        tmux-orc monitor status --json      # Get system status
        tmux-orc monitor recovery-start     # Start recovery daemon
        tmux-orc monitor performance        # Analyze system performance

    The monitoring system operates at multiple levels:
    - Process monitoring for daemon health
    - Session monitoring for agent activity
    - Performance monitoring for system optimization
    - Recovery monitoring for automated failure handling
    """
    pass


# Import command functions and register them
@monitor.command()
@click.pass_context
@click.option("--interval", default=10, help="Check interval in seconds (minimum: 10)")
@click.option("--supervised", is_flag=True, help="Run in supervised mode (auto-restart, designed for systemd/launchd)")
@click.option("--json", is_flag=True, help="Output status in JSON format")
def start(ctx: click.Context, interval: int, supervised: bool, json: bool) -> None:
    """Start the monitoring daemon with enhanced idle detection."""

    start_daemon(ctx, interval, supervised, json)


@monitor.command()
@click.pass_context
@click.option("--json", is_flag=True, help="Output status in JSON format")
def stop(ctx: click.Context, json: bool) -> None:
    """Stop the monitoring daemon gracefully."""

    stop_daemon(ctx, json)


@monitor.command()
@click.option("--follow", "-f", is_flag=True, help="Follow log output (like tail -f)")
@click.option("--lines", "-n", default=20, help="Number of lines to show (default: 20)")
def logs(follow: bool, lines: int) -> None:
    """Show monitoring daemon logs with enhanced formatting."""

    show_logs(follow, lines)


@monitor.command()
@click.pass_context
@click.option("--json", is_flag=True, help="Output status in JSON format")
def status(ctx: click.Context, json: bool) -> None:
    """Show comprehensive monitoring daemon status."""

    daemon_status(ctx, json)


@monitor.command("pause")
@click.pass_context
@click.argument("seconds", type=int)
def pause(ctx: click.Context, seconds: int) -> None:
    """Temporarily pause monitoring daemon for specified seconds."""

    pause_daemon(ctx, seconds)


@monitor.command("recovery-start")
@click.pass_context
@click.option("--config", type=str, help="Custom recovery config file path (must be in allowed directories)")
def recovery_start(ctx: click.Context, config: str | None) -> None:
    """Start the agent recovery daemon with enhanced PM detection."""

    recovery_start_daemon(ctx, config)


@monitor.command("recovery-stop")
def recovery_stop() -> None:
    """Stop the agent recovery daemon."""

    recovery_stop_daemon()


@monitor.command("recovery-status")
@click.pass_context
@click.option("--verbose", "-v", is_flag=True, help="Show detailed recovery information")
def recovery_status(ctx: click.Context, verbose: bool) -> None:
    """Show agent recovery daemon status and recent activity."""

    recovery_status_info(ctx, verbose)


@monitor.command("recovery-logs")
@click.option("--follow", "-f", is_flag=True, help="Follow log output (like tail -f)")
@click.option("--lines", "-n", default=20, help="Number of lines to show (default: 20)")
def recovery_logs(follow: bool, lines: int) -> None:
    """Show agent recovery daemon logs."""

    show_recovery_logs(follow, lines)


@monitor.command()
@click.pass_context
@click.option("--session", "-s", help="Filter dashboard to specific session")
@click.option("--refresh", "-r", default=5, help="Refresh interval in seconds (default: 5)")
@click.option("--json", is_flag=True, help="Output dashboard data in JSON format")
def dashboard(ctx: click.Context, session: str | None, refresh: int, json: bool) -> None:
    """Interactive monitoring dashboard with real-time updates."""

    show_dashboard(ctx, session, refresh, json)


@monitor.command("performance")
@click.pass_context
@click.option("--agent-count", type=int, help="Expected number of agents for optimization")
@click.option("--analyze", is_flag=True, help="Analyze current performance and suggest optimizations")
@click.option("--optimize", is_flag=True, help="Apply recommended performance optimizations")
def performance(ctx: click.Context, agent_count: int | None, analyze: bool, optimize: bool) -> None:
    """Performance monitoring and optimization for high-load scenarios."""

    performance_monitor(ctx, agent_count, analyze, optimize)
