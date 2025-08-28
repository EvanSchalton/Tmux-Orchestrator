"""Orchestrator management commands for session scheduling and coordination."""

import click
from rich.console import Console

console: Console = Console()


@click.group()
@click.pass_context
def orchestrator(ctx: click.Context) -> None:
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


# Import and register command functions
from .broadcast_message import broadcast
from .kill_all_sessions import kill_all
from .kill_session import kill
from .list_sessions import list_sessions
from .schedule_reminder import schedule

# from .start_orchestrator import start  # TODO: Fix missing @click.command decorator
from .status_orchestrator import status

# Register commands with the CLI group
# orchestrator.add_command(start)  # TODO: Re-enable when fixed
orchestrator.add_command(schedule)
orchestrator.add_command(status)
orchestrator.add_command(list_sessions, name="list")
orchestrator.add_command(kill)
orchestrator.add_command(kill_all)
orchestrator.add_command(broadcast)

# Export the main orchestrator group for backwards compatibility
__all__ = ["orchestrator"]
