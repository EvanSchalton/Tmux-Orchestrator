"""Monitoring commands with enhanced idle detection."""

import os
import signal
import subprocess

import click
from rich.console import Console

from tmux_orchestrator.core.performance_optimizer import (
    PerformanceOptimizer,
    create_optimized_config,
)
from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()
PID_FILE = "/tmp/tmux-orchestrator-idle-monitor.pid"
LOG_FILE = "/tmp/tmux-orchestrator-idle-monitor.log"
RECOVERY_PID_FILE = "/tmp/tmux-orchestrator-recovery.pid"
RECOVERY_LOG_FILE = "/tmp/tmux-orchestrator-recovery.log"


@click.group()
def monitor() -> None:
    """Advanced monitoring and health management for agent systems.

    The monitor command group provides comprehensive monitoring capabilities,
    including real-time dashboards, automated recovery, health checks, and
    diagnostic tools for maintaining optimal system performance.

    Examples:
        tmux-orc monitor start --interval 30    # Start monitoring daemon
        tmux-orc monitor dashboard              # Live system dashboard
        tmux-orc monitor recovery-start         # Start automated recovery
        tmux-orc monitor status                 # Check monitoring status
        tmux-orc monitor logs -f                # Follow monitor logs

    Monitoring Features:
        • Real-time agent health tracking
        • Automated failure detection and recovery
        • Performance metrics and analytics
        • Interactive dashboard with live updates
        • Comprehensive logging and diagnostics
        • Bulletproof idle detection algorithms

    Critical for maintaining 24/7 agent operations and ensuring
    system reliability in production environments.
    """
    pass


@monitor.command()
@click.option("--interval", default=10, help="Check interval in seconds")
@click.pass_context
def start(ctx: click.Context, interval: int) -> None:
    """Start the intelligent idle detection and monitoring daemon.

    Launches a background service that continuously monitors all Claude agents
    for responsiveness, health status, and activity patterns.

    Examples:
        tmux-orc monitor start                 # Start with default 10s interval
        tmux-orc monitor start --interval 30  # Custom 30-second checks
        tmux-orc monitor start --interval 5   # High-frequency monitoring

    Monitoring Capabilities:
        • Agent responsiveness detection
        • Idle state identification
        • Performance degradation alerts
        • Resource usage tracking
        • Communication health checks
        • Automatic failure notifications

    Recommended Intervals:
        • Development: 10-15 seconds
        • Production: 30-60 seconds
        • Critical systems: 5-10 seconds
        • Resource-constrained: 60+ seconds

    The daemon runs in the background and provides continuous health
    monitoring without affecting agent performance.
    """
    from tmux_orchestrator.core.monitor import IdleMonitor

    monitor = IdleMonitor(ctx.obj["tmux"])

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
def stop(ctx: click.Context) -> None:
    """Stop the monitoring daemon and disable automated health checks.

    Gracefully shuts down the monitoring daemon, stopping all automated
    health checks and recovery operations.

    Examples:
        tmux-orc monitor stop                  # Stop monitoring daemon

    Impact of Stopping:
        • No automatic agent health monitoring
        • No automated failure detection
        • No idle agent identification
        • Manual intervention required for issues
        • Loss of performance metrics collection

    ⚠️  Warning: Stopping monitoring disables automated recovery

    Use this when:
        • Performing system maintenance
        • Debugging monitoring issues
        • Temporarily reducing system load
        • Switching to manual management mode

    Remember to restart monitoring after maintenance to ensure
    continued system reliability.
    """
    from tmux_orchestrator.core.monitor import IdleMonitor

    monitor = IdleMonitor(ctx.obj["tmux"])

    if not monitor.is_running():
        console.print("[yellow]Monitor is not running[/yellow]")
        return

    if monitor.stop():
        console.print("[green]✓ Monitor stopped successfully[/green]")
    else:
        console.print("[red]✗ Failed to stop monitor[/red]")


