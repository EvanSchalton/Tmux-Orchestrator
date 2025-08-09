"""Project Manager specific commands."""

import click
from rich.console import Console

from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


@click.group()
def pm() -> None:
    """Project Manager operations and team coordination.

    The PM command group provides tools for creating and managing Project Managers,
    specialized Claude agents responsible for team coordination, quality assurance,
    and project oversight.

    Examples:
        tmux-orc pm create my-project           # Create PM for project
        tmux-orc pm status                      # Check PM and team status
        tmux-orc pm checkin                     # Trigger team status review
        tmux-orc pm message "Sprint review at 3pm"
        tmux-orc pm broadcast "Deploy to staging now"

    Project Manager Responsibilities:
        • Team coordination and communication
        • Quality standards enforcement
        • Progress monitoring and reporting
        • Risk identification and mitigation
        • Resource allocation and optimization

    PM agents work alongside development teams to ensure projects
    stay on track and meet quality standards.
    """
    pass


@pm.command()
@click.pass_context
def checkin(ctx: click.Context) -> None:
    """Trigger comprehensive team status review by Project Manager.

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
    from tmux_orchestrator.core.pm_manager import PMManager

    manager = PMManager(ctx.obj["tmux"])
    manager.trigger_status_review()

    console.print("[green]✓ PM status review triggered[/green]")


@pm.command()
@click.argument("message")
@click.pass_context
def message(ctx: click.Context, message: str) -> None:
    """Send a direct message to the Project Manager.

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
    from tmux_orchestrator.core.pm_manager import PMManager

    manager = PMManager(ctx.obj["tmux"])
    target = manager.find_pm_session()

    if not target:
        console.print("[red]✗ No PM session found[/red]")
        return

    if ctx.obj["tmux"].send_message(target, message):
        console.print(f"[green]✓ Message sent to PM at {target}[/green]")
    else:
        console.print("[red]✗ Failed to send message to PM[/red]")


@pm.command()
@click.argument("message")
@click.pass_context
def broadcast(ctx: click.Context, message: str) -> None:
    """Have the Project Manager broadcast a message to all team agents.

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
    from tmux_orchestrator.core.pm_manager import PMManager

    manager = PMManager(ctx.obj["tmux"])
    results = manager.broadcast_to_all_agents(message)

    console.print(f"[green]✓ Broadcast sent to {len(results)} agents[/green]")
    for agent, success in results.items():
        status = "✓" if success else "✗"
        color = "green" if success else "red"
        console.print(f"  [{color}]{status} {agent}[/{color}]")


@pm.command()
@click.option("--custom-message", help="Custom check-in message")
@click.pass_context
def custom_checkin(ctx: click.Context, custom_message: str | None) -> None:
    """Send customized status check-in request to all team agents.

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
    from tmux_orchestrator.core.pm_manager import PMManager

    if not custom_message:
        custom_message = "Please provide a status update on your current work."

    manager = PMManager(ctx.obj["tmux"])
    results = manager.custom_checkin(custom_message)

    console.print(f"[green]✓ Custom check-in sent to {len(results)} agents[/green]")


