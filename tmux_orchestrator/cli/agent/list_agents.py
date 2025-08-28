"""List all active agents with filtering options."""

import click
from rich.console import Console
from rich.table import Table

console = Console()


def list_all_agents(ctx: click.Context, session: str, json: bool) -> None:
    """List all active agents with filtering options."""
    from tmux_orchestrator.utils.tmux import TMUXManager

    tmux: TMUXManager = ctx.obj["tmux"]

    try:
        # Get list of sessions, filter by session if specified
        sessions = tmux.list_sessions()

        if session:
            sessions = [s for s in sessions if session in s]

        if json:
            import json as json_module

            result = {
                "agents": sessions,
                "count": len(sessions),
                "filter": session,
                "timestamp": __import__("time").time(),
            }
            console.print(json_module.dumps(result, indent=2))
        else:
            table = Table(title=f"Active Agents{f' (filtered: {session})' if session else ''}")
            table.add_column("Agent", style="cyan")
            table.add_column("Status", style="green")

            for agent_session in sessions:
                table.add_row(str(agent_session), "Active")

            console.print(table)
            console.print(f"\nTotal agents: {len(sessions)}")

    except Exception as e:
        if json:
            import json as json_module

            result = {"success": False, "error": str(e)}
            console.print(json_module.dumps(result, indent=2))
        else:
            console.print(f"[red]✗ Error listing agents: {e}[/red]")
