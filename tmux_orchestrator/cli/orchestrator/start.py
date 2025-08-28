"""Orchestrator start command - session creation and initialization."""

import time
from pathlib import Path

import click
from rich.console import Console

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


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
