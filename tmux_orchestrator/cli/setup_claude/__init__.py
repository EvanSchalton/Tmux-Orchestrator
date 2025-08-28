"""Setup commands for Claude Code integration."""


import click
from rich.console import Console

from .check_requirements import check_requirements
from .check_setup import check_setup
from .detect_claude_environment import detect_claude_environment
from .detect_claude_executable import detect_claude_executable
from .register_mcp_with_claude_cli import register_mcp_with_claude_cli
from .restart_claude_if_running import restart_claude_if_running
from .setup_all import setup_all
from .setup_claude_code import setup_claude_code
from .setup_mcp import setup_mcp
from .setup_tmux import setup_tmux
from .setup_vscode import setup_vscode

console = Console()

# Re-export functions for backwards compatibility
__all__ = [
    "detect_claude_executable",
    "detect_claude_environment",
    "restart_claude_if_running",
    "register_mcp_with_claude_cli",
    "setup_mcp",
    "check_requirements",
    "setup",  # Main CLI group
]


@click.group(invoke_without_command=True)
@click.pass_context
def setup(ctx: click.Context) -> None:
    """Check system requirements and setup Claude integrations.

    Automatically detects your development environment and provides
    guidance for setting up tmux-orchestrator with Claude Desktop,
    Claude Code, VS Code, and tmux configurations.

    Examples:
        tmux-orc setup              # Check system requirements
        tmux-orc setup claude-code  # Setup Claude Code integration
        tmux-orc setup vscode       # Setup VS Code integration
        tmux-orc setup tmux         # Setup tmux configuration
        tmux-orc setup all          # Run all setup steps
    """
    if ctx.invoked_subcommand is None:
        check_requirements()


@setup.command(name="mcp")
@click.option("--force", is_flag=True, help="Force re-registration even if already registered")
def mcp_command(force: bool) -> None:
    """Register MCP server with Claude Desktop."""
    setup_mcp(force)


@setup.command(name="check-requirements")
def check_requirements_command() -> None:
    """Check system requirements for tmux-orchestrator."""
    check_requirements()


@setup.command(name="claude-code")
@click.option(
    "--root-dir",
    help="Root directory for Claude Code config (defaults to auto-detection)",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=None,
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.option("--non-interactive", is_flag=True, help="Use defaults without prompting")
def setup_claude_code_command(root_dir: str | None, force: bool, non_interactive: bool) -> None:
    """Install slash commands and MCP server for Claude Code."""

    setup_claude_code(root_dir, force, non_interactive)


@setup.command(name="vscode")
@click.argument("project_dir", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
def setup_vscode_command(project_dir: str, force: bool) -> None:
    """Set up VS Code configuration."""

    setup_vscode(project_dir, force)


@setup.command(name="tmux")
@click.option("--force", is_flag=True, help="Overwrite existing tmux configuration")
def setup_tmux_command(force: bool) -> None:
    """Set up tmux configuration."""

    setup_tmux(force)


@setup.command(name="all")
@click.option("--force", is_flag=True, help="Overwrite existing configurations")
def setup_all_command(force: bool) -> None:
    """Run all setup commands."""

    setup_all(force)


@setup.command(name="check-setup")
def check_setup_command() -> None:
    """Check and validate current setup configuration."""

    check_setup()
