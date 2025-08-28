"""Terminate all agents across all sessions."""

import json
from typing import Any

import click
from rich.console import Console

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


def kill_all_agents_command(ctx: click.Context, force: bool, json_format: bool) -> None:
    """Terminate all agents across all sessions.
    This command kills ALL Claude agents in ALL tmux sessions.
    Use with extreme caution as it will terminate all active work.
    Options:
        --force: Skip the confirmation prompt (dangerous!)
        --json: Output results in JSON format
    Examples:
        tmux-orc agent kill-all                # Kill all agents (with confirmation)
        tmux-orc agent kill-all --force        # Kill all agents without confirmation
        tmux-orc agent kill-all --json         # Kill all agents and output JSON
    ⚠️  WARNING:
        - This terminates ALL agents in ALL sessions
        - All agent contexts and conversations will be lost
        - Cannot be undone
    Safety Features:
        - Requires explicit confirmation (unless --force)
        - Shows count of agents to be killed
        - Lists all affected sessions before proceeding
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Get all agents
    agents = tmux.list_agents()
    if not agents:
        message = "No agents found to kill"
        if json_format:
            result = {"success": True, "message": message, "agents_killed": 0, "sessions_affected": []}
            console.print(json.dumps(result, indent=2))
            return
        console.print(f"[yellow]{message}[/yellow]")
        return

    # Group agents by session
    sessions_dict: dict[str, list[dict[str, Any]]] = {}
    for agent in agents:
        session = agent["session"]
        if session not in sessions_dict:
            sessions_dict[session] = []
        sessions_dict[session].append(agent)

    # Show warning and get confirmation
    if not force:
        console.print("\n[bold red]⚠️  WARNING: Kill All Agents[/bold red]")
        console.print(f"This will terminate {len(agents)} agent(s) across {len(sessions_dict)} session(s):")
        console.print()

        # List all affected sessions and agents
        for session, session_agents in sessions_dict.items():
            console.print(f"  Session: [cyan]{session}[/cyan]")
            for agent in session_agents:
                console.print(f"    - Window {agent['window']}: {agent['type']}")

        console.print("\n[red]All agent contexts and conversations will be lost.[/red]")
        if not click.confirm("\nAre you sure you want to kill ALL agents?", default=False):
            message = "Kill-all operation cancelled"
            if json_format:
                result = {"success": False, "message": message, "agents_killed": 0, "sessions_affected": []}
                console.print(json.dumps(result, indent=2))
                return
            console.print(f"[yellow]{message}[/yellow]")
            return

    # Kill all agents
    if not json:
        console.print("[yellow]Killing all agents...[/yellow]")

    killed_count = 0
    failed_kills = []
    sessions_affected = set()

    for agent in agents:
        target = f"{agent['session']}:{agent['window']}"
        try:
            if tmux.kill_window(target):
                killed_count += 1
                sessions_affected.add(agent["session"])
            else:
                failed_kills.append(target)
        except Exception as e:
            failed_kills.append(f"{target} (error: {str(e)})")

    # Prepare result
    success = killed_count == len(agents)
    if success:
        status_message = f"Successfully killed all {killed_count} agent(s)"
    else:
        status_message = f"Killed {killed_count}/{len(agents)} agent(s)"
        if failed_kills:
            status_message += f". Failed: {', '.join(failed_kills)}"

    result_data = {
        "success": success,
        "message": status_message,
        "agents_killed": killed_count,
        "sessions_affected": list(sessions_affected),
        "total_agents": len(agents),
    }

    if failed_kills:
        result_data["failed_kills"] = failed_kills

    if json_format:
        console.print(json.dumps(result_data, indent=2))
    else:
        if success:
            console.print(f"[green]✓ {status_message}[/green]")
        else:
            console.print(f"[red]✗ {status_message}[/red]")
        if sessions_affected:
            console.print(f"[dim]Sessions affected: {', '.join(sorted(sessions_affected))}[/dim]")
