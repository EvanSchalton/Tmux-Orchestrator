"""Task list management commands - Main entry point using decomposed modules."""


from tmux_orchestrator.cli.tasks_core import tasks
from tmux_orchestrator.cli.tasks_export import export, list_tasks
from tmux_orchestrator.cli.tasks_project import archive, create, status
from tmux_orchestrator.cli.tasks_workflow import distribute, generate

# Register all subcommands with the main tasks group
tasks.add_command(create)
tasks.add_command(status)
tasks.add_command(distribute)
tasks.add_command(export)
tasks.add_command(archive)
tasks.add_command(list_tasks, name="list")
tasks.add_command(generate)

__all__ = ["tasks"]
