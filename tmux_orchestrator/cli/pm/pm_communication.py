"""Project Manager communication commands."""

import json as json_module
import time

import click
from rich.console import Console

from tmux_orchestrator.core.pm_manager import PMManager

console: Console = Console()


@click.command()
@click.argument("message")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def message(ctx: click.Context, message: str, json: bool) -> None:
    """Send a direct message to the Project Manager.

    <mcp>[PM MESSAGE] Send direct message to Project Manager agent.
    Parameters: kwargs (string) - 'action=message args=["message text"] [options={"json": true}]'

    Examples:
    - Priority update: kwargs='action=message args=["Focus on API testing"]'
    - Deadline change: kwargs='action=message args=["Sprint ends Friday"]'
    - With JSON: kwargs='action=message args=["Status report needed"] options={"json": true}'

    Messages TO the PM. For PM to broadcast TO team, use 'pm broadcast' instead.</mcp>

    Delivers a message directly to the PM agent, useful for providing
    instructions, updates, or requesting specific PM actions.

    MESSAGE: Message text to send to the Project Manager

    Examples:
        tmux-orc pm message "Prioritize the API testing tasks"
        tmux-orc pm message "Client meeting moved to tomorrow 2pm"
        tmux-orc pm message "Generate weekly progress report"
        tmux-orc pm message "Review code quality metrics"

    Common PM Message Types:
        • Priority changes and urgent updates
        • Meeting schedules and deadlines
        • Resource allocation decisions
        • Quality standards clarifications
        • Stakeholder communication requests
        • Risk assessment instructions

    The PM will acknowledge the message and take appropriate action
    based on the content and current project context.
    """

    start_time = time.time()
    manager = PMManager(ctx.obj["tmux"])
    target = manager.find_pm_session()

    if not target:
        result_data = {
            "success": False,
            "command": "pm message",
            "message": message,
            "error": "No PM session found",
            "timestamp": time.time(),
            "execution_time_ms": (time.time() - start_time) * 1000,
        }

        if json:
            console.print(json_module.dumps(result_data, indent=2))
        else:
            console.print("[red]✗ No PM session found[/red]")
        return

    success = ctx.obj["tmux"].send_message(target, message)
    execution_time = (time.time() - start_time) * 1000

    result_data = {
        "success": success,
        "command": "pm message",
        "message": message,
        "target": target,
        "timestamp": time.time(),
        "execution_time_ms": execution_time,
    }

    if json:
        console.print(json_module.dumps(result_data, indent=2))
    else:
        if success:
            console.print(f"[green]✓ Message sent to PM at {target}[/green]")
        else:
            console.print("[red]✗ Failed to send message to PM[/red]")


@click.command()
@click.argument("message")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def broadcast(ctx: click.Context, message: str, json: bool) -> None:
    """Have the Project Manager broadcast a message to all team agents.

    <mcp>[PM BROADCAST] Project Manager broadcasts message to entire team.
    Parameters: kwargs (string) - 'action=broadcast args=["message text"] [options={"json": true}]'

    Examples:
    - Team update: kwargs='action=broadcast args=["Code freeze at 5pm"]'
    - Priority alert: kwargs='action=broadcast args=["Critical bug in production"]'
    - With tracking: kwargs='action=broadcast args=["Sprint review in 30min"] options={"json": true}'

    PM adds context and coordinates responses. For direct team broadcast, use 'team broadcast' instead.</mcp>

    Uses the PM as a communication hub to send coordinated messages to
    the entire development team, maintaining proper chain of command.

    MESSAGE: Message text for PM to broadcast to all team agents

    Examples:
        tmux-orc pm broadcast "Code freeze begins now for release candidate"
        tmux-orc pm broadcast "Daily standup moved to 10am tomorrow"
        tmux-orc pm broadcast "Focus on critical bugs for next 2 hours"
        tmux-orc pm broadcast "Demo preparation starts after lunch"

    PM Broadcast Features:
        • Consistent message formatting and context
        • Role-appropriate message delivery
        • Delivery confirmation and failure handling
        • Follow-up coordination as needed
        • Integration with project timeline

    Difference from Direct Team Broadcast:
        • PM broadcast: Goes through PM with context and follow-up
        • Team broadcast: Direct message to all agents

    The PM adds project context, ensures message clarity, and
    coordinates any follow-up actions required from the team.
    """

    start_time = time.time()
    manager = PMManager(ctx.obj["tmux"])
    results = manager.broadcast_to_all_agents(message)
    execution_time = (time.time() - start_time) * 1000

    successful_agents = [agent for agent, success in results.items() if success]
    failed_agents = [agent for agent, success in results.items() if not success]

    result_data = {
        "success": len(failed_agents) == 0,
        "command": "pm broadcast",
        "message": message,
        "total_agents": len(results),
        "successful_agents": len(successful_agents),
        "failed_agents": len(failed_agents),
        "results": results,
        "timestamp": time.time(),
        "execution_time_ms": execution_time,
    }

    if json:
        console.print(json_module.dumps(result_data, indent=2))
    else:
        console.print(f"[green]✓ Broadcast sent to {len(results)} agents[/green]")
        for agent, success in results.items():
            status = "✓" if success else "✗"
            color = "green" if success else "red"
            console.print(f"  [{color}]{status} {agent}[/{color}]")
