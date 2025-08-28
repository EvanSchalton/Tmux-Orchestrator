"""Orchestrator schedule command - automated reminders and check-ins."""

import subprocess
from pathlib import Path

import click
from rich.console import Console

console = Console()


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
