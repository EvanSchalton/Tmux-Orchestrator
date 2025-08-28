"""Trigger comprehensive team status review by Project Manager."""

import time

import click
from rich.console import Console

from tmux_orchestrator.core.pm_manager import PMManager

console = Console()


def checkin_command(ctx: click.Context, json: bool) -> None:
    """Trigger comprehensive team status review by Project Manager.

    <mcp>[PM CHECKIN] Trigger Project Manager team status review.
    Parameters: kwargs (string) - 'action=checkin [options={"json": true}]'

    Examples:
    - Standard checkin: kwargs='action=checkin'
    - JSON response: kwargs='action=checkin options={"json": true}'

    PM polls all team members for status. For custom message checkin, use 'pm custom-checkin' instead.</mcp>

    Initiates a systematic status check where the PM requests updates
    from all team agents and compiles a comprehensive progress report.

    Examples:
        tmux-orc pm checkin                    # Trigger standard status review

    Review Process:
        1. 🔍 PM identifies all team agents
        2. 📹 Sends status request to each agent
        3. 📄 Collects and analyzes responses
        4. 📊 Generates progress summary
        5. ⚠️ Identifies blockers and risks
        6. 📨 Reports findings to orchestrator

    When to Use:
        • Daily standup coordination
        • Sprint milestone reviews
        • Pre-deployment assessments
        • Troubleshooting team issues
        • Orchestrator status requests

    The PM will provide structured feedback including task completion
    status, identified blockers, resource needs, and timeline updates.
    """
    start_time = time.time()
    manager = PMManager(ctx.obj["tmux"])
    manager.trigger_status_review()
    success = True  # Assume success if no exception
    execution_time = (time.time() - start_time) * 1000

    if json:
        import json as json_module

        result = {
            "success": success,
            "command": "pm checkin",
            "execution_time_ms": execution_time,
            "timestamp": time.time(),
            "message": "PM status review triggered" if success else "Failed to trigger PM status review",
        }
        console.print(json_module.dumps(result, indent=2))
    else:
        if success:
            console.print("[green]✓ PM status review triggered[/green]")
        else:
            console.print("[red]✗ Failed to trigger PM status review[/red]")
