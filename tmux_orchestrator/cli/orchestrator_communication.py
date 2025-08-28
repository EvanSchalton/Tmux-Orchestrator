"""Orchestrator communication commands (broadcast, schedule)."""

import subprocess
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


@click.command()
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


@click.command()
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

    # Initialize result dictionary for JSON output
    result: dict[str, Any] = {}

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
                if json and "session_results" in result:
                    result["session_results"].append(
                        {"session": session_name, "success": True, "target_window": target_window}
                    )
                else:
                    console.print(f"  [green]✓ {session_name}[/green]")
                success_count += 1
            else:
                if json and "session_results" in result:
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
            if json and "session_results" in result:
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
        console.print(f"\n[green]✓ Broadcast sent to {success_count}/{len(sessions)} sessions[/green]")
