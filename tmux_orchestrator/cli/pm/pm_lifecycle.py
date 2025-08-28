"""Project Manager lifecycle commands."""

import json as json_module
import time
from pathlib import Path

import click
from rich.console import Console

from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


@click.command()
@click.argument("session")
@click.option("--project-dir", help="Project directory (defaults to current)")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def create(ctx: click.Context, session: str, project_dir: str | None, json: bool) -> None:
    """Create a new Project Manager for team coordination and oversight.

    <mcp>Create PM agent in session for team coordination (args: [session], options: --project-dir, --json). Deploys specialized Claude PM with team leadership capabilities. Use vs spawn pm for session-specific PM creation.</mcp>

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

    start_time = time.time()

    if not project_dir:
        project_dir = str(Path.cwd())

    tmux: TMUXManager = ctx.obj["tmux"]
    pm_window = "Project-Manager"

    # Track creation steps for JSON output
    steps_completed = []
    success = True
    error_message = None

    try:
        # 1. Check for existing PM in the target session
        existing_pm = None
        if tmux.has_session(session):
            windows = tmux.list_windows(session)
            for window in windows:
                if any(pattern in window["name"].lower() for pattern in ["pm", "project-manager", "claude-pm"]):
                    existing_pm = f"{session}:{window['index']}"
                    break

        # 2. Handle existing PM
        if existing_pm:
            if not json:
                console.print(f"[yellow]PM already exists at {existing_pm}[/yellow]")
                console.print("[blue]Replacing existing PM...[/blue]")

            # Kill the existing PM window
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"🔪 PM LIFECYCLE KILL: pm_lifecycle.py killing existing PM window: {existing_pm}")
            logger.warning("🔪 KILL REASON: PM already exists, replacing with new PM")
            logger.warning("🔪 CALL STACK: pm_lifecycle.create() -> tmux.kill_window()")

            if tmux.kill_window(existing_pm):
                steps_completed.append("existing_pm_replaced")
            else:
                if not json:
                    console.print("[yellow]⚠ Could not remove existing PM, continuing...[/yellow]")

        # 3. Create session if needed (but without PM window name conflict)
        session_existed = tmux.has_session(session)
        if not session_existed:
            if not json:
                console.print(f"[blue]Creating new session: {session}[/blue]")
            # Create session with generic first window name to avoid conflicts
            if not tmux.create_session(session, "main", project_dir):
                error_message = f"Failed to create session {session}"
                success = False
                raise Exception(error_message)
            steps_completed.append("session_created")
        else:
            steps_completed.append("session_existed")

        # 4. Create PM window (guaranteed unique since we cleaned up existing PM)
        if not tmux.create_window(session, pm_window, project_dir):
            error_message = f"Failed to create PM window in {session}"
            success = False
            raise Exception(error_message)
        steps_completed.append("pm_window_created")

        # 5. Get the actual window index for targeting
        windows = tmux.list_windows(session)
        pm_window_index = None
        for window in windows:
            if window["name"] == "Project-Manager":
                pm_window_index = window["index"]
                break

        if not pm_window_index:
            error_message = "Failed to find created PM window"
            success = False
            raise Exception(error_message)

        target = f"{session}:{pm_window_index}"  # Use index, not name

        # 6. Start Claude PM
        if not json:
            console.print(f"[blue]Starting Project Manager at {target}...[/blue]")

        # Start Claude
        if not tmux.send_text(target, "claude --dangerously-skip-permissions"):
            error_message = f"Failed to start Claude in {target}"
            success = False
            raise Exception(error_message)
        steps_completed.append("claude_started")

        time.sleep(0.5)
        tmux.press_enter(target)
        time.sleep(3)  # Wait for Claude to start

        # Send PM briefing
        pm_briefing = """You are the Project Manager for this development team. Your responsibilities:

1. Coordinate team activities and maintain project timeline
2. Ensure quality standards are met across all deliverables
3. Monitor progress and identify blockers quickly
4. Facilitate communication between team members
5. Report status updates to the orchestrator

🔄 AGENT RESTART & RECOVERY:
When agents fail and need restart, use the team plan you created to determine their role briefing, then restart with:
claude --dangerously-skip-permissions --system-prompt "[role from team plan]"

Steps for agent recovery:
1. Navigate to failed agent's window: tmux select-window -t <session:window>
2. Reference your team plan for the correct role briefing
3. Restart with proper role: claude --dangerously-skip-permissions --system-prompt "..."
4. Verify agent is responsive before reassigning tasks

Begin by analyzing the project structure and creating an initial project plan."""

        briefing_success = tmux.send_message(target, pm_briefing)
        if briefing_success:
            steps_completed.append("briefing_sent")
        else:
            steps_completed.append("briefing_failed")

    except Exception as e:
        success = False
        if not error_message:
            error_message = str(e)

    execution_time = (time.time() - start_time) * 1000

    result_data = {
        "success": success,
        "command": "pm create",
        "session": session,
        "target": target,
        "window": pm_window,
        "project_directory": project_dir,
        "steps_completed": steps_completed,
        "session_existed": session_existed if "session_existed" in locals() else False,
        "briefing_success": briefing_success if "briefing_success" in locals() else False,
        "execution_time_ms": execution_time,
        "timestamp": time.time(),
    }

    if not success:
        result_data["error"] = error_message

    if json:
        console.print(json_module.dumps(result_data, indent=2))
    else:
        if success:
            console.print(f"[green]✓ Project Manager created successfully at {target}[/green]")
            console.print(f"  Session: {session}")
            console.print(f"  Window: {pm_window}")
            console.print(f"  Directory: {project_dir}")
            if not briefing_success:
                console.print("[yellow]⚠ PM created but briefing may have failed[/yellow]")
        else:
            console.print(f"[red]✗ {error_message}[/red]")