@pm.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def status(ctx: click.Context, json: bool) -> None:
    """Display comprehensive Project Manager and team status overview.

    Shows detailed information about the PM agent status, team composition,
    agent health, and overall project coordination metrics.

    Examples:
        tmux-orc pm status                     # Show PM and team status
        tmux-orc pm status --json             # JSON output for monitoring

    PM Status Information:
        • PM agent location and responsiveness
        • Current PM session and window details
        • PM health and activity metrics
        • Communication channel status

    Team Overview Includes:
        • Total number of team agents
        • Agent types and specializations
        • Individual agent status and activity
        • Team coordination health
        • Recent communication patterns
        • Project progress indicators

    Status Indicators:
        🟢 Active:    PM and team functioning normally
        🟡 Warning:   Some coordination issues detected
        🔴 Critical:  PM unresponsive or major team problems
        ⚫ Unknown:   Unable to determine status

    If no PM is found, provides guidance on creating one.
    JSON mode outputs machine-readable data for integration
    with monitoring and automation systems.
    """
    from rich.table import Table

    from tmux_orchestrator.core.pm_manager import PMManager

    manager = PMManager(ctx.obj["tmux"])
    pm_target = manager.find_pm_session()

    if not pm_target:
        console.print("[red]✗ No PM session found[/red]")
        console.print("\nTo create a PM, use: [bold]tmux-orc pm create <session>[/bold]")
        return

    # Get PM status
    pm_status = {
        "target": pm_target,
        "active": True,
        "session": pm_target.split(":")[0],
        "window": pm_target.split(":")[1] if ":" in pm_target else "0",
    }

    # Get team overview using tmux directly
    team_agents = ctx.obj["tmux"].list_agents()

    if json:
        import json as json_module

        status_data = {
            "pm_status": pm_status,
            "team_agents": team_agents,
            "summary": {
                "total_agents": len(team_agents),
                "active_agents": len([a for a in team_agents if a.get("status") == "active"]),
            },
        }
        console.print(json_module.dumps(status_data, indent=2))
        return

    # Display rich status
    console.print("[bold blue]Project Manager Status[/bold blue]")
    console.print(f"  Target: {pm_target}")
    console.print(f"  Session: {pm_status['session']}")
    console.print(f"  Window: {pm_status['window']}")
    console.print("  Status: [green]Active[/green]")

    if team_agents:
        console.print(f"\n[bold]Team Overview ({len(team_agents)} agents):[/bold]")

        table = Table()
        table.add_column("Agent", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Last Activity", style="blue")

        for agent in team_agents:
            table.add_row(
                f"{agent.get('session', 'unknown')}:{agent.get('window', '0')}",
                agent.get("type", "unknown"),
                agent.get("status", "unknown"),
                agent.get("last_activity", "Unknown"),
            )

        console.print(table)
    else:
        console.print("\n[yellow]No team agents found in this session[/yellow]")


@pm.command()
@click.argument("session")
@click.option("--project-dir", help="Project directory (defaults to current)")
@click.pass_context
def create(ctx: click.Context, session: str, project_dir: str | None) -> None:
    """Create a new Project Manager for team coordination and oversight.

    Deploys a specialized Claude agent configured as a Project Manager
    with team coordination, quality assurance, and project management
    capabilities.

    SESSION: Session name where PM will be created (e.g., 'my-project')

    Examples:
        tmux-orc pm create my-project          # Create PM for 'my-project' session
        tmux-orc pm create frontend-team       # Create PM for frontend team
        tmux-orc pm create testing-suite --project-dir /path/to/project

    PM Creation Process:
        1. 🏧 Creates session if it doesn't exist
        2. 🗺️ Sets up PM window in specified project directory
        3. 🤖 Starts Claude agent with PM specialization
        4. 📜 Provides comprehensive PM briefing and responsibilities
        5. 🔗 Establishes team communication protocols
        6. 🔍 Analyzes project structure and creates initial plan

    PM Capabilities:
        • Team coordination and communication
        • Quality standards enforcement
        • Progress tracking and milestone management
        • Risk identification and mitigation
        • Resource allocation optimization
        • Stakeholder communication
        • Code review coordination
        • Testing and deployment oversight

    PM Briefing Includes:
        • Team leadership and coordination principles
        • Quality assurance methodologies
        • Project management best practices
        • Communication protocols and escalation paths
        • Tool usage for project tracking
        • Reporting and status update procedures

    The PM will immediately begin analyzing the project structure,
    identifying team members, and establishing coordination workflows.

    Note: Only one PM should be created per project session to
    maintain clear chain of command and avoid coordination conflicts.
    """
    from pathlib import Path

    if not project_dir:
        project_dir = str(Path.cwd())

    tmux: TMUXManager = ctx.obj["tmux"]

    # Check if session exists, create if not
    if not tmux.has_session(session):
        console.print(f"[blue]Creating new session: {session}[/blue]")
        if not tmux.create_session(session, "Project-Manager", project_dir):
            console.print(f"[red]✗ Failed to create session {session}[/red]")
            return

    # Create PM window
    pm_window = "Project-Manager"
    if not tmux.create_window(session, pm_window, project_dir):
        console.print(f"[red]✗ Failed to create PM window in {session}[/red]")
        return

    # Start Claude PM
    target = f"{session}:{pm_window}"
    console.print(f"[blue]Starting Project Manager at {target}...[/blue]")

    # Start Claude
    if not tmux.send_keys(target, "claude --dangerously-skip-permissions"):
        console.print(f"[red]✗ Failed to start Claude in {target}[/red]")
        return

    import time

    time.sleep(0.5)
    tmux.send_keys(target, "Enter")
    time.sleep(3)  # Wait for Claude to start

    # Send PM briefing
    pm_briefing = """You are the Project Manager for this development team. Your responsibilities:

1. Coordinate team activities and maintain project timeline
2. Ensure quality standards are met across all deliverables
3. Monitor progress and identify blockers quickly
4. Facilitate communication between team members
5. Report status updates to the orchestrator

Begin by analyzing the project structure and creating an initial project plan."""

    if tmux.send_message(target, pm_briefing):
        console.print(f"[green]✓ Project Manager created successfully at {target}[/green]")
        console.print(f"  Session: {session}")
        console.print(f"  Window: {pm_window}")
        console.print(f"  Directory: {project_dir}")
    else:
        console.print("[yellow]⚠ PM created but briefing may have failed[/yellow]")
