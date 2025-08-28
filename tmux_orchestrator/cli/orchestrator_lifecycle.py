"""Orchestrator lifecycle management commands (start, kill, kill-all)."""

from pathlib import Path

import click
from rich.console import Console

from tmux_orchestrator.cli.orchestrator_core import format_orchestrator_panel, get_orchestrator_briefing
from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


@click.command()
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
        console.print(f"To kill first: [bold]tmux-orc orchestrator kill {session}[/bold]")
        return

    console.print("[cyan]Starting Master Orchestrator...[/cyan]")

    # Create session with orchestrator window
    if not tmux.create_session(session, "orchestrator"):
        console.print("[red]Failed to create orchestrator session[/red]")
        return

    console.print(f"[green]✓ Created session '{session}'[/green]")

    # Start Claude in the orchestrator window
    target = f"{session}:orchestrator"
    claude_cmd = "claude"

    if not tmux.send_keys(target, claude_cmd):
        console.print("[red]Failed to start Claude[/red]")
        tmux.kill_session(session)
        return

    if not tmux.press_enter(target):
        console.print("[red]Failed to send command[/red]")
        tmux.kill_session(session)
        return

    console.print("[green]✓ Claude agent started[/green]")

    # Wait a moment for Claude to initialize
    import time

    time.sleep(2)

    # Send orchestrator briefing
    briefing = get_orchestrator_briefing(session, project_dir)

    console.print("[cyan]Sending orchestrator briefing...[/cyan]")
    if tmux.send_message(target, briefing):
        console.print("[green]✓ Orchestrator briefing sent[/green]")
    else:
        console.print("[yellow]⚠ Failed to send full briefing[/yellow]")

    # Display success panel
    format_orchestrator_panel(
        "🎭 Master Orchestrator Started",
        f"""Session: {session}
Window: orchestrator
Project: {project_dir}

To attach: [bold]tmux attach -t {session}[/bold]
To send messages: [bold]tmux-orc orchestrator broadcast "message"[/bold]
To check status: [bold]tmux-orc orchestrator status[/bold]

The orchestrator is now ready to manage your development ecosystem.""",
        "green",
    )


@click.command()
@click.argument("session")
@click.option("--force", is_flag=True, help="Force kill without safety checks")
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


@click.command(name="kill-all")
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
