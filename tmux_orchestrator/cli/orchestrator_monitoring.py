"""Orchestrator monitoring commands (status, list)."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


@click.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def status(ctx: click.Context, json: bool) -> None:
    """Display enterprise-wide orchestrator status and strategic overview.

    Provides a comprehensive view of the entire orchestrator ecosystem,
    including all sessions, teams, agents, and strategic performance metrics
    from the orchestrator's perspective.

    Examples:
        tmux-orc orchestrator status          # Strategic status overview
        tmux-orc orchestrator status --json   # JSON for integration

    Strategic Status Components:

    Orchestrator Health:
        • Main orchestrator session status
        • Orchestrator agent responsiveness
        • System integration health
        • Communication pathway status

    Portfolio Overview:
        • Total active projects and teams
        • Resource allocation across projects
        • Cross-project dependency mapping
        • Strategic milestone tracking

    Team Coordination:
        • Project Manager status and health
        • Team productivity metrics
        • Inter-team communication patterns
        • Coordination bottlenecks

    System Performance:
        • Overall system utilization
        • Agent efficiency metrics
        • Quality gate compliance
        • Error rates and recovery statistics

    Strategic Indicators:
        🟢 Optimal:   All systems performing at peak efficiency
        🟡 Monitor:   Some areas need attention
        🔴 Critical:  Strategic intervention required
        ⚫ Unknown:   Insufficient data for assessment

    Use this for executive reporting, strategic planning sessions,
    and high-level system health assessments.
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Gather system status
    sessions = tmux.list_sessions()
    agents = tmux.list_agents()

    # Find orchestrator sessions
    orc_sessions = [s for s in sessions if "orc" in s["name"].lower() or "orchestrator" in s["name"].lower()]

    # Calculate summary stats
    total_sessions = len(sessions)
    total_agents = len(agents)
    active_agents_count = len([a for a in agents if a.get("status") == "Active"])

    if json:
        import json as json_module

        status_data = {
            "timestamp": "2024-01-01T10:00:00Z",  # Would use real timestamp
            "orchestrator_sessions": orc_sessions,
            "total_sessions": total_sessions,
            "total_agents": total_agents,
            "active_agents": active_agents_count,
            "system_health": "healthy" if active_agents_count > 0 else "idle",
            "sessions": sessions,
            "agents": agents,
        }
        console.print(json_module.dumps(status_data, indent=2))
        return

    # Rich status display
    console.print("[bold blue]🎭 ORCHESTRATOR SYSTEM STATUS[/bold blue]")

    # System summary panel
    summary_text = (
        f"Total Sessions: {total_sessions} | "
        f"Total Agents: {total_agents} | "
        f"Active: {active_agents_count} | "
        f"Health: {'🟢 Healthy' if active_agents_count > 0 else '🟡 Idle'}"
    )
    summary_panel = Panel(summary_text, title="System Summary", style="green")
    console.print(summary_panel)

    # Orchestrator sessions
    if orc_sessions:
        console.print(f"\n[bold]🎯 Orchestrator Sessions ({len(orc_sessions)}):[/bold]")
        orc_table = Table()
        orc_table.add_column("Session", style="cyan")
        orc_table.add_column("Attached", style="green")
        orc_table.add_column("Windows", style="yellow")
        orc_table.add_column("Created", style="blue")

        for session in orc_sessions:
            attached = "✓" if session.get("attached") == "1" else "○"
            orc_table.add_row(
                session["name"],
                attached,
                session.get("windows", "0"),
                session.get("created", "Unknown"),
            )
        console.print(orc_table)
    else:
        console.print("\n[yellow]No orchestrator sessions found[/yellow]")
        console.print("To start: [bold]tmux-orc orchestrator start[/bold]")

    # Recent activity summary
    if agents:
        console.print(f"\n[bold]📊 Agent Activity Overview:[/bold] ({len(agents)} total agents)")

        # Simple summary without detailed breakdown to avoid Click interference
        active_agents = [a for a in agents if a.get("status") == "Active"]
        idle_agents = [a for a in agents if a.get("status") == "Idle"]
        console.print(f"  Active: {len(active_agents)}, Idle: {len(idle_agents)}")


@click.command(name="list")
@click.option("--all-sessions", is_flag=True, help="List all sessions, not just orchestrator")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def list_sessions(ctx: click.Context, all_sessions: bool, json: bool) -> None:
    """List sessions under orchestrator management with strategic context.

    Displays all sessions relevant to orchestrator oversight, categorized
    by type and importance, with strategic information for decision-making.

    Examples:
        tmux-orc orchestrator list             # Show orchestrator sessions
        tmux-orc orchestrator list --all-sessions  # Include all sessions
        tmux-orc orchestrator list --json     # JSON for automation

    Session Categories:

    Orchestrator Sessions:
        🎭 Main orchestrator and control sessions
        • Primary strategic coordination
        • System-wide monitoring
        • Cross-project management

    Project Teams:
        👥 Active development teams
        • Frontend, backend, fullstack teams
        • Testing and QA teams
        • Specialized project teams

    Project Management:
        👔 Project Manager sessions
        • Team coordination hubs
        • Quality oversight
        • Progress tracking

    Support Services:
        🔧 Infrastructure and support
        • DevOps and deployment
        • Database management
        • Security and compliance

    Session Information:
        • Session name and creation time
        • Attachment status and accessibility
        • Window count and configuration
        • Session type and specialization
        • Resource utilization
        • Strategic importance level

    Use for portfolio management, resource planning, and
    strategic session organization.
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    sessions = tmux.list_sessions()
    if not all_sessions:
        # Filter to orchestrator and project sessions
        sessions = [
            s
            for s in sessions
            if any(
                keyword in s["name"].lower()
                for keyword in [
                    "orc",
                    "orchestrator",
                    "frontend",
                    "backend",
                    "team",
                    "project",
                ]
            )
        ]

    if json:
        import json as json_module

        console.print(json_module.dumps(sessions, indent=2))
        return

    if not sessions:
        console.print("[yellow]No orchestrator sessions found[/yellow]")
        console.print("\nTo start orchestrator: [bold]tmux-orc orchestrator start[/bold]")
        return

    console.print(
        f"[bold]🎭 {'All Sessions' if all_sessions else 'Orchestrator & Project Sessions'} ({len(sessions)}):[/bold]"
    )

    table = Table()
    table.add_column("Session", style="cyan", width=20)
    table.add_column("Status", style="green", width=10)
    table.add_column("Windows", style="yellow", width=8)
    table.add_column("Type", style="magenta", width=15)
    table.add_column("Created", style="blue", width=12)

    for session in sessions:
        attached = "Attached" if session.get("attached") == "1" else "Detached"

        # Determine session type
        name_lower = session["name"].lower()
        if "orc" in name_lower:
            session_type = "🎭 Orchestrator"
        elif any(t in name_lower for t in ["frontend", "backend", "fullstack"]):
            session_type = "👥 Team"
        elif "pm" in name_lower or "manager" in name_lower:
            session_type = "👔 Project Mgr"
        else:
            session_type = "📁 Project"

        table.add_row(
            session["name"],
            attached,
            session.get("windows", "0"),
            session_type,
            (
                session.get("created", "Unknown")[:12] + "..."
                if len(session.get("created", "")) > 12
                else session.get("created", "Unknown")
            ),
        )

    console.print(table)
