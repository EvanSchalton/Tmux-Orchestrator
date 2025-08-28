"""Orchestrator management commands - Main entry point using decomposed modules."""


from tmux_orchestrator.cli.orchestrator_communication import broadcast, schedule
from tmux_orchestrator.cli.orchestrator_core import orchestrator
from tmux_orchestrator.cli.orchestrator_lifecycle import kill, kill_all, start
from tmux_orchestrator.cli.orchestrator_monitoring import list_sessions, status

# Register all subcommands with the main orchestrator group
orchestrator.add_command(start)
orchestrator.add_command(kill)
orchestrator.add_command(kill_all)
orchestrator.add_command(status)
orchestrator.add_command(list_sessions, name="list")
orchestrator.add_command(broadcast)
orchestrator.add_command(schedule)

__all__ = ["orchestrator"]
