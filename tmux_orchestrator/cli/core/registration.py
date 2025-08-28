"""Command registration logic - Set up all CLI command groups."""

import click
from rich.console import Console

from tmux_orchestrator.cli import (
    agent,
    context,
    daemon,
    errors,
    execute,
    monitor,
    orchestrator,
    pm,
    pubsub,
    recovery,
    server,
    session,
    setup_claude,
    spawn,
    tasks,
    team,
    team_compose,
)

from .commands.list_agents import list_agents
from .commands.quick_deploy import quick_deploy_team
from .commands.reflect import reflect_commands
from .commands.status import system_status

# Initialize console for error handling
console = Console()


def register_core_commands(cli_group: click.Group) -> None:
    """Register core CLI commands directly on the main CLI group."""

    # Register list command
    @cli_group.command()
    @click.option("--json", is_flag=True, help="Output in JSON format")
    @click.pass_context
    def list(ctx: click.Context, json: bool) -> None:
        """List all active agents across sessions with comprehensive status."""
        list_agents(ctx, json)

    # Register reflect command
    @cli_group.command()
    @click.option("--format", type=click.Choice(["tree", "json", "markdown"]), default="tree", help="Output format")
    @click.option("--include-hidden", is_flag=True, help="Include hidden commands")
    @click.option("--filter", help="Filter commands by pattern (string or regex)")
    @click.pass_context
    def reflect(ctx: click.Context, format: str, include_hidden: bool, filter: str | None) -> None:
        """Generate complete CLI command structure via runtime introspection."""
        reflect_commands(ctx, format, include_hidden, filter)

    # Register status command
    @cli_group.command()
    @click.option("--json", is_flag=True, help="Output in JSON format")
    @click.pass_context
    def status(ctx: click.Context, json: bool) -> None:
        """Display comprehensive system status dashboard with intelligent caching."""
        system_status(ctx, json)

    # Register quick-deploy command
    @cli_group.command("quick-deploy")
    @click.argument("team_type", type=click.Choice(["frontend", "backend", "fullstack", "testing"]))
    @click.argument("size", type=int, default=3)
    @click.option("--project-name", help="Project name (defaults to current directory)")
    @click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
    @click.pass_context
    def quick_deploy(
        ctx: click.Context, team_type: str, size: int, project_name: str | None, output_json: bool
    ) -> None:
        """Rapidly deploy optimized team configurations for immediate productivity."""
        quick_deploy_team(ctx, team_type, size, project_name, output_json)


def setup_command_groups(cli_group: click.Group) -> None:
    """Set up command groups - called at module load time."""
    try:
        # Import command groups (with error handling for missing modules)

        # Add core command groups
        cli_group.add_command(agent.agent)
        cli_group.add_command(monitor.monitor)
        cli_group.add_command(pm.pm)
        cli_group.add_command(context.context)

        # Add team commands
        try:
            cli_group.add_command(team.team)
        except ImportError:
            # Fallback to team_compose if team.py doesn't exist
            try:
                cli_group.add_command(team_compose.team)
            except ImportError:
                console.print("[yellow]Warning: Team commands not available[/yellow]")

        # Add orchestrator commands (may not exist yet)
        try:
            cli_group.add_command(orchestrator.orchestrator)
        except ImportError:
            pass  # orchestrator.py module will be created in Task 2.4

        # Add setup commands
        try:
            cli_group.add_command(setup_claude.setup)
        except ImportError:
            pass  # setup_claude.py module for environment setup

        # Add spawn command group
        try:
            cli_group.add_command(spawn.spawn)
        except ImportError:
            pass  # spawn.py module for spawning agents

        # Add recovery commands
        try:
            cli_group.add_command(recovery.recovery)
        except ImportError:
            pass  # recovery.py module for automatic agent recovery

        # Add session commands
        try:
            cli_group.add_command(session.session)
        except ImportError:
            pass  # session.py module for session management

        # Add pubsub commands
        try:
            cli_group.add_command(pubsub.pubsub)
        except ImportError:
            pass  # pubsub.py module for agent communication

        # Add daemon management commands
        try:
            cli_group.add_command(daemon.daemon)
        except ImportError:
            pass  # daemon.py module for messaging daemon management

        # Add tasks commands
        try:
            cli_group.add_command(tasks.tasks)
        except ImportError:
            pass  # tasks.py module for task list management

        # Add execute command
        try:
            cli_group.add_command(execute.execute)
        except ImportError:
            pass  # execute.py module for PRD execution

        # Add error management commands
        try:
            cli_group.add_command(errors.errors)
        except ImportError:
            pass  # errors.py module for error management

        # Add MCP server commands
        try:
            cli_group.add_command(server.server)
        except ImportError:
            pass  # server.py module for MCP server management

    except ImportError as e:
        # Handle missing modules gracefully during development
        console.print(f"[yellow]Warning: Some CLI modules not available: {e}[/yellow]")
