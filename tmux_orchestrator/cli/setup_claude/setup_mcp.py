"""Register MCP server with Claude Desktop."""

import json
import platform

from rich.console import Console

console = Console()


def setup_mcp(force: bool) -> None:
    """Register MCP server with Claude Desktop.

    This command specifically handles MCP server registration without
    running the full Claude Code setup. Useful for:
    - Re-registering after Claude Desktop updates
    - Fixing registration issues
    - Checking registration status

    Examples:
        tmux-orc setup mcp          # Register MCP server
        tmux-orc setup mcp --force  # Force re-registration
    """
    from tmux_orchestrator.utils.claude_config import (
        check_claude_installation,
        get_registration_status,
        register_mcp_server,
    )

    console.print("[bold]MCP Server Registration for Claude Desktop[/bold]\n")

    # Check current status
    status = get_registration_status()

    if status["mcp_registered"] and not force:
        console.print("[green]✓ MCP server is already registered with Claude Desktop[/green]")
        console.print(f"   Config: {status['config_path']}")
        console.print(f"   Status: {'Enabled' if not status['server_details'].get('disabled') else 'Disabled'}")
        console.print("\nTo check server status: [cyan]tmux-orc server status[/cyan]")
        console.print("To test the server: [cyan]tmux-orc server start --test[/cyan]")
        return

    # Check if Claude is installed
    is_installed, config_path = check_claude_installation()

    if not is_installed:
        console.print("[red]❌ Claude Desktop not found[/red]")
        console.print("\nClaude Desktop must be installed first:")
        console.print("Download from: [cyan]https://claude.ai/download[/cyan]")

        # Platform-specific guidance
        system = platform.system()
        if system == "Darwin":
            console.print("\nExpected location: ~/Library/Application Support/Claude/")
        elif system == "Windows":
            console.print("\nExpected location: %APPDATA%\\Claude\\")
        else:
            console.print("\nExpected location: ~/.config/Claude/")
        return

    # Attempt registration
    console.print("[blue]Registering MCP server with Claude Desktop...[/blue]")
    success, message = register_mcp_server()

    if success:
        console.print(f"[green]✅ {message}[/green]")
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("1. Restart Claude Desktop to load the MCP server")
        console.print("2. Test with 'List tmux sessions' in Claude")
        console.print("3. Check status: [cyan]tmux-orc server status[/cyan]")
    else:
        console.print(f"[red]❌ {message}[/red]")
        console.print("\n[yellow]Manual registration required:[/yellow]")
        console.print(f"1. Edit Claude config: {config_path}")
        console.print("2. Add to 'mcpServers' section:")
        console.print(
            json.dumps(
                {
                    "tmux-orchestrator": {
                        "command": "tmux-orc",
                        "args": ["server", "start"],
                        "env": {"TMUX_ORC_MCP_MODE": "claude"},
                        "disabled": False,
                    }
                },
                indent=2,
            )
        )
        console.print("3. Save and restart Claude Desktop")