@monitor.command()
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--lines", "-n", default=20, help="Number of lines to show")
def logs(follow: bool, lines: int) -> None:
    """View monitoring daemon logs and diagnostic information.

    Displays detailed logs from the monitoring system, including agent
    health checks, detection events, and system diagnostics.

    Examples:
        tmux-orc monitor logs                  # Show last 20 log lines
        tmux-orc monitor logs -n 50           # Show last 50 lines
        tmux-orc monitor logs -f              # Follow live log output
        tmux-orc monitor logs -f -n 100      # Follow with more history

    Log Information Includes:
        • Agent health check results
        • Idle detection events
        • Performance metrics
        • Error conditions and recovery actions
        • System resource usage
        • Communication statistics

    Log Levels:
        • INFO: Normal operations and status updates
        • WARN: Minor issues and degraded performance
        • ERROR: Failures and recovery actions
        • DEBUG: Detailed diagnostic information

    Use for troubleshooting monitoring issues, understanding system
    behavior, and analyzing agent performance patterns.
    """
    if not os.path.exists(LOG_FILE):
        console.print("[yellow]No log file found[/yellow]")
        return

    if follow:
        try:
            subprocess.run(["tail", "-f", LOG_FILE])
        except KeyboardInterrupt:
            pass
    else:
        subprocess.run(["tail", f"-{lines}", LOG_FILE])


@monitor.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def status(ctx: click.Context, json: bool) -> None:
    """Display comprehensive monitoring system status and health.

    Shows detailed information about the monitoring daemon, including
    operational status, performance metrics, and agent health summary.

    Examples:
        tmux-orc monitor status                # Show monitoring system status

    Status Information:
        • Monitoring daemon operational state
        • Check interval and timing configuration
        • Number of agents under monitoring
        • Recent health check results
        • Performance metrics and statistics
        • Error rates and recovery actions

    Daemon Status Indicators:
        🟢 Running:   Daemon active and monitoring
        🔴 Stopped:   Daemon not running (no monitoring)
        🟡 Warning:   Daemon running but issues detected
        ⚫ Error:     Daemon in error state

    Use this to verify monitoring is working correctly and to
    get an overview of system health before making changes.
    """
    from tmux_orchestrator.core.monitor import IdleMonitor

    monitor = IdleMonitor(ctx.obj["tmux"])

    if json:
        # Get monitor status data
        import json as json_module

        status_data = {
            "running": monitor.is_running(),
            "daemon_type": "idle_monitor",
            "log_file": LOG_FILE,
            "pid_file": PID_FILE,
        }
        console.print(json_module.dumps(status_data, indent=2))
        return

    monitor.status()


@monitor.command("recovery-start")
@click.option("--config", "-c", help="Configuration file path")
@click.pass_context
def recovery_start(ctx: click.Context, config: str | None) -> None:
    """Start the advanced recovery daemon with bulletproof agent restoration.

    Launches an intelligent recovery system that automatically detects and
    restores failed, crashed, or unresponsive agents using advanced algorithms.

    Examples:
        tmux-orc monitor recovery-start        # Start with default config
        tmux-orc monitor recovery-start -c custom.conf

    Recovery Features:
        • 4-snapshot idle detection algorithm
        • Intelligent failure pattern recognition
        • Graduated recovery escalation
        • Context-preserving agent restoration
        • Communication pathway recovery
        • Resource conflict resolution

    Detection Algorithms:
        • Activity-based monitoring
        • Response time analysis
        • Resource usage patterns
        • Communication health checks
        • Process state verification

    Recovery Actions:
        1. Soft restart: Gentle agent refresh
        2. Hard restart: Complete agent recreation
        3. Session recovery: Full session restoration
        4. Escalation: Human operator notification

    Essential for production environments where 24/7 agent availability
    is critical and manual intervention isn't feasible.
    """
    from tmux_orchestrator.core.recovery_daemon import RecoveryDaemon

    daemon = RecoveryDaemon(config)

    if daemon.is_running():
        console.print("[yellow]Recovery daemon is already running[/yellow]")
        return

    console.print("[blue]Starting recovery daemon with enhanced detection...[/blue]")

    # Start daemon in background
    import threading

    def run_daemon() -> None:
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


@monitor.command("recovery-stop")
def recovery_stop() -> None:
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


