"""Team management commands."""

import builtins
from typing import Any, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tmux_orchestrator.core.team_operations import (
    broadcast_to_team,
    get_team_status,
    list_all_teams,
)
from tmux_orchestrator.core.team_operations.deploy_team import (
    deploy_standard_team,
    recover_team_agents,
)
from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


@click.group()
def team() -> None:
    """Manage multi-agent teams across tmux sessions.

    The team command group provides comprehensive management of agent teams,
    including deployment, monitoring, communication, and recovery operations.
    Teams consist of multiple specialized Claude agents working together.

    Examples:
        tmux-orc team deploy frontend 4         # Deploy 4-agent frontend team
        tmux-orc team status my-project         # Check team health
        tmux-orc team list                      # Show all active teams
        tmux-orc team broadcast frontend "Update status"
        tmux-orc team recover stuck-project    # Recover failed agents

    Team Types:
        • frontend:  UI/UX development team
        • backend:   Server-side development team
        • fullstack: Full-stack development team
        • testing:   QA and testing team

    Each team includes specialized roles like developers, project managers,
    QA engineers, and code reviewers working in coordination.
    """
    pass


@team.command()
@click.argument("session")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def status(ctx: click.Context, session: str, json: bool) -> None:
    """Show comprehensive team status and health metrics.

    Displays detailed information about all agents in a team session,
    including individual agent status, activity levels, and team coordination.

    SESSION: Session name to check (e.g., 'my-project', 'frontend-team')

    Examples:
        tmux-orc team status my-project        # Check project team status
        tmux-orc team status frontend-team     # Check frontend team health
        tmux-orc team status testing-suite     # Check testing team progress

    Status Information:
        • Session metadata (creation time, attachment status)
        • Individual agent status and last activity
        • Agent types and specializations
        • Communication and coordination health
        • Resource usage and performance metrics
        • Team productivity summary

    Use this regularly to monitor team health and identify agents
    that may need attention, restart, or additional resources.
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Delegate to business logic
    team_status: Optional[dict[str, Any]] = get_team_status(tmux, session)

    if not team_status:
        console.print(f"[red]✗ Session '{session}' not found[/red]")
        return

    # JSON output mode
    if json:
        import json as json_module

        console.print(json_module.dumps(team_status, indent=2))
        return

    # Display session header
    session_info: dict[str, str] = team_status["session_info"]
    attached: str = "Yes" if session_info.get("attached") == "1" else "No"
    header_text: str = f"Session: {session} | Created: {session_info.get('created', 'Unknown')} | Attached: {attached}"
    console.print(Panel(header_text, style="bold blue"))

    # Create team status table
    table: Table = Table(title=f"Team Status - {session}")
    table.add_column("Window", style="cyan", width=8)
    table.add_column("Name", style="magenta", width=20)
    table.add_column("Type", style="green", width=15)
    table.add_column("Status", style="yellow", width=12)
    table.add_column("Last Activity", style="blue", width=30)

    windows: builtins.list[dict[str, Any]] = team_status["windows"]
    for window in windows:
        table.add_row(
            window["index"],
            window["name"],
            window["type"],
            window["status"],
            window["last_activity"],
        )

    # Display table
    console.print(table)

    # Show summary
    summary: dict[str, int] = team_status["summary"]
    summary_text: str = f"Total Windows: {summary['total_windows']} | Active Agents: {summary['active_agents']}"
    console.print(f"\n[bold green]{summary_text}[/bold green]")


@team.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def list(ctx: click.Context, json: bool) -> None:
    """List all active team sessions with summary information.

    Provides an overview of all team sessions currently running,
    including team size, agent count, and overall status.

    Examples:
        tmux-orc team list                     # Show all active teams

    Information Displayed:
        • Session name and creation time
        • Number of windows (workspaces) per team
        • Active agent count and types
        • Overall team status (Healthy, Warning, Critical)
        • Resource utilization summary

    Team Status Indicators:
        🟢 Healthy:  All agents responsive and productive
        🟡 Warning:  Some agents need attention
        🔴 Critical: Multiple failed agents or system issues
        ⚫ Unknown:  Unable to determine team status

    Use this for system-wide monitoring and to identify teams
    that may need management intervention.
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Delegate to business logic
    teams: builtins.list[dict[str, Any]] = list_all_teams(tmux)

    if json:
        import json as json_module

        console.print(json_module.dumps(teams, indent=2))
        return

    if not teams:
        console.print("[yellow]No active sessions found[/yellow]")
        return

    table: Table = Table(title="All Team Sessions")
    table.add_column("Session", style="cyan")
    table.add_column("Windows", style="magenta")
    table.add_column("Agents", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Created", style="blue")

    for team in teams:
        table.add_row(
            team["name"],
            str(team["windows"]),
            str(team["agents"]),
            team["status"],
            team["created"],
        )

    console.print(table)


@team.command()
@click.argument("session")
@click.argument("message")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def broadcast(ctx: click.Context, session: str, message: str, json: bool) -> None:
    """Broadcast a coordinated message to all agents in a team.

    Sends the same message simultaneously to all Claude agents in the
    specified team session, enabling coordinated team communication.

    SESSION: Target team session name (e.g., 'my-project', 'frontend-team')
    MESSAGE: Message text to broadcast to all team agents

    Examples:
        tmux-orc team broadcast frontend "Sprint planning meeting in 30 minutes"
        tmux-orc team broadcast my-project "Deploy to staging environment now"
        tmux-orc team broadcast testing "Focus on API endpoint testing today"
        tmux-orc team broadcast backend "Database migration scheduled for 3pm"

    Common Use Cases:
        • Sprint announcements and coordination
        • Priority shifts and urgent updates
        • Deployment instructions and timing
        • Status update requests from all agents
        • Emergency notifications and alerts

    Message Delivery:
        • Delivered instantly to all responsive agents
        • Failed deliveries are reported individually
        • Agents receive messages as direct user input
        • No message queuing for offline agents

    Best Practices:
        • Use clear, actionable messages
        • Include context and urgency level
        • Follow up with individual agents if needed
        • Coordinate timing for synchronized actions
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Delegate to business logic
    success, summary_message, results = broadcast_to_team(tmux, session, message)

    if json:
        import json as json_module

        broadcast_result = {
            "success": success,
            "session": session,
            "message": message,
            "summary": summary_message,
            "results": results,
        }
        console.print(json_module.dumps(broadcast_result, indent=2))
        return

    if not success:
        console.print(f"[red]✗ {summary_message}[/red]")
        return

    # Display detailed results
    for result in results:
        if result["success"]:
            console.print(f"[green]✓ Message sent to {result['window_name']} ({result['target']})[/green]")
        else:
            console.print(f"[red]✗ Failed to send message to {result['window_name']} ({result['target']})[/red]")

    console.print(f"\n[bold]{summary_message}[/bold]")


@team.command()
@click.argument("team_type", type=click.Choice(["frontend", "backend", "fullstack", "testing"]))
@click.argument("size", type=int, default=3)
@click.option("--project-name", help="Project name (defaults to current directory)")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def deploy(
    ctx: click.Context,
    team_type: str,
    size: int,
    project_name: Optional[str],
    json: bool,
) -> None:
    """Deploy a complete multi-agent team with specialized roles.

    Creates a new tmux session with multiple coordinated Claude agents,
    each with specialized roles and responsibilities based on team type.

    TEAM_TYPE: Specialization focus (frontend, backend, fullstack, testing)
    SIZE: Number of agents to deploy (recommended: 2-8, max: 20)

    Examples:
        tmux-orc team deploy frontend 4              # 4-agent frontend team
        tmux-orc team deploy backend 3               # 3-agent backend team
        tmux-orc team deploy fullstack 6             # 6-agent fullstack team
        tmux-orc team deploy testing 2               # 2-agent testing team
        tmux-orc team deploy frontend 5 --project-name my-app

    Team Compositions by Type:

    Frontend Team:
        • UI/UX Developer: Component design and user experience
        • Frontend Developer: React/Vue/Angular implementation
        • CSS/Styling Expert: Responsive design and animations
        • Performance Optimizer: Bundle optimization and speed
        • Project Manager: Coordination and quality assurance

    Backend Team:
        • API Developer: REST/GraphQL endpoint development
        • Database Engineer: Schema design and optimization
        • DevOps Engineer: Deployment and infrastructure
        • Security Specialist: Authentication and authorization
        • Project Manager: Architecture and coordination

    Fullstack Team:
        • Lead Developer: Architecture and technical decisions
        • Frontend Specialist: Client-side development
        • Backend Specialist: Server-side development
        • Database Expert: Data layer and optimization
        • QA Engineer: Testing and quality assurance
        • DevOps Engineer: Deployment and monitoring

    Testing Team:
        • QA Lead: Test strategy and planning
        • Automation Engineer: Test framework and CI/CD
        • Manual Tester: User acceptance and edge cases
        • Performance Tester: Load and stress testing

    The deployment process:
        1. Creates project-specific tmux session
        2. Assigns specialized roles to each agent
        3. Provides role-specific briefings and tools
        4. Establishes team communication protocols
        5. Initializes project context and objectives

    Recommended Team Sizes:
        • Small project: 2-3 agents
        • Medium project: 4-6 agents
        • Large project: 6-8 agents
        • Enterprise: 8+ agents (requires careful coordination)
    """
    from pathlib import Path

    tmux: TMUXManager = ctx.obj["tmux"]

    if not project_name:
        project_name = Path.cwd().name

    console.print(f"[blue]Deploying {team_type} team with {size} agents...[/blue]")

    # Delegate to business logic
    success, message = deploy_standard_team(tmux, team_type, size, project_name)

    if json:
        import json as json_module

        deploy_result = {
            "success": success,
            "team_type": team_type,
            "size": size,
            "project_name": project_name,
            "message": message,
        }
        console.print(json_module.dumps(deploy_result, indent=2))
        return

    if success:
        console.print(f"[green]✓ {message}[/green]")
    else:
        console.print(f"[red]✗ {message}[/red]")


@team.command()
@click.argument("session")
@click.pass_context
def recover(ctx: click.Context, session: str) -> None:
    """Recover and restore failed or unresponsive team agents.

    Automatically detects and restarts failed agents in the specified
    team session, restoring them to their original roles and context.

    SESSION: Team session name to recover (e.g., 'my-project', 'frontend-team')

    Examples:
        tmux-orc team recover my-project           # Recover failed project agents
        tmux-orc team recover frontend-team       # Fix unresponsive frontend team
        tmux-orc team recover testing-suite       # Restore crashed testing agents

    Recovery Process:
        1. 🔍 Scans all windows in the team session
        2. 🏥 Identifies failed, crashed, or unresponsive agents
        3. 💾 Captures current context and work state
        4. 🔄 Restarts failed agents with fresh Claude instances
        5. 📋 Restores agent roles, briefings, and context
        6. 🔗 Re-establishes team communication protocols
        7. ✅ Verifies all agents are responsive

    When to Use Recovery:
        • Multiple agents in team are unresponsive
        • System crash or restart affected agents
        • Agents showing error states or stuck processes
        • Team coordination has broken down
        • After system updates or configuration changes

    Recovery Features:
        • Preserves agent specializations and roles
        • Maintains project context and objectives
        • Restores inter-agent communication
        • Minimal disruption to working agents
        • Detailed recovery status reporting

    Prevention Tips:
        • Monitor team status regularly with 'tmux-orc team status'
        • Use proper tmux detach commands
        • Avoid forcefully killing tmux sessions
        • Keep system resources adequate for team size
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    console.print(f"[blue]Recovering failed agents in session '{session}'...[/blue]")

    # Delegate to business logic
    success, message = recover_team_agents(tmux, session)

    if success:
        console.print(f"[green]✓ {message}[/green]")
    else:
        console.print(f"[red]✗ {message}[/red]")
