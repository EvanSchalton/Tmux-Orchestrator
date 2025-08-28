"""Show comprehensive monitoring daemon status."""

import click
from rich.console import Console

console = Console()


def daemon_status(ctx: click.Context, json: bool) -> None:
    """Show comprehensive monitoring daemon status."""
    from tmux_orchestrator.core.monitor import IdleMonitor
    from tmux_orchestrator.utils.tmux import TMUXManager

    tmux = TMUXManager()
    monitor = IdleMonitor(tmux)

    if json:
        import json as json_module

        # Get basic status info since get_status_json doesn't exist
        status_data = {
            "daemon_running": monitor.is_running(),
            "status": "running" if monitor.is_running() else "stopped",
        }
        console.print(json_module.dumps(status_data, indent=2))
    else:
        monitor.status()