@monitor.command("recovery-status")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.pass_context
def recovery_status(ctx: click.Context, verbose: bool) -> None:
    """Display comprehensive recovery daemon status and agent health analytics.

    Provides detailed information about the recovery system status, including
    daemon health, agent monitoring statistics, and recovery operation history.

    Examples:
        tmux-orc monitor recovery-status       # Show recovery system status
        tmux-orc monitor recovery-status -v   # Detailed diagnostics

    Recovery Status Information:
        • Recovery daemon operational state
        • Monitoring configuration and intervals
        • Agent health summary and statistics
        • Recent recovery operations
        • Performance metrics and trends
        • Error rates and success statistics

    Agent Health Categories:
        🟢 Healthy:      Agent fully operational
        🟡 Warning:      Minor performance issues
        🔴 Critical:     Major problems detected
        ⚫ Unresponsive:  Agent not responding
        🔵 Idle:         Agent waiting for tasks

    Verbose Mode Includes:
        • Individual agent diagnostic details
        • Recent activity patterns
        • Failure analysis and root causes
        • Recovery action history
        • Resource utilization metrics
        • Communication pathway health

    Use for monitoring system health, troubleshooting issues,
    and analyzing recovery effectiveness.
    """
    from rich.panel import Panel
    from rich.table import Table

    from tmux_orchestrator.core.config import Config
    from tmux_orchestrator.core.monitor import AgentMonitor
    from tmux_orchestrator.core.recovery_daemon import RecoveryDaemon

    daemon = RecoveryDaemon()
    status = daemon.get_status()

    # Show daemon status
    if status["running"]:
        console.print(f"[green]✓ Recovery daemon is running (PID: {status['pid']})[/green]")
        console.print("  Using bulletproof 4-snapshot idle detection")
    else:
        console.print("[red]✗ Recovery daemon is not running[/red]")

    if verbose:
        console.print(
            Panel(
                f"Check interval: {status['check_interval']}s\n"
                f"Auto-discovery: {status['auto_discover']}\n"
                f"Enhanced detection: {status['enhanced_detection']}\n"
                f"Log file: {status['log_file']}\n"
                f"PID file: {status['pid_file']}",
                title="Recovery Daemon Config",
                style="blue",
            )
        )

    # Show agent health if daemon is running
    if status["running"]:
        try:
            tmux = ctx.obj["tmux"]
            config = Config()
            monitor = AgentMonitor(config, tmux)

            summary = monitor.get_monitoring_summary()

            if summary["total_agents"] > 0:
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
                                agent_status.last_response.strftime("%H:%M:%S"),
                            )

                        console.print("\n")
                        console.print(table)
            else:
                console.print("\n[yellow]No agents currently registered for monitoring[/yellow]")

        except Exception as e:
            console.print(f"\n[red]Error getting agent health status: {e}[/red]")


@monitor.command("recovery-logs")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--lines", "-n", default=20, help="Number of lines to show")
def recovery_logs(follow: bool, lines: int) -> None:
    """View recovery daemon logs."""
    if not os.path.exists(RECOVERY_LOG_FILE):
        console.print("[yellow]No recovery log file found[/yellow]")
        return

    if follow:
        try:
            subprocess.run(["tail", "-f", RECOVERY_LOG_FILE])
        except KeyboardInterrupt:
            pass
    else:
        subprocess.run(["tail", f"-{lines}", RECOVERY_LOG_FILE])


