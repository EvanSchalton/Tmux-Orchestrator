"""Run all setup commands for complete environment configuration."""

import click
from rich.console import Console

from .setup_claude_code import setup_claude_code
from .setup_tmux import setup_tmux
from .setup_vscode import setup_vscode

console = Console()


def setup_all(force: bool) -> None:
    """Run all setup commands for complete environment configuration.

    Configures:
    - Claude Code integration (slash commands + MCP)
    - MCP server for agent coordination
    - VS Code tasks and settings
    - Tmux configuration with mouse support
    - Git hooks for quality checks
    - Shell completions

    Examples:
        tmux-orc setup all
        tmux-orc setup all --force
    """
    console.print("[bold blue]Running complete environment setup...[/bold blue]\n")

    # Setup Claude Code
    console.print("[cyan]1. Setting up Claude Code...[/cyan]")
    setup_claude_code(root_dir=None, force=force, non_interactive=False)

    # Setup VS Code
    console.print("\n[cyan]2. Setting up VS Code...[/cyan]")
    setup_vscode(project_dir=".", force=force)

    # Setup Tmux
    console.print("\n[cyan]3. Setting up Tmux configuration...[/cyan]")
    setup_tmux(force=force)

    # Setup MCP Server
    console.print("\n[cyan]4. Setting up MCP server...[/cyan]")
    try:
        # Import the server command group to get the setup command
        from tmux_orchestrator.cli.server import server

        ctx = click.get_current_context()
        # Get the setup command from the server group
        setup_mcp_server = server.commands.get("setup")
        if setup_mcp_server:
            ctx.invoke(setup_mcp_server)
        else:
            console.print("[yellow]⚠ MCP server setup command not found[/yellow]")
    except Exception as e:
        console.print(f"[yellow]⚠ MCP server setup failed: {e}[/yellow]")

    console.print("\n[bold green]✓ All setup tasks complete![/bold green]")
    console.print("\nYou can now:")
    console.print("1. Use slash commands in Claude Code")
    console.print("2. Run VS Code tasks for agent management")
    console.print("3. Click tmux windows with mouse support enabled")
    console.print("4. Execute PRDs with: tmux-orc execute <prd-file>")
    console.print("5. Access MCP server API at: http://127.0.0.1:8000/docs")
