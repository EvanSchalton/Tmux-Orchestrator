"""Orchestrator management commands for session scheduling and coordination."""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


@click.group()
def orchestrator() -> None:
    """Orchestrator operations."""
    pass


@orchestrator.command()
@click.option('--session', default='tmux-orc', help='Orchestrator session name')
@click.option('--project-dir', help='Project directory (defaults to current)')
@click.pass_context
def start(ctx: click.Context, session: str, project_dir: Optional[str]) -> None:
    """Start the main orchestrator session.

    Creates or attaches to the main orchestrator session where the primary
    orchestrator agent manages all teams and projects.
    """
    if not project_dir:
        project_dir = str(Path.cwd())

    tmux: TMUXManager = ctx.obj['tmux']

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
    if not tmux.send_keys(target, 'claude --dangerously-skip-permissions'):
        console.print("[red]✗ Failed to start Claude in orchestrator[/red]")
        return

    import time
    time.sleep(0.5)
    tmux.send_keys(target, 'Enter')
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
@click.argument('minutes', type=int)
@click.argument('note')
@click.option('--target', help='Target window (defaults to current orchestrator)')
@click.pass_context
def schedule(ctx: click.Context, minutes: int, note: str, target: Optional[str]) -> None:
    """Schedule a self-check or reminder message.

    MINUTES: Minutes from now to schedule the reminder
    NOTE: Reminder message or task description
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
        result = subprocess.run([
            script_path, str(minutes), note, target
        ], capture_output=True, text=True, check=False)

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
@click.option('--json', is_flag=True, help='Output in JSON format')
@click.pass_context
def status(ctx: click.Context, json: bool) -> None:
    """Show comprehensive orchestrator system status.

    Displays overview of all sessions, agents, and system health.
    """
    tmux: TMUXManager = ctx.obj['tmux']

    # Gather system status
    sessions = tmux.list_sessions()
    agents = tmux.list_agents()

    # Find orchestrator sessions
    orc_sessions = [s for s in sessions if 'orc' in s['name'].lower() or 'orchestrator' in s['name'].lower()]

    # Calculate summary stats
    total_sessions = len(sessions)
    total_agents = len(agents)
    active_agents = len([a for a in agents if a.get('status') == 'Active'])

    if json:
        import json as json_module
        status_data = {
            'timestamp': '2024-01-01T10:00:00Z',  # Would use real timestamp
            'orchestrator_sessions': orc_sessions,
            'total_sessions': total_sessions,
            'total_agents': total_agents,
            'active_agents': active_agents,
            'system_health': 'healthy' if active_agents > 0 else 'idle',
            'sessions': sessions,
            'agents': agents
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
            attached = "✓" if session.get('attached') == '1' else "○"
            orc_table.add_row(
                session['name'],
                attached,
                session.get('windows', '0'),
                session.get('created', 'Unknown')
            )
        console.print(orc_table)
    else:
        console.print("\n[yellow]No orchestrator sessions found[/yellow]")
        console.print("To start: [bold]tmux-orc orchestrator start[/bold]")

    # Recent activity summary
    if agents:
        console.print("\n[bold]📊 Agent Activity Overview:[/bold]")
        # Group by session
        sessions_with_agents: Dict[str, List[Dict[str, Any]]] = {}
        for agent in agents:
            session_name = agent.get('session', 'unknown')
            if session_name not in sessions_with_agents:
                sessions_with_agents[session_name] = []
            sessions_with_agents[session_name].append(agent)

        for session_name, session_agents in list(sessions_with_agents.items())[:5]:  # Top 5
            active_count = len([a for a in session_agents if a.get('status') == 'Active'])
            total_count = len(session_agents)
            console.print(f"  • {session_name}: {active_count}/{total_count} active")


@orchestrator.command()
@click.option('--all-sessions', is_flag=True, help='List all sessions, not just orchestrator')
@click.option('--json', is_flag=True, help='Output in JSON format')
@click.pass_context
def list(ctx: click.Context, all_sessions: bool, json: bool) -> None:
    """List orchestrator and project sessions.

    Shows active sessions with agent counts and status information.
    """
    tmux: TMUXManager = ctx.obj['tmux']

    sessions = tmux.list_sessions()
    if not all_sessions:
        # Filter to orchestrator and project sessions
        sessions = [s for s in sessions if any(keyword in s['name'].lower()
                   for keyword in ['orc', 'orchestrator', 'frontend', 'backend', 'team', 'project'])]

    if json:
        import json as json_module
        console.print(json_module.dumps(sessions, indent=2))
        return

    if not sessions:
        console.print("[yellow]No orchestrator sessions found[/yellow]")
        console.print("\nTo start orchestrator: [bold]tmux-orc orchestrator start[/bold]")
        return

    console.print(f"[bold]🎭 {'All Sessions' if all_sessions else 'Orchestrator & Project Sessions'} ({len(sessions)}):[/bold]")

    table = Table()
    table.add_column("Session", style="cyan", width=20)
    table.add_column("Status", style="green", width=10)
    table.add_column("Windows", style="yellow", width=8)
    table.add_column("Type", style="magenta", width=15)
    table.add_column("Created", style="blue", width=12)

    for session in sessions:
        attached = "Attached" if session.get('attached') == '1' else "Detached"

        # Determine session type
        name_lower = session['name'].lower()
        if 'orc' in name_lower:
            session_type = "🎭 Orchestrator"
        elif any(t in name_lower for t in ['frontend', 'backend', 'fullstack']):
            session_type = "👥 Team"
        elif 'pm' in name_lower or 'manager' in name_lower:
            session_type = "👔 Project Mgr"
        else:
            session_type = "📁 Project"

        table.add_row(
            session['name'],
            attached,
            session.get('windows', '0'),
            session_type,
            session.get('created', 'Unknown')[:12] + '...' if len(session.get('created', '')) > 12 else session.get('created', 'Unknown')
        )

    console.print(table)


@orchestrator.command()
@click.argument('session')
@click.option('--force', is_flag=True, help='Force kill without confirmation')
@click.pass_context
def kill(ctx: click.Context, session: str, force: bool) -> None:
    """Kill a specific session and all its agents.

    SESSION: Session name to terminate
    """
    tmux: TMUXManager = ctx.obj['tmux']

    if not tmux.has_session(session):
        console.print(f"[red]✗ Session '{session}' not found[/red]")
        return

    # Safety check for orchestrator session
    if 'orc' in session.lower() and not force:
        console.print("[yellow]⚠ You're about to kill an orchestrator session![/yellow]")
        console.print("This will terminate the main orchestrator. Use --force to confirm.")
        return

    console.print(f"[yellow]Killing session '{session}' and all its agents...[/yellow]")

    if tmux.kill_session(session):
        console.print(f"[green]✓ Session '{session}' killed successfully[/green]")
    else:
        console.print(f"[red]✗ Failed to kill session '{session}'[/red]")


@orchestrator.command()
@click.argument('message')
@click.option('--all-sessions', is_flag=True, help='Broadcast to all sessions')
@click.option('--session-filter', help='Filter sessions by name pattern')
@click.pass_context
def broadcast(ctx: click.Context, message: str, all_sessions: bool, session_filter: Optional[str]) -> None:
    """Broadcast a message from the orchestrator to project teams.

    MESSAGE: Message to broadcast to teams
    """
    tmux: TMUXManager = ctx.obj['tmux']

    sessions = tmux.list_sessions()

    if not all_sessions:
        # Filter to project/team sessions (exclude orchestrator)
        sessions = [s for s in sessions if not any(keyword in s['name'].lower()
                   for keyword in ['orc', 'orchestrator'])]

    if session_filter:
        sessions = [s for s in sessions if session_filter.lower() in s['name'].lower()]

    if not sessions:
        console.print("[yellow]No target sessions found for broadcast[/yellow]")
        return

    console.print(f"[blue]Broadcasting to {len(sessions)} sessions...[/blue]")

    success_count = 0
    for session in sessions:
        session_name = session['name']

        # Find PM or main agent window in session
        windows = tmux.list_windows(session_name)
        target_window = None

        for window in windows:
            window_name = window['name'].lower()
            if any(keyword in window_name for keyword in ['pm', 'manager', 'claude']):
                target_window = f"{session_name}:{window['index']}"
                break

        if target_window:
            if tmux.send_message(target_window, f"🎭 ORCHESTRATOR BROADCAST: {message}"):
                console.print(f"  [green]✓ {session_name}[/green]")
                success_count += 1
            else:
                console.print(f"  [red]✗ {session_name}[/red]")
        else:
            console.print(f"  [yellow]⚠ {session_name} (no suitable window)[/yellow]")

    console.print(f"\n[bold]Broadcast completed: {success_count}/{len(sessions)} successful[/bold]")
