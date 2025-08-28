"""Status command - Display comprehensive system status dashboard."""

import json
from datetime import datetime, timezone

import click

from tmux_orchestrator.core.monitoring.status_writer import StatusWriter
from tmux_orchestrator.utils.tmux import TMUXManager


def system_status(ctx: click.Context, json_format: bool) -> None:
    """Display comprehensive system status dashboard with intelligent caching.

    <mcp>Show comprehensive system status dashboard (output: rich table or JSON). Displays sessions, agents, daemon health with intelligent caching. Use for system health overview. Different from 'list' (agent-focused) and 'agent status' (individual agents).</mcp>

    Provides a sophisticated real-time view of the entire TMUX Orchestrator
    ecosystem with automatic performance optimization through daemon-based
    status caching and intelligent freshness detection.

    Status Data Sources:
        Primary (Cached): Real-time daemon-maintained status file
        - Updated every 15 seconds by monitoring daemon
        - Atomic writes ensure data consistency
        - Sub-second response times for dashboard queries
        - Includes agent states, daemon health, and performance metrics

        Fallback (Live): Direct TMUX query when cache unavailable
        - Used when daemon not running or data stale (>30s)
        - Higher latency but always current
        - Graceful degradation ensures reliability

    Health Status Indicators:
        🟢 Healthy:    All systems operational, no issues detected
        🟡 Warning:    Minor issues (stale cache, slow responses)
        🔴 Critical:   Major problems (daemon failures, agent crashes)
        ⚫ Offline:    System components not responding
        🔵 Busy:       Agents processing complex tasks
    """

    console = ctx.obj["console"]
    tmux_optimized: TMUXManager = ctx.obj["tmux_optimized"]
    use_json: bool = json_format or ctx.obj.get("json_mode", False)

    # Try to read from status file first for better performance
    status_writer = StatusWriter()
    status_data = status_writer.read_status()

    using_cached_status = False
    freshness_warning = None

    if status_data:
        # Check freshness - warn if status is older than 30 seconds
        try:
            last_updated = datetime.fromisoformat(status_data["last_updated"].replace("Z", "+00:00"))
            age_seconds = (datetime.now(timezone.utc) - last_updated).total_seconds()

            if age_seconds < 30:
                # Use cached status for better performance
                using_cached_status = True
                sessions = tmux_optimized.list_sessions_cached()

                # Convert status file format to expected agent format
                agents = []
                for target, agent_info in status_data.get("agents", {}).items():
                    agents.append(
                        {
                            "target": target,
                            "name": agent_info.get("name", "unknown"),
                            "type": agent_info.get("type", "unknown"),
                            "status": agent_info.get("status", "unknown").capitalize(),
                            "session": agent_info.get("session"),
                            "window": agent_info.get("window"),
                        }
                    )
            else:
                freshness_warning = f"Status data is {int(age_seconds)}s old, gathering fresh data..."
        except Exception:
            pass

    # Fall back to live query if no cached status or it's stale
    if not using_cached_status:
        sessions = tmux_optimized.list_sessions_cached()
        agents = tmux_optimized.list_agents_ultra_optimized()

    if use_json:
        output_data = {
            "sessions": sessions,
            "agents": agents,
            "summary": {
                "total_sessions": len(sessions),
                "total_agents": len(agents),
                "active_agents": len([a for a in agents if a["status"] == "Active"]),
            },
        }

        # Add daemon status if available
        if using_cached_status and status_data:
            output_data["daemon_status"] = status_data.get("daemon_status", {})
            output_data["status_age_seconds"] = int(  # type: ignore[assignment]
                (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(status_data["last_updated"].replace("Z", "+00:00"))
                ).total_seconds()
            )

        console.print(json.dumps(output_data, indent=2))
        return

    # Display rich status dashboard
    console.print("\n[bold blue]TMUX Orchestrator System Status[/bold blue]")
    console.print("=" * 50)

    # Show freshness warning if needed
    if freshness_warning:
        console.print(f"\n[yellow]⚠️  {freshness_warning}[/yellow]")
    elif using_cached_status:
        console.print("\n[green]✓ Using cached status from monitoring daemon[/green]")

    # Sessions summary
    if sessions:
        console.print(f"\n[bold]Sessions ({len(sessions)} active):[/bold]")
        for session in sessions[:5]:  # Show top 5
            attached = "✓" if session.get("attached") == "1" else "○"
            console.print(f"  {attached} {session['name']}")
        if len(sessions) > 5:
            console.print(f"  ... and {len(sessions) - 5} more sessions")
    else:
        console.print("\n[yellow]No active sessions found[/yellow]")

    # Agents summary
    if agents:
        console.print(f"\n[bold]Agents ({len(agents)} active):[/bold]")
        status_counts: dict[str, int] = {}
        for agent in agents:
            status_counts[agent["status"]] = status_counts.get(agent["status"], 0) + 1

        for status, count in status_counts.items():
            color = "green" if status == "Active" else "yellow" if status == "Idle" else "red"
            console.print(f"  [{color}]{status}: {count}[/{color}]")
    else:
        console.print("\n[yellow]No active agents found[/yellow]")

    # Show daemon status if available from status file
    if using_cached_status and status_data:
        daemon_status = status_data.get("daemon_status", {})
        if daemon_status:
            console.print("\n[bold]Daemon Status:[/bold]")

            # Monitor daemon
            monitor = daemon_status.get("monitor", {})
            if monitor.get("running"):
                uptime = monitor.get("uptime_seconds", 0)
                uptime_str = (
                    f"{uptime // 3600}h {(uptime % 3600) // 60}m"
                    if uptime > 3600
                    else f"{uptime // 60}m {uptime % 60}s"
                )
                console.print(
                    f"  [green]✓ Monitor: Running (PID: {monitor.get('pid', 'N/A')}, uptime: {uptime_str})[/green]"
                )
            else:
                console.print("  [red]✗ Monitor: Not running[/red]")

            # Messaging daemon
            messaging = daemon_status.get("messaging", {})
            if messaging.get("running"):
                console.print(f"  [green]✓ Messaging: Running (PID: {messaging.get('pid', 'N/A')})[/green]")
            else:
                console.print("  [yellow]○ Messaging: Not running[/yellow]")

    console.print("\nUse [bold]tmux-orc team status <session>[/bold] for detailed team info")
