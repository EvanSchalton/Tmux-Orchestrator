"""Get detailed information about a specific agent."""

import click
from rich.console import Console

console = Console()


def get_agent_info(ctx: click.Context, target: str, json: bool) -> None:
    """Get detailed information about a specific agent."""
    from tmux_orchestrator.utils.tmux import TMUXManager

    tmux: TMUXManager = ctx.obj["tmux"]

    try:
        # Get agent information
        session_name = target.split(":")[0]
        window_id = target.split(":")[1] if ":" in target else "0"

        info = {
            "target": target,
            "session": session_name,
            "window": window_id,
            "exists": tmux.has_session(session_name),
            "timestamp": __import__("time").time(),
        }

        if json:
            import json as json_module

            console.print(json_module.dumps(info, indent=2))
        else:
            console.print(f"[cyan]Agent Info: {target}[/cyan]")
            console.print(f"  Session: {session_name}")
            console.print(f"  Window: {window_id}")
            console.print(f"  Status: {'✓ Active' if info['exists'] else '✗ Not Found'}")

    except Exception as e:
        if json:
            import json as json_module

            result = {"success": False, "error": str(e), "target": target}
            console.print(json_module.dumps(result, indent=2))
        else:
            console.print(f"[red]✗ Error getting info for {target}: {e}[/red]")
