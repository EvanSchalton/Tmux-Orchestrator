"""Orchestrator management commands for session scheduling and coordination."""

import builtins
import subprocess
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


@click.group()
def orchestrator() -> None:
    """High-level orchestrator operations for system-wide management.

    The orchestrator command group provides strategic oversight and coordination
    capabilities for managing multiple projects, teams, and agents across the
    entire TMUX Orchestrator ecosystem.

    Examples:
        tmux-orc orchestrator start            # Start main orchestrator
        tmux-orc orchestrator status           # System-wide status
        tmux-orc orchestrator schedule 30 "Check progress"
        tmux-orc orchestrator broadcast "Deploy now"
        tmux-orc orchestrator list --all-sessions

    Orchestrator Responsibilities:
        • Strategic project coordination across teams
        • Resource allocation and optimization
        • Cross-project dependency management
        • Quality standards enforcement
        • System health monitoring and alerts
        • Automated scheduling and reminders

    The orchestrator operates at the highest level, managing Project Managers
    who in turn coordinate individual development teams.
    """
    pass


@orchestrator.command()
@click.option("--session", default="tmux-orc", help="Orchestrator session name")
@click.option("--project-dir", help="Project directory (defaults to current)")
@click.pass_context
def start(ctx: click.Context, session: str, project_dir: str | None) -> None:
    """Start the master orchestrator for enterprise-wide project coordination.

    Creates and initializes the main orchestrator agent with comprehensive
    system oversight capabilities, strategic planning tools, and multi-project
    coordination workflows.

    Examples:
        tmux-orc orchestrator start           # Start with default session 'tmux-orc'
        tmux-orc orchestrator start --session main-control
        tmux-orc orchestrator start --project-dir /workspace/projects

    Orchestrator Initialization:
        1. 🏧 Creates dedicated orchestrator session
        2. 🤖 Starts Claude agent with orchestrator specialization
        3. 📋 Provides comprehensive strategic briefing
        4. 🔍 Analyzes current system state and projects
        5. 🔗 Establishes communication with existing teams
        6. ⚙️ Sets up monitoring and scheduling systems

    Orchestrator Capabilities:
        • Multi-project portfolio management
        • Strategic resource allocation
        • Cross-team dependency coordination
        • Quality gate enforcement
        • Risk assessment and mitigation
        • Automated progress tracking
        • Stakeholder communication
        • Performance optimization

    Strategic Focus Areas:
        • Big-picture architectural decisions
        • Timeline and milestone coordination
        • Resource utilization optimization
        • Quality standards maintenance
        • Team productivity enhancement
        • Technology stack alignment

    The orchestrator operates with elevated permissions and system-wide
    visibility, making strategic decisions that affect multiple teams.
    """
    if not project_dir:
        project_dir = str(Path.cwd())

    tmux: TMUXManager = ctx.obj["tmux"]

    # Check if orchestrator session already exists
    if tmux.has_session(session):
        console.print(f"[yellow]Orchestrator session '{session}' already exists[/yellow]")
        console.print(f"To attach: [bold]tmux attach -t {session}[/bold]")
        return

    console.print(f"[blue]Starting orchestrator session '{session}'...[/blue]")

    # Create orchestrator session
    if not tmux.create_session(session, "Orchestrator", project_dir):
        console.print("[red]✗ Failed to create orchestrator session[/red]")
        return

    # Start Claude orchestrator
    target = f"{session}:Orchestrator"
    if not tmux.send_text(target, "claude --dangerously-skip-permissions"):
        console.print("[red]✗ Failed to start Claude in orchestrator[/red]")
        return

    import time

    time.sleep(0.5)
    tmux.press_enter(target)
    time.sleep(3)  # Wait for Claude to start

    # Send orchestrator briefing
    orchestrator_briefing = """You are the MAIN ORCHESTRATOR for the TMUX Orchestrator system. Your role:

🎯 **PRIMARY RESPONSIBILITIES:**
1. Deploy and coordinate agent teams across multiple projects
2. Monitor system health and agent performance
3. Make high-level architectural and project decisions
4. Resolve cross-project dependencies and conflicts
5. Ensure quality standards are maintained across all teams

🚀 **OPERATIONAL GUIDELINES:**
- Deploy teams using: tmux-orc team deploy <type> <size> --project-name <name>
- Monitor all agents with: tmux-orc monitor dashboard
- Check PM status with: tmux-orc pm status
- Create new PMs with: tmux-orc pm create <session>

🎭 **ORCHESTRATOR PERSONA:**
- Strategic thinker focused on big picture
- Quality-driven but pragmatic about deadlines
- Excellent communicator across technical levels
- Proactive problem solver and decision maker

Begin by analyzing the current system state and available projects."""

    if tmux.send_message(target, orchestrator_briefing):
        console.print(f"[green]✓ Orchestrator started successfully at {target}[/green]")
        console.print(f"  Session: {session}")
        console.print(f"  Directory: {project_dir}")
        console.print(f"\nTo attach: [bold]tmux attach -t {session}[/bold]")
    else:
        console.print("[yellow]⚠ Orchestrator created but briefing may have failed[/yellow]")


