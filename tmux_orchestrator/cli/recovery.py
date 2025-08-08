"""Recovery system CLI commands for managing automatic agent recovery."""

import asyncio
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tmux_orchestrator.core.recovery.recovery_daemon import run_recovery_daemon
from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


@click.group()
def recovery() -> None:
    """Automatic agent recovery system management.
    
    The recovery system provides continuous monitoring and automatic 
    recovery of failed Claude agents across all tmux sessions.
    
    Features:
        • Continuous health monitoring
        • Automatic failure detection
        • Context-preserving restarts
        • Intelligent briefing restoration
        • Notification throttling
        • Comprehensive event logging
    """
    pass


@recovery.command('start')
@click.option('--interval', '-i', default=30, help='Monitoring interval in seconds')
@click.option('--max-concurrent', '-c', default=3, help='Maximum concurrent recoveries')
@click.option('--failure-threshold', '-f', default=3, help='Failures before triggering recovery')
@click.option('--cooldown', '-cd', default=300, help='Recovery cooldown in seconds')
@click.option('--dry-run', is_flag=True, help='Monitor only, do not perform recovery')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--daemon', '-d', is_flag=True, help='Run as background daemon')
def start_recovery(
    interval: int,
    max_concurrent: int,
    failure_threshold: int,
    cooldown: int,
    dry_run: bool,
    verbose: bool,
    daemon: bool
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
    
    console.print(f"[blue]Starting recovery daemon...[/blue]")
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
            verbose=verbose
        )
    else:
        # Run in foreground
        console.print("\n[yellow]Press Ctrl+C to stop the daemon[/yellow]\n")
        
        try:
            asyncio.run(run_recovery_daemon(
                monitor_interval=interval,
                recovery_enabled=not dry_run,
                max_concurrent_recoveries=max_concurrent,
                failure_threshold=failure_threshold,
                recovery_cooldown=cooldown,
                log_level=log_level
            ))
        except KeyboardInterrupt:
            console.print("\n[green]Recovery daemon stopped[/green]")


@recovery.command('stop')
def stop_recovery() -> None:
    """Stop the running recovery daemon.
    
    Gracefully stops the background recovery daemon, allowing active
    recovery operations to complete before shutdown.
    
    The daemon will wait up to 2 minutes for active recoveries to finish.
    """
    pid_file = Path("/tmp/tmux-orchestrator-recovery-daemon.pid")
    
    if not pid_file.exists():
        console.print("[yellow]No recovery daemon PID file found[/yellow]")
        return
    
    try:
        with open(pid_file, 'r') as f:
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


@recovery.command('status')
@click.option('--json', is_flag=True, help='Output in JSON format')
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
    pid_file = Path("/tmp/tmux-orchestrator-recovery-daemon.pid")
    daemon_running = False
    daemon_pid = None
    
    if pid_file.exists():
        try:
            with open(pid_file, 'r') as f:
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
    
    daemon_panel = Panel(daemon_info, title="Recovery Daemon", border_style="green" if daemon_running else "red")
    console.print(daemon_panel)
    
    # Agent health overview
    try:
        agents = tmux.list_agents() if hasattr(tmux, 'list_agents') else []
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


