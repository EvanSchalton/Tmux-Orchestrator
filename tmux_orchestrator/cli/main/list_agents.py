"""List all active agents across sessions with comprehensive status."""

import click
from rich.console import Console
from rich.table import Table

console = Console()


def list_agents_command(ctx: click.Context, json: bool) -> None:
    """List all active agents across sessions with comprehensive status.

    <mcp>[LIST] Display all active agents across all tmux sessions.
    Parameters: kwargs (string) - 'action=list [options={"json": true}]'

    Examples:
    - List all agents: kwargs='action=list'
    - JSON format: kwargs='action=list options={"json": true}'

    Shows all agents system-wide. For team summaries use 'team list', for agent details use 'agent status'.</mcp>

    Provides a system-wide overview of all Claude agents currently running
    in tmux sessions, including their specializations, health status, and
    recent activity patterns.

    Examples:
        tmux-orc list                    # Show formatted agent overview
        tmux-orc list --json            # JSON output for scripts/monitoring

    Agent Information Displayed:
        • Session name and window location
        • Agent type and specialization
        • Current status (Active, Idle, Busy, Error)
        • Last activity timestamp
        • Response time and health metrics

    Status Indicators:
        🟢 Active:  Agent is responsive and working
        🟡 Idle:    Agent is waiting for tasks
        🔵 Busy:    Agent is processing complex work
        🔴 Error:   Agent encountered issues
        ⚫ Unknown: Status cannot be determined

    Use Cases:
        • System health monitoring
        • Resource utilization assessment
        • Identifying unresponsive agents
        • Planning team deployments
        • Integration with monitoring tools (JSON)

    If no agents are found, provides guidance on deploying teams.
    """
    from tmux_orchestrator.utils.tmux import TMUXManager

    tmux_optimized: TMUXManager = ctx.obj["tmux_optimized"]
    use_json: bool = json or ctx.obj.get("json_mode", False)

    agents = tmux_optimized.list_agents_ultra_optimized()

    if use_json:
        import json as json_module

        console.print(json_module.dumps(agents, indent=2))
        return

    if not agents:
        console.print("[yellow]No active agents found.[/yellow]")
        console.print("\nTo deploy agents, use: [bold]tmux-orc team deploy[/bold]")
        return

    table = Table(title=f"Active Agents ({len(agents)} total)")
    table.add_column("Session", style="cyan", width=12)
    table.add_column("Window", style="magenta", width=8)
    table.add_column("Type", style="green", width=15)
    table.add_column("Status", style="yellow", width=12)

    for agent in agents:
        table.add_row(agent["session"], str(agent["window"]), agent["type"], agent["status"])

    console.print(table)
    console.print("\nUse [bold]tmux-orc agent status[/bold] for detailed information")
