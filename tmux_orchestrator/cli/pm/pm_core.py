"""Project Manager core CLI commands and shared utilities."""

import click
from rich.console import Console

from .pm_communication import broadcast, message
from .pm_lifecycle import create
from .pm_status import checkin, custom_checkin, status

console: Console = Console()


@click.group()
def pm() -> None:
    """Project Manager operations and team coordination.

    The PM command group provides tools for creating and managing Project Managers,
    specialized Claude agents responsible for team coordination, quality assurance,
    and project oversight.

    Examples:
        tmux-orc pm create my-project           # Create PM for project
        tmux-orc pm status                      # Check PM and team status
        tmux-orc pm checkin                     # Trigger team status review
        tmux-orc pm message "Sprint review at 3pm"
        tmux-orc pm broadcast "Deploy to staging now"

    Project Manager Responsibilities:
        • Team coordination and communication
        • Quality standards enforcement
        • Progress monitoring and reporting
        • Risk identification and mitigation
        • Resource allocation and optimization

    PM agents work alongside development teams to ensure projects
    stay on track and meet quality standards.
    """
    pass


# Register all commands
pm.add_command(checkin)
pm.add_command(message)
pm.add_command(broadcast)
pm.add_command(custom_checkin)
pm.add_command(status)
pm.add_command(create)