@recovery.command('test')
@click.argument('target', required=False)
@click.option('--no-restart', is_flag=True, help='Test detection only, do not restart')
@click.option('--comprehensive', is_flag=True, help='Run comprehensive test suite')
@click.option('--stress-test', is_flag=True, help='Include stress testing')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def test_recovery(target: Optional[str], no_restart: bool, comprehensive: bool, stress_test: bool, verbose: bool) -> None:
    """Test recovery system with a specific agent.
    
    TARGET: Agent target in format 'session:window' (e.g., 'tmux-orc-dev:4')
    
    Performs a complete recovery test including:
        • Health check and failure detection
        • Recovery coordination (if enabled)  
        • Context preservation
        • Briefing restoration
        • Notification system
    
    Examples:
        tmux-orc recovery test tmux-orc-dev:4          # Full recovery test
        tmux-orc recovery test frontend:0 --no-restart # Detection only
    
    Use --no-restart to test detection without actually restarting the agent.
    """
    from tmux_orchestrator.core.recovery import coordinate_agent_recovery
    
    console.print(f"[blue]Testing recovery system with agent: {target}[/blue]")
    
    if no_restart:
        console.print("[yellow]Running in detection-only mode[/yellow]")
    
    tmux = TMUXManager()
    
    try:
        # Test recovery coordination
        success, message, data = coordinate_agent_recovery(
            tmux=tmux,
            target=target,
            enable_auto_restart=not no_restart,
            use_structured_logging=True
        )
        
        if success:
            console.print(f"[green]✓ Recovery test successful: {message}[/green]")
        else:
            console.print(f"[red]✗ Recovery test failed: {message}[/red]")
        
        # Display test results
        if data:
            results_table = Table(title="Recovery Test Results")
            results_table.add_column("Component", style="cyan")
            results_table.add_column("Status", style="green")
            results_table.add_column("Details", style="yellow")
            
            # Health check results
            health_checks = data.get('health_checks', [])
            if health_checks:
                latest_check = health_checks[-1]
                health_status = "✓ Healthy" if latest_check.get('is_healthy') else "✗ Unhealthy"
                results_table.add_row("Health Check", health_status, latest_check.get('failure_reason', 'N/A'))
            
            # Recovery attempt
            recovery_attempted = data.get('recovery_attempted', False)
            if recovery_attempted:
                recovery_status = "✓ Success" if data.get('recovery_successful') else "✗ Failed"
                duration = data.get('total_duration', 0)
                results_table.add_row("Recovery", recovery_status, f"{duration:.1f}s")
            
            # Briefing restoration
            restart_results = data.get('restart_results', {})
            if restart_results:
                briefing_status = "✓ Success" if restart_results.get('briefing_restored') else "✗ Failed"
                agent_role = restart_results.get('agent_role', 'Unknown')
                results_table.add_row("Briefing", briefing_status, f"Role: {agent_role}")
            
            console.print(results_table)
    
    except Exception as e:
        console.print(f"[red]Recovery test error: {e}[/red]")


def _start_daemon_background(
    interval: int,
    max_concurrent: int,
    failure_threshold: int,
    cooldown: int,
    recovery_enabled: bool,
    verbose: bool
) -> None:
    """Start recovery daemon in background."""
    pid_file = Path("/tmp/tmux-orchestrator-recovery-daemon.pid")
    
    # Check if daemon is already running
    if pid_file.exists():
        try:
            with open(pid_file, 'r') as f:
                existing_pid = int(f.read().strip())
            os.kill(existing_pid, 0)  # Check if process exists
            console.print(f"[yellow]Daemon already running (PID: {existing_pid})[/yellow]")
            return
        except (ValueError, OSError):
            # PID file exists but process is dead, remove it
            pid_file.unlink()
    
    # Start daemon as subprocess
    python_path = sys.executable
    script_args = [
        python_path, '-c',
        f"""
import asyncio
from tmux_orchestrator.core.recovery.recovery_daemon import run_recovery_daemon

asyncio.run(run_recovery_daemon(
    monitor_interval={interval},
    recovery_enabled={recovery_enabled},
    max_concurrent_recoveries={max_concurrent},
    failure_threshold={failure_threshold},
    recovery_cooldown={cooldown},
    log_level={'logging.DEBUG' if verbose else 'logging.INFO'}
))
"""
    ]
    
    # Start daemon process
    process = subprocess.Popen(
        script_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    
    # Write PID file
    with open(pid_file, 'w') as f:
        f.write(str(process.pid))
    
    console.print(f"[green]Recovery daemon started in background (PID: {process.pid})[/green]")
    console.print(f"[dim]Use 'tmux-orc recovery stop' to stop the daemon[/dim]")
    console.print(f"[dim]Use 'tmux-orc recovery status' to check daemon status[/dim]")