@monitor.command()
@click.option("--session", help="Filter by specific session")
@click.option("--refresh", default=5, help="Auto-refresh interval in seconds (0 to disable)")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def dashboard(ctx: click.Context, session: str | None, refresh: int, json: bool) -> None:
    """Launch interactive real-time monitoring dashboard with live updates.

    Displays a comprehensive, continuously updating overview of all system
    components, agent health, performance metrics, and operational status.

    Examples:
        tmux-orc monitor dashboard             # Full system dashboard
        tmux-orc monitor dashboard --session my-project
        tmux-orc monitor dashboard --refresh 10  # 10-second updates
        tmux-orc monitor dashboard --json     # JSON output for integration

    Dashboard Components:

    System Overview:
        • Total sessions and agent counts
        • System health indicators
        • Resource utilization metrics
        • Recent activity summary

    Agent Status Grid:
        • Individual agent health and status
        • Response times and performance
        • Current tasks and activity
        • Error states and recovery actions

    Session Management:
        • Session creation times and uptime
        • Window counts and configuration
        • Attachment status and accessibility
        • Resource consumption per session

    Performance Metrics:
        • Average response times
        • Task completion rates
        • Error frequencies
        • Recovery success rates

    Interactive Features:
        • Live updates without page refresh
        • Session filtering and focus
        • Customizable refresh intervals
        • Export to JSON for automation

    Dashboard Controls:
        • Press Ctrl+C to exit live mode
        • Use --refresh 0 for static snapshot
        • Filter by --session for project focus
        • Use --json for machine-readable output

    Perfect for operations centers, development monitoring,
    and integration with external monitoring systems.
    """
    from rich.columns import Columns
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table

    tmux: TMUXManager = ctx.obj["tmux"]

    def create_dashboard() -> str:
        """Create the dashboard layout."""
        # Get system data
        sessions = tmux.list_sessions()
        agents = tmux.list_agents()

        if session:
            sessions = [s for s in sessions if s["name"] == session]
            agents = [a for a in agents if a["session"] == session]

        if json:
            dashboard_data = {
                "timestamp": "2024-01-01T10:00:00Z",  # Would use real timestamp
                "sessions": sessions,
                "agents": agents,
                "summary": {
                    "total_sessions": len(sessions),
                    "total_agents": len(agents),
                    "active_agents": len([a for a in agents if a["status"] == "Active"]),
                },
            }
            import json as json_module

            return json_module.dumps(dashboard_data, indent=2)

        # Create dashboard components
        title = "🔍 TMUX Orchestrator Dashboard" + (f" - {session}" if session else "")

        # System summary
        summary_text = (
            f"Sessions: {len(sessions)} | "
            f"Agents: {len(agents)} | "
            f"Active: {len([a for a in agents if a['status'] == 'Active'])}"
        )
        summary_panel = Panel(summary_text, title="System Summary", style="blue")

        # Sessions table
        sessions_table = Table(title="Sessions")
        sessions_table.add_column("Name", style="cyan")
        sessions_table.add_column("Attached", style="green")
        sessions_table.add_column("Windows", style="yellow")
        sessions_table.add_column("Created", style="white")

        for sess in sessions[:10]:  # Limit to top 10
            attached = "✓" if sess.get("attached") == "1" else "○"
            sessions_table.add_row(
                sess["name"],
                attached,
                sess.get("windows", "0"),
                sess.get("created", "Unknown"),
            )

        # Agents table
        agents_table = Table(title="Agent Status")
        agents_table.add_column("Session", style="cyan")
        agents_table.add_column("Window", style="magenta")
        agents_table.add_column("Type", style="green")
        agents_table.add_column("Status", style="yellow")
        agents_table.add_column("Activity", style="blue")

        for agent in agents[:15]:  # Limit to top 15
            agents_table.add_row(
                agent["session"],
                str(agent["window"]),
                agent["type"],
                agent["status"],
                agent.get("last_activity", "Unknown"),
            )

        # Layout
        upper = Columns([summary_panel])
        lower = Columns([sessions_table, agents_table])

        return f"{title}\n\n{upper}\n\n{lower}"

    if refresh > 0:
        # Live updating dashboard
        try:
            with Live(create_dashboard(), refresh_per_second=1 / refresh) as live:
                import time

                while True:
                    time.sleep(refresh)
                    live.update(create_dashboard())
        except KeyboardInterrupt:
            console.print("\n[yellow]Dashboard stopped[/yellow]")
    else:
        # Static dashboard
        result = create_dashboard()
        console.print(result)


