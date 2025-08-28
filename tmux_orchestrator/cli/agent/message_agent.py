"""Send a quick message to a specific agent."""

import click
from rich.console import Console

console = Console()


def message_agent(ctx: click.Context, target: str, message: str, json: bool) -> None:
    """Send a quick message to a specific agent."""
    from tmux_orchestrator.utils.tmux import TMUXManager

    tmux: TMUXManager = ctx.obj["tmux"]

    try:
        # Simple message sending (for backwards compatibility)
        tmux.press_ctrl_u(target)
        tmux.send_text(target, message)
        tmux.press_enter(target)

        success = True
        status_msg = "sent"
    except Exception as e:
        success = False
        status_msg = f"failed: {str(e)}"

    if json:
        import json as json_module

        result = {"success": success, "target": target, "message": message, "status": status_msg}
        console.print(json_module.dumps(result, indent=2))
    else:
        if success:
            console.print(f"[green]✓ Message sent to {target}[/green]")
        else:
            console.print(f"[red]✗ Failed to send message to {target}: {status_msg}[/red]")