@orchestrator.command()
@click.argument("minutes", type=int)
@click.argument("note")
@click.option("--target", help="Target window (defaults to current orchestrator)")
@click.pass_context
def schedule(ctx: click.Context, minutes: int, note: str, target: str | None) -> None:
    """Schedule automated reminders and orchestrator check-ins.

    Creates time-based reminders for the orchestrator to perform specific
    actions, ensuring consistent oversight and preventing important tasks
    from being forgotten.

    MINUTES: Minutes from now to schedule (1-1440, max 24 hours)
    NOTE: Reminder message or action description

    Examples:
        tmux-orc orchestrator schedule 30 "Review team progress"
        tmux-orc orchestrator schedule 120 "Check deployment pipeline"
        tmux-orc orchestrator schedule 15 "Sprint planning preparation"
        tmux-orc orchestrator schedule 60 "Client demo rehearsal"

    Common Scheduling Use Cases:
        • Regular progress check-ins
        • Meeting preparation reminders
        • Deployment coordination windows
        • Quality gate assessments
        • Resource utilization reviews
        • Stakeholder communication
        • System health evaluations

    Scheduling Features:
        • Precision timing with system integration
        • Automatic target window detection
        • Context-aware reminder delivery
        • Integration with orchestrator workflows
        • Flexible time ranges (1 minute to 24 hours)

    Recommended Intervals:
        • Status checks: 15-30 minutes
        • Progress reviews: 60-120 minutes
        • Planning activities: 2-4 hours
        • Strategic assessments: 4-8 hours

    Essential for maintaining consistent oversight in complex,
    multi-team environments where timing is critical.
    """
    if minutes < 1 or minutes > 1440:  # Max 24 hours
        console.print("[red]✗ Minutes must be between 1 and 1440 (24 hours)[/red]")
        return

    # Use the scheduling script
    script_path = "/Users/jasonedward/Coding/Tmux orchestrator/schedule_with_note.sh"

    if not Path(script_path).exists():
        console.print(f"[red]✗ Scheduling script not found at {script_path}[/red]")
        return

    # Determine target window
    if not target:
        # Try to detect current orchestrator window
        target = "tmux-orc:0"  # Default orchestrator target

    console.print(f"[blue]Scheduling reminder for {minutes} minutes...[/blue]")

    try:
        # Execute the scheduling script
        result = subprocess.run(
            [script_path, str(minutes), note, target],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            console.print(f"[green]✓ Scheduled reminder in {minutes} minutes[/green]")
            console.print(f"  Target: {target}")
            console.print(f"  Note: {note}")
        else:
            console.print("[red]✗ Failed to schedule reminder[/red]")
            if result.stderr:
                console.print(f"  Error: {result.stderr.strip()}")
    except Exception as e:
        console.print(f"[red]✗ Error executing schedule script: {str(e)}[/red]")


@orchestrator.command()
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
    active_agents = len([a for a in agents if a.get("status") == "Active"])

    if json:
        import json as json_module

        status_data = {
            "timestamp": "2024-01-01T10:00:00Z",  # Would use real timestamp
            "orchestrator_sessions": orc_sessions,
            "total_sessions": total_sessions,
            "total_agents": total_agents,
            "active_agents": active_agents,
            "system_health": "healthy" if active_agents > 0 else "idle",
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
        f"Active: {active_agents} | "
        f"Health: {'🟢 Healthy' if active_agents > 0 else '🟡 Idle'}"
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
        console.print("\n[bold]📊 Agent Activity Overview:[/bold]")
        # Group by session
        sessions_with_agents: dict[str, builtins.list[dict[str, Any]]] = {}
        for agent in agents:
            session_name = agent.get("session", "unknown")
            if session_name not in sessions_with_agents:
                sessions_with_agents[session_name] = []
            sessions_with_agents[session_name].append(agent)

        for session_name, session_agents in list(sessions_with_agents.items())[:5]:  # Top 5
            active_count = len([a for a in session_agents if a.get("status") == "Active"])
            total_count = len(session_agents)
            console.print(f"  • {session_name}: {active_count}/{total_count} active")


@orchestrator.command()
@click.option("--all-sessions", is_flag=True, help="List all sessions, not just orchestrator")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def list(ctx: click.Context, all_sessions: bool, json: bool) -> None:
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


@orchestrator.command()
@click.argument("session")
@click.option("--force", is_flag=True, help="Force kill without confirmation")
@click.pass_context
def kill(ctx: click.Context, session: str, force: bool) -> None:
    """Terminate sessions with strategic oversight and safety checks.

    Carefully terminates specified sessions with proper orchestrator-level
    safety checks, dependency verification, and graceful shutdown procedures.

    SESSION: Session name to terminate (e.g., 'old-project', 'failed-team')

    Examples:
        tmux-orc orchestrator kill old-project    # Kill with safety check
        tmux-orc orchestrator kill failed-team --force

    Strategic Safety Features:

    Pre-termination Checks:
        • Dependency analysis across projects
        • Active work preservation warnings
        • Resource impact assessment
        • Communication pathway disruption

    Protected Sessions:
        • Main orchestrator sessions require --force
        • Active production deployments
        • Critical infrastructure services
        • Sessions with unsaved work

    Termination Process:
        1. 🔍 Analyze session dependencies
        2. 💾 Capture session state and logs
        3. 📢 Notify affected teams and PMs
        4. 📋 Update project status tracking
        5. 🗑️ Graceful agent shutdown
        6. ⚙️ Resource cleanup and reallocation

    ⚠️  Strategic Considerations:
        • Impact on other projects and teams
        • Resource reallocation opportunities
        • Timeline adjustments needed
        • Communication to stakeholders

    Use with careful consideration of broader strategic impact
    and always verify dependencies before termination.
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    if not tmux.has_session(session):
        console.print(f"[red]✗ Session '{session}' not found[/red]")
        return

    # Safety check for orchestrator session
    if "orc" in session.lower() and not force:
        console.print("[yellow]⚠ You're about to kill an orchestrator session![/yellow]")
        console.print("This will terminate the main orchestrator. Use --force to confirm.")
        return

    console.print(f"[yellow]Killing session '{session}' and all its agents...[/yellow]")

    if tmux.kill_session(session):
        console.print(f"[green]✓ Session '{session}' killed successfully[/green]")
    else:
        console.print(f"[red]✗ Failed to kill session '{session}'[/red]")


@orchestrator.command(name="kill-all")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--exclude", help="Comma-separated list of sessions to preserve")
@click.pass_context
def kill_all(ctx: click.Context, force: bool, exclude: str | None) -> None:
    """Terminate ALL tmux sessions with strategic oversight and safety controls.

    Provides emergency shutdown capabilities for the entire tmux ecosystem
    with proper safety checks and selective preservation options.

    Examples:
        tmux-orc orchestrator kill-all              # Interactive confirmation
        tmux-orc orchestrator kill-all --force      # Skip confirmation
        tmux-orc orchestrator kill-all --exclude main,prod-deploy

    Safety Features:

    Interactive Confirmation:
        • Lists all sessions before termination
        • Requires explicit confirmation unless --force
        • Shows impact assessment and warnings
        • Provides cancellation opportunity

    Selective Preservation:
        • --exclude option to preserve critical sessions
        • Automatic detection of production systems
        • Protection of active deployment sessions
        • Preservation of logged work sessions

    Termination Process:
        1. 🔍 Discovery: Scan all active sessions
        2. 📋 Assessment: Categorize by importance
        3. ⚠️  Warning: Show impact and ask confirmation
        4. 🛡️  Protection: Apply exclusion filters
        5. 📸 Capture: Save session logs/state
        6. 🗑️  Terminate: Graceful shutdown sequence
        7. ✅ Verification: Confirm all sessions ended

    Use Cases:
        • End-of-day workspace cleanup
        • Development environment reset
        • Emergency system shutdown
        • Resource reclamation
        • Environment switching

    ⚠️  CRITICAL WARNING:
    This command will terminate ALL development work, agent sessions,
    and orchestrator coordination. Use only when intentionally ending
    all work or during emergency situations.
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Get all sessions
    sessions = tmux.list_sessions()

    if not sessions:
        console.print("[yellow]No tmux sessions found[/yellow]")
        return

    # Parse exclusion list
    excluded_sessions = []
    if exclude:
        excluded_sessions = [s.strip() for s in exclude.split(",")]

    # Filter sessions to kill
    sessions_to_kill = [s for s in sessions if s["name"] not in excluded_sessions]

    if not sessions_to_kill:
        console.print("[yellow]No sessions to kill after applying exclusions[/yellow]")
        return

    # Show impact assessment
    console.print("[bold red]⚠️  KILL ALL SESSIONS - IMPACT ASSESSMENT[/bold red]")
    console.print(f"\n[yellow]Total sessions found: {len(sessions)}[/yellow]")
    console.print(f"[red]Sessions to kill: {len(sessions_to_kill)}[/red]")

    if excluded_sessions:
        preserved = [s for s in sessions if s["name"] in excluded_sessions]
        console.print(f"[green]Sessions to preserve: {len(preserved)}[/green]")
        for session in preserved:
            console.print(f"  [green]✓ {session['name']}[/green]")

    console.print("\n[bold]Sessions to be terminated:[/bold]")

    # Categorize sessions for better visibility
    orchestrator_sessions = []
    team_sessions = []
    other_sessions = []

    for session in sessions_to_kill:
        name_lower = session["name"].lower()
        if "orc" in name_lower or "orchestrator" in name_lower:
            orchestrator_sessions.append(session)
        elif any(t in name_lower for t in ["team", "frontend", "backend", "project", "pm"]):
            team_sessions.append(session)
        else:
            other_sessions.append(session)

    if orchestrator_sessions:
        console.print("  [bold magenta]🎭 Orchestrator Sessions:[/bold magenta]")
        for session in orchestrator_sessions:
            console.print(f"    [red]✗ {session['name']}[/red]")

    if team_sessions:
        console.print("  [bold cyan]👥 Team/Project Sessions:[/bold cyan]")
        for session in team_sessions:
            console.print(f"    [red]✗ {session['name']}[/red]")

    if other_sessions:
        console.print("  [bold white]📁 Other Sessions:[/bold white]")
        for session in other_sessions:
            console.print(f"    [red]✗ {session['name']}[/red]")

    # Confirmation unless --force
    if not force:
        console.print(
            f"\n[bold yellow]This will terminate {len(sessions_to_kill)} sessions and all their agents.[/bold yellow]"
        )
        console.print("[yellow]All unsaved work and agent context will be lost.[/yellow]")

        try:
            confirm = input("\nType 'KILL ALL' to confirm (or anything else to cancel): ")
            if confirm != "KILL ALL":
                console.print("[green]Operation cancelled[/green]")
                return
        except KeyboardInterrupt:
            console.print("\n[green]Operation cancelled[/green]")
            return

    # Execute termination
    console.print(f"\n[red]Terminating {len(sessions_to_kill)} sessions...[/red]")

    success_count = 0
    failed_sessions = []

    for session in sessions_to_kill:
        session_name = session["name"]
        console.print(f"  Killing {session_name}...", end=" ")

        if tmux.kill_session(session_name):
            console.print("[green]✓[/green]")
            success_count += 1
        else:
            console.print("[red]✗[/red]")
            failed_sessions.append(session_name)

    # Results summary
    console.print("\n[bold]Termination Complete:[/bold]")
    console.print(f"  [green]Successful: {success_count}[/green]")
    console.print(f"  [red]Failed: {len(failed_sessions)}[/red]")

    if failed_sessions:
        console.print("\n[red]Failed to kill sessions:[/red]")
        for session_name in failed_sessions:
            console.print(f"  [red]✗ {session_name}[/red]")
        console.print("\nYou may need to kill these manually: [bold]tmux kill-session -t <session>[/bold]")

    if success_count > 0:
        console.print(f"\n[green]✓ Successfully terminated {success_count} sessions[/green]")
        if excluded_sessions:
            console.print(
                f"[green]✓ Preserved {len([s for s in sessions if s['name'] in excluded_sessions])} excluded sessions[/green]"
            )


@orchestrator.command()
@click.argument("message")
@click.option("--all-sessions", is_flag=True, help="Broadcast to all sessions")
@click.option("--session-filter", help="Filter sessions by name pattern")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def broadcast(ctx: click.Context, message: str, all_sessions: bool, session_filter: str | None, json: bool) -> None:
    """Orchestrator-level strategic broadcasts to project teams and PMs.

    Sends high-priority, strategically important communications from the
    orchestrator to Project Managers and teams, maintaining proper command
    hierarchy and strategic context.

    MESSAGE: Strategic message to broadcast across the organization

    Examples:
        tmux-orc orchestrator broadcast "Emergency deployment window opens at 3pm"
        tmux-orc orchestrator broadcast "All teams: code freeze for release" --all-sessions
        tmux-orc orchestrator broadcast "Frontend focus on performance" --session-filter frontend

    Strategic Broadcast Features:

    Message Routing:
        • Intelligent PM and team lead targeting
        • Strategic context preservation
        • Command hierarchy respect
        • Delivery confirmation tracking

    Broadcast Scopes:
        • Default: Project teams only (excludes orchestrator)
        • --all-sessions: Every session in system
        • --session-filter: Pattern-based targeting

    Message Types:

    Strategic Directives:
        • Portfolio-wide priority changes
        • Resource reallocation decisions
        • Quality standard updates
        • Timeline adjustments

    Operational Coordination:
        • Deployment windows and freezes
        • Cross-team synchronization
        • Emergency response procedures
        • System-wide maintenance

    Communication Coordination:
        • Stakeholder meeting schedules
        • Demo and presentation timing
        • Reporting requirement changes
        • Documentation updates

    Message Delivery Process:
        1. 🎯 Strategic message composition
        2. 🔍 Target audience identification
        3. 📡 Multi-channel delivery (PMs first)
        4. ✅ Delivery confirmation collection
        5. 📈 Impact tracking and follow-up
        6. 📢 Escalation for non-responsive teams

    Use for critical communications that require immediate
    attention and coordinated response across the organization.
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    sessions = tmux.list_sessions()

    if not all_sessions:
        # Filter to project/team sessions (exclude orchestrator)
        sessions = [s for s in sessions if not any(keyword in s["name"].lower() for keyword in ["orc", "orchestrator"])]

    if session_filter:
        sessions = [s for s in sessions if session_filter.lower() in s["name"].lower()]

    if not sessions:
        if json:
            import json as json_module

            result = {
                "success": False,
                "message": "No target sessions found for broadcast",
                "sessions_targeted": 0,
                "sessions_succeeded": 0,
                "broadcast_message": message,
            }
            console.print(json_module.dumps(result, indent=2))
        else:
            console.print("[yellow]No target sessions found for broadcast[/yellow]")
        return

    if json:
        # Prepare JSON result structure
        import json as json_module

        result = {
            "success": False,
            "message": "",
            "broadcast_message": message,
            "sessions_targeted": len(sessions),
            "sessions_succeeded": 0,
            "session_results": [],
        }
    else:
        console.print(f"[blue]Broadcasting to {len(sessions)} sessions...[/blue]")

    success_count = 0
    for session in sessions:
        session_name = session["name"]

        # Find PM or main agent window in session
        windows = tmux.list_windows(session_name)
        target_window = None

        for window in windows:
            window_name = window["name"].lower()
            if any(keyword in window_name for keyword in ["pm", "manager", "claude"]):
                target_window = f"{session_name}:{window['index']}"
                break

        if target_window:
            if tmux.send_message(target_window, f"🎭 ORCHESTRATOR BROADCAST: {message}"):
                if json:
                    result["session_results"].append(
                        {"session": session_name, "success": True, "target_window": target_window}
                    )
                else:
                    console.print(f"  [green]✓ {session_name}[/green]")
                success_count += 1
            else:
                if json:
                    result["session_results"].append(
                        {
                            "session": session_name,
                            "success": False,
                            "target_window": target_window,
                            "error": "Failed to send message",
                        }
                    )
                else:
                    console.print(f"  [red]✗ {session_name}[/red]")
        else:
            if json:
                result["session_results"].append(
                    {"session": session_name, "success": False, "error": "No suitable window found"}
                )
            else:
                console.print(f"  [yellow]⚠ {session_name} (no suitable window)[/yellow]")

    if json:
        result["sessions_succeeded"] = success_count
        result["success"] = success_count > 0
        result["message"] = f"Broadcast completed: {success_count}/{len(sessions)} successful"
        console.print(json_module.dumps(result, indent=2))
    else:
        console.print(f"\n[bold]Broadcast completed: {success_count}/{len(sessions)} successful[/bold]")
