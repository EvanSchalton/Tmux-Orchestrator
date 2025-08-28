"""Main CLI group definition and context setup."""

from pathlib import Path

import click
from rich.console import Console

from tmux_orchestrator import __version__
from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

# Initialize console for CLI output
console: Console = Console()


@click.group(name="tmux-orc")
@click.version_option(version=__version__, prog_name="tmux-orc")
@click.option(
    "--config-file",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
    envvar="TMUX_ORC_CONFIG",
)
@click.option("--json", is_flag=True, help="Output in JSON format for scripting")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, config_file: str | None, json: bool, verbose: bool) -> None:
    """TMUX Orchestrator - AI-powered tmux session management.

    The TMUX Orchestrator enables autonomous AI agents to collaborate in tmux sessions,
    providing intelligent session management, automatic recovery, and seamless monitoring.

    Examples:
        tmux-orc team deploy frontend 3          # Deploy 3-agent frontend team
        tmux-orc agent restart session:0         # Restart specific agent
        tmux-orc monitor start --interval 15     # Start monitoring daemon
        tmux-orc setup vscode ./my-project       # Setup VS Code integration

    For detailed command help, use: tmux-orc COMMAND --help
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Initialize configuration
    try:
        ctx.obj["config"] = Config.load(Path(config_file) if config_file else None)
    except Exception as e:
        if verbose:
            console.print(f"[red]Configuration error: {e}[/red]")
        ctx.obj["config"] = Config()  # Use defaults

    # Initialize TMUX manager (now using high-performance implementation)
    ctx.obj["tmux"] = TMUXManager()
    ctx.obj["tmux_optimized"] = TMUXManager()  # Both point to same optimized version
    ctx.obj["console"] = console
    ctx.obj["json_mode"] = json
    ctx.obj["verbose"] = verbose


# Register commands after CLI is defined
def _setup_commands() -> None:
    """Set up all CLI commands."""
    from .registration import register_core_commands, setup_command_groups

    # Register core commands directly on the CLI group
    register_core_commands(cli)

    # Register command groups from other modules
    setup_command_groups(cli)


# Set up commands when module is imported
_setup_commands()
