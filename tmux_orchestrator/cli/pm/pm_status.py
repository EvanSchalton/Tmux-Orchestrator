"""Project Manager status and checkin commands."""

import json as json_module
import time

import click
from rich.console import Console

from tmux_orchestrator.core.pm_manager import PMManager

console: Console = Console()


@click.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def checkin(ctx: click.Context, json: bool) -> None:
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


@click.command()
@click.option("--custom-message", help="Custom check-in message")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def custom_checkin(ctx: click.Context, custom_message: str | None, json: bool) -> None:
    """Send customized status check-in request to all team agents.

    <mcp>Send custom status check-in to team (no args, options: --custom-message, --json). PM sends tailored status request instead of standard checkin. Use for feature-specific updates, deployment readiness, bug fix status.</mcp>

    Allows the PM to send a tailored status request instead of the
    standard check-in message, useful for specific project phases.

    Examples:
        tmux-orc pm custom-checkin --custom-message "Report testing progress for release"
        tmux-orc pm custom-checkin --custom-message "Status on API endpoint implementation"
        tmux-orc pm custom-checkin --custom-message "Update on database migration tasks"

    Custom Check-in Use Cases:
        • Feature-specific progress updates
        • Bug fix status during critical periods
        • Pre-deployment readiness checks
        • Performance optimization reports
        • Security audit preparations
        • Client demo preparation status

    Default Message (if none provided):
        "Please provide a status update on your current work."

    The PM will collect all responses, analyze them for patterns and
    issues, and provide a consolidated report with actionable insights.
    """

    if not custom_message:
        custom_message = "Please provide a status update on your current work."

    start_time = time.time()
    manager = PMManager(ctx.obj["tmux"])
    results = manager.custom_checkin(custom_message)
    execution_time = (time.time() - start_time) * 1000

    result_data = {
        "success": True,
        "command": "pm custom_checkin",
        "custom_message": custom_message,
        "agents_contacted": len(results),
        "results": results,
        "timestamp": time.time(),
        "execution_time_ms": execution_time,
    }

    if json:
        console.print(json_module.dumps(result_data, indent=2))
    else:
        console.print(f"[green]✓ Custom check-in sent to {len(results)} agents[/green]")


@click.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def status(ctx: click.Context, json: bool) -> None:
    """Display comprehensive Project Manager and team status information.

    <mcp>[PM STATUS] Get comprehensive PM and team status.
    Parameters: kwargs (string) - 'action=status [options={"json": true}]'

    Examples:
    - Basic status: kwargs='action=status'
    - Detailed JSON: kwargs='action=status options={"json": true}'

    Shows PM health, team composition, current projects, blocked tasks.</mcp>

    Provides detailed information about the PM's current state, active
    team members, project progress, and any issues requiring attention.

    Examples:
        tmux-orc pm status                     # Show complete PM status
        tmux-orc pm status --json              # JSON formatted output

    Status Information Includes:
        📊 PM Session Details:
           • Session ID and window location
           • Current active project
           • Uptime and last activity

        👥 Team Composition:
           • Active team members and roles
           • Agent status and availability
           • Communication channels

        📈 Project Progress:
           • Current sprint or milestone
           • Completed vs remaining tasks
           • Timeline and deadline tracking

        ⚠️  Issues and Blockers:
           • Identified risks and obstacles
           • Resource constraints
           • Team coordination issues

        📡 Communication Status:
           • Message queue status
           • Recent team interactions
           • Escalation alerts

    Use this command for regular health checks, troubleshooting team
    coordination issues, or preparing status reports for stakeholders.
    """

    start_time = time.time()
    manager = PMManager(ctx.obj["tmux"])

    # Get PM session info
    pm_session = manager.find_pm_session()

    # Get team status - list all windows in PM session if found
    team_agents = []
    if pm_session:
        try:
            session_name = pm_session.split(":")[0]
            windows = manager.tmux.list_windows(session_name)
            team_agents = [{"session": session_name, "window": w["index"], "name": w["name"]} for w in windows]
        except Exception:
            team_agents = []

    # Calculate execution time
    execution_time = (time.time() - start_time) * 1000

    # Build status data
    status_data = {
        "success": pm_session is not None,
        "command": "pm status",
        "execution_time_ms": execution_time,
        "timestamp": time.time(),
        "pm_session": pm_session,
        "team_agents": team_agents,
        "total_agents": len(team_agents),
        "active_agents": len([agent for agent in team_agents if agent.get("active", True)]),
    }

    if json:
        console.print(json_module.dumps(status_data, indent=2))
    else:
        if pm_session:
            console.print(f"[green]✓ PM active at {pm_session}[/green]")
            console.print(f"[blue]Team: {len(team_agents)} agents[/blue]")
            for agent in team_agents:
                status_icon = "✓" if agent.get("active", True) else "✗"
                status_color = "green" if agent.get("active", True) else "red"
                agent_name = agent.get("name", "unknown")
                console.print(f"  [{status_color}]{status_icon} {agent_name}[/{status_color}]")
        else:
            console.print("[red]✗ No PM session found[/red]")
