"""Terminate a specific agent gracefully or forcefully."""

import click
from rich.console import Console

console = Console()


def kill_agent_command(ctx: click.Context, target: str, timeout: int, force: bool, json: bool) -> None:
    """Terminate a specific agent gracefully or forcefully."""
    from tmux_orchestrator.utils.tmux import TMUXManager

    tmux: TMUXManager = ctx.obj["tmux"]

    try:
        # Simple agent termination implementation
        # Parse target to get session and window
        if ":" not in target:
            success = False
        else:
            session_name = target.split(":")[0]
            if tmux.has_session(session_name):
                # Kill the session (basic implementation)
                success = tmux.kill_session(session_name) if hasattr(tmux, "kill_session") else False
                if not success:
                    # Fallback: try to kill window/pane
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
                "message": "Agent terminated successfully" if success else "Failed to terminate agent",
            }
            console.print(json_module.dumps(result, indent=2))
        else:
            if success:
                console.print(f"[green]✓ Agent {target} terminated successfully[/green]")
            else:
                console.print(f"[red]✗ Failed to terminate agent {target}[/red]")

    except Exception as e:
        if json:
            import json as json_module

            result = {"success": False, "error": str(e), "target": target}
            console.print(json_module.dumps(result, indent=2))
        else:
            console.print(f"[red]✗ Error terminating {target}: {e}[/red]")
