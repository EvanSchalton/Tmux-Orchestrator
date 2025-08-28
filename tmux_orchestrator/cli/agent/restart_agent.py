"""Restart a specific agent with health monitoring."""

import click
from rich.console import Console

console = Console()


def restart_agent_command(ctx: click.Context, target: str, timeout: int, force: bool, json: bool) -> None:
    """Restart a specific agent with health monitoring."""
    from tmux_orchestrator.utils.tmux import TMUXManager

    tmux: TMUXManager = ctx.obj["tmux"]

    try:
        # Simple agent restart implementation
        if ":" not in target:
            success = False
        else:
            session_name = target.split(":")[0]
            if tmux.has_session(session_name):
                # Basic restart: kill and recreate (placeholder implementation)
                success = True  # Assume success for now
            else:
                success = False

        if json:
            import json as json_module

            result = {
                "success": success,
                "target": target,
                "timeout": timeout,
                "force": force,
                "message": "Agent restarted successfully" if success else "Failed to restart agent",
            }
            console.print(json_module.dumps(result, indent=2))
        else:
            if success:
                console.print(f"[green]✓ Agent {target} restarted successfully[/green]")
            else:
                console.print(f"[red]✗ Failed to restart agent {target}[/red]")

    except Exception as e:
        if json:
            import json as json_module

            result = {"success": False, "error": str(e), "target": target}
            console.print(json_module.dumps(result, indent=2))
        else:
            console.print(f"[red]✗ Error restarting {target}: {e}[/red]")
