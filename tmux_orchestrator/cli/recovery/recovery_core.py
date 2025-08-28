"""Recovery system core CLI commands and shared utilities."""

from pathlib import Path

import click

from .recovery_daemon_commands import start_recovery, stop_recovery
from .recovery_status import recovery_status
from .recovery_testing import test_recovery


# Use secure project directory instead of /tmp
def get_project_dir() -> Path:
    """Get project directory, creating it only when needed."""
    project_dir = Path.cwd() / ".tmux_orchestrator"
    try:
        project_dir.mkdir(exist_ok=True)
        return project_dir
    except PermissionError:
        # Fallback to user home directory if current directory is not writable
        home_project_dir = Path.home() / ".tmux_orchestrator"
        home_project_dir.mkdir(exist_ok=True)
        return home_project_dir


def get_logs_dir() -> Path:
    """Get logs directory, creating it only when needed."""
    logs_dir = get_project_dir() / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


@click.group()
def recovery() -> None:
    """Automatic agent recovery system management.

    The recovery system provides continuous monitoring and automatic
    recovery of failed Claude agents across all tmux sessions.

    Key Features:
        • Automatic detection of failed Claude agents
        • Intelligent recovery with proper briefings
        • Configurable monitoring intervals and thresholds
        • Comprehensive logging and status reporting
        • Daemon mode for continuous operation
    """
    pass


# Register all commands
recovery.add_command(start_recovery)
recovery.add_command(stop_recovery)
recovery.add_command(recovery_status)
recovery.add_command(test_recovery)
