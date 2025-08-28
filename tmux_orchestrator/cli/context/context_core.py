"""Context core CLI commands and shared utilities."""

import click

from .context_display import list_contexts, show_context
from .context_export import export_context
from .context_spawn import spawn_context


@click.group()
def context() -> None:
    """Manage agent context and standardized briefings.

    The context system provides standardized briefings for different agent roles,
    ensuring consistent behavior and capabilities across the orchestration system.
    """
    pass


# Register all commands
context.add_command(show_context)
context.add_command(list_contexts)
context.add_command(spawn_context)
context.add_command(export_context)