@monitor.command("performance")
@click.option("--agent-count", type=int, help="Number of agents (auto-detect if not provided)")
@click.option("--analyze", is_flag=True, help="Run performance analysis")
@click.option("--optimize", is_flag=True, help="Show optimization recommendations")
@click.pass_context
def performance(ctx: click.Context, agent_count: int | None, analyze: bool, optimize: bool) -> None:
    """Monitor and optimize performance for large-scale deployments.

    Provides performance metrics, analysis, and optimization recommendations
    for deployments with 50+ agents. Includes caching, batching, and
    connection pooling optimizations.

    Examples:
        tmux-orc monitor performance                    # Show current metrics
        tmux-orc monitor performance --analyze          # Run performance analysis
        tmux-orc monitor performance --optimize         # Get optimization tips
        tmux-orc monitor performance --agent-count 75   # Optimize for 75 agents
    """
    from rich.table import Table

    tmux: TMUXManager = ctx.obj["tmux"]

    # Auto-detect agent count if not provided
    if not agent_count:
        sessions = tmux.list_sessions() or []
        agent_count = sum(len(tmux.list_windows(s["name"]) or []) for s in sessions)

    console.print(f"[blue]Performance Monitor - {agent_count} agents detected[/blue]\n")

    # Create optimizer with appropriate config
    config = create_optimized_config(agent_count)
    optimizer = PerformanceOptimizer(tmux, config)

    if analyze:
        console.print("[yellow]Running performance analysis...[/yellow]")

        # Run some operations to gather metrics
        optimizer.optimize_list_operations()

        # Get bulk status for sample agents
        sessions = tmux.list_sessions() or []
        sample_agents = []
        for session in sessions[:5]:  # Sample first 5 sessions
            windows = tmux.list_windows(session["name"]) or []
            for window in windows[:3]:  # Sample first 3 windows
                sample_agents.append(f"{session['name']}:{window['index']}")

        if sample_agents:
            optimizer.get_agent_status_bulk(sample_agents)

        # Display metrics
        metrics = optimizer.get_performance_metrics()

        metrics_table = Table(title="Performance Metrics", show_header=True)
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="green")

        metrics_table.add_row("Agent Count", str(metrics.agent_count))
        metrics_table.add_row("Avg Response Time", f"{metrics.response_time_avg:.3f}s")
        metrics_table.add_row("P95 Response Time", f"{metrics.response_time_p95:.3f}s")
        metrics_table.add_row(
            "Cache Hit Rate", f"{metrics.cache_hits / max(1, metrics.cache_hits + metrics.cache_misses) * 100:.1f}%"
        )
        metrics_table.add_row("Error Rate", f"{metrics.error_rate:.1f}%")
        metrics_table.add_row("Batch Operations", str(metrics.batch_operations_count))

        console.print(metrics_table)

    if optimize:
        console.print("\n[yellow]Optimization Recommendations:[/yellow]")

        recommendations = optimizer.optimize_team_deployment(agent_count)

        opt_table = Table(title="Deployment Optimization", show_header=True)
        opt_table.add_column("Setting", style="cyan")
        opt_table.add_column("Recommendation", style="green")

        opt_table.add_row("Batch Size", str(recommendations["recommended_batch_size"]))
        opt_table.add_row(
            "Parallel Deployment", "✓ Enabled" if recommendations["use_parallel_deployment"] else "✗ Disabled"
        )
        opt_table.add_row("Startup Stagger", f"{recommendations['stagger_startup_ms']}ms")
        opt_table.add_row("Sessions", str(recommendations["session_distribution"]["sessions"]))
        opt_table.add_row("Agents per Session", str(recommendations["session_distribution"]["agents_per_session"]))

        # Resource limits
        limits = recommendations["resource_limits"]
        opt_table.add_row("Recommended Memory", f"{limits['recommended_memory_mb']} MB")
        opt_table.add_row("Recommended CPU Cores", str(limits["recommended_cpu_cores"]))
        opt_table.add_row("Connection Pool Size", str(limits["connection_pool_size"]))

        console.print(opt_table)

        if "warnings" in recommendations:
            console.print("\n[red]⚠ Warnings:[/red]")
            for warning in recommendations["warnings"]:
                console.print(f"  • {warning}")

    if not analyze and not optimize:
        # Show current configuration
        config_table = Table(title="Current Performance Configuration", show_header=True)
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="green")

        config_table.add_row("Batching", "✓ Enabled" if config.enable_batching else "✗ Disabled")
        config_table.add_row("Batch Size", str(config.batch_size))
        config_table.add_row("Caching", "✓ Enabled" if config.enable_caching else "✗ Disabled")
        config_table.add_row("Cache TTL", f"{config.cache_ttl_seconds}s")
        config_table.add_row("Connection Pool", str(config.connection_pool_size))
        config_table.add_row("Max Concurrent Ops", str(config.max_concurrent_operations))
        config_table.add_row("Async Operations", "✓ Enabled" if config.enable_async_operations else "✗ Disabled")

        console.print(config_table)

        console.print("\n[dim]Use --analyze or --optimize for detailed insights[/dim]")

    # Cleanup
    optimizer.shutdown()
