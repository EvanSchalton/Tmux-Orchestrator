"""Show detailed status of all agents across sessions."""

import json as json_module

import click
from rich.console import Console
from rich.table import Table

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


def show_agent_status(ctx: click.Context, target: str, json: bool) -> None:
    """Show detailed status of all agents across sessions or a specific agent."""
    tmux: TMUXManager = ctx.obj["tmux"]

    try:
        # Get agent status information
        if target:
            # Show status for specific target
            if ":" not in target:
                if json:
                    result = {"success": False, "error": f"Invalid target format: {target}. Use 'session:window'"}
                    console.print(json_module.dumps(result, indent=2))
                else:
                    console.print(f"[red]✗ Invalid target format: {target}. Use 'session:window'[/red]")
                return

            session, window_str = target.split(":", 1)
            try:
                window_num = int(window_str)
                # Check if session exists and get windows
                windows = tmux.list_windows(session)
                window_found = any(w["index"] == window_num for w in windows)

                if json:
                    status_data = {
                        "target": target,
                        "session": session,
                        "window": window_str,
                        "status": "Active" if window_found else "Not Found",
                        "timestamp": __import__("time").time(),
                    }
                    console.print(json_module.dumps(status_data, indent=2))
                else:
                    status = "Active" if window_found else "Not Found"
                    console.print(f"Agent {target}: {status}")
            except ValueError:
                if json:
                    result = {"success": False, "error": f"Invalid window number in target: {target}"}
                    console.print(json_module.dumps(result, indent=2))
                else:
                    console.print(f"[red]✗ Invalid window number in target: {target}[/red]")
        else:
            # Show status for all agents
            sessions = tmux.list_sessions()
            # Sessions can be list of dicts or list of strings
            from typing import Any

            sessions_list: list[Any] = sessions

            if json:
                status_data = {
                    "sessions": sessions,
                    "total_agents": len(sessions),
                    "timestamp": __import__("time").time(),
                }
                console.print(json_module.dumps(status_data, indent=2))
            else:
                table = Table(title="Agent Status")
                table.add_column("Session", style="cyan")
                table.add_column("Status", style="green")

                for session in sessions_list:
                    session_name = session.get("name", str(session)) if isinstance(session, dict) else str(session)
                    table.add_row(session_name, "Active")

                console.print(table)

    except Exception as e:
        if json:
            result = {"success": False, "error": str(e)}
            console.print(json_module.dumps(result, indent=2))
        else:
            console.print(f"[red]✗ Error getting agent status: {e}[/red]")
