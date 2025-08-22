"""MCP server commands for Claude integration."""

import asyncio
import json
import logging
import sys

import click
from rich.console import Console
from rich.panel import Panel

console = Console()
logger = logging.getLogger(__name__)


@click.group()
def server():
    """MCP server management for Claude integration.

    <mcp>MCP (Model Context Protocol) server management for Claude Code integration. Provides 92 auto-generated tools for agent coordination. Use 'server start' to launch MCP server, 'server status' to check health, 'server validate' to test functionality.</mcp>

    The server command group manages the MCP server that provides Claude agents
    with direct access to tmux-orchestrator functionality through 92 auto-generated
    tools organized hierarchically for optimal agent performance.

    Examples:
        tmux-orc server start        # Start MCP server (for Claude Code CLI)
        tmux-orc server status       # Check MCP server health
        tmux-orc server validate     # Test MCP server functionality
    """
    pass


@server.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--test", is_flag=True, help="Run in test mode with sample output")
def start(verbose, test):
    """Start MCP server for Claude Code CLI integration.

    This command is registered with Claude Code CLI and will be
    executed automatically when Claude needs MCP tools.

    Runs in stdio mode: reads from stdin, writes to stdout.
    """
    # Configure logging to stderr only (stdout is for MCP protocol)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    if test:
        # Test mode for verification
        click.echo('{"status": "ready", "tools": ["list", "spawn", "status"], "mode": "claude_code_cli"}')
        return

    try:
        # Import here to avoid circular imports
        # Set environment to indicate Claude Code CLI mode
        import os

        from tmux_orchestrator.mcp_server import main

        os.environ["TMUX_ORC_MCP_MODE"] = "claude_code"

        # Run the server
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
    except Exception as e:
        logger.error(f"MCP server failed: {e}", exc_info=True)
        sys.exit(1)


@server.command()
def status():
    """Check MCP server registration status with Claude."""
    from tmux_orchestrator.utils.claude_config import get_registration_status

    status_info = get_registration_status()

    console.print("[bold]Claude Desktop MCP Integration Status[/bold]\n")

    # Claude Desktop installation
    if status_info["claude_installed"]:
        console.print("[green]✅ Claude Desktop: Installed[/green]")
        console.print(f"   Config path: {status_info['config_path']}")
    else:
        console.print("[red]❌ Claude Desktop: Not found[/red]")
        console.print("   Install from: https://claude.ai/download")
        return

    # MCP server registration
    if status_info["mcp_registered"]:
        console.print("[green]✅ MCP Server: Registered[/green]")
        details = status_info["server_details"]
        console.print(f"   Command: {details.get('command')} {' '.join(details.get('args', []))}")
        if details.get("disabled"):
            console.print("[yellow]   ⚠️  Server is currently DISABLED in Claude[/yellow]")
        else:
            console.print("   Status: Active")
    else:
        console.print("[red]❌ MCP Server: NOT registered[/red]")
        console.print("   Run 'tmux-orc setup claude-code' to register")

    # Platform info
    console.print(f"\nPlatform: {status_info['platform']}")


@server.command()
@click.option("--json", "json_output", is_flag=True, help="Output tools in JSON format")
def tools(json_output):
    """List available MCP tools that Claude can use."""
    try:
        # Quick tool discovery without full server startup
        from tmux_orchestrator.mcp_fresh import FreshCLIToMCPServer

        server_instance = FreshCLIToMCPServer()
        asyncio.run(server_instance.discover_cli_structure())
        server_instance.generate_all_mcp_tools()

        if json_output:
            tool_list = [
                {"name": name, "description": info["description"], "command": info["command_name"]}
                for name, info in server_instance.generated_tools.items()
            ]
            click.echo(json.dumps(tool_list, indent=2))
        else:
            console.print(f"[bold]Available MCP Tools ({len(server_instance.generated_tools)})[/bold]")
            console.print("=" * 50)

            for tool_name, info in sorted(server_instance.generated_tools.items()):
                cmd_name = info["command_name"]
                desc = info["description"][:60] + "..." if len(info["description"]) > 60 else info["description"]
                console.print(f"{tool_name:20} → tmux-orc {cmd_name}")
                console.print(f"{'':20}   {desc}")

            console.print("=" * 50)
            console.print(f"Total: {len(server_instance.generated_tools)} tools available to Claude")

    except Exception as e:
        console.print(f"[red]Error discovering tools: {e}[/red]")
        sys.exit(1)


@server.command()
def setup():
    """Setup MCP server registration with Claude Desktop.

    This command will:
    1. Detect Claude Desktop installation
    2. Register tmux-orchestrator MCP server
    3. Verify the configuration
    """
    console.print("[blue]Setting up MCP server for Claude Desktop...[/blue]")

    from tmux_orchestrator.utils.claude_config import get_registration_status, register_mcp_server

    # Check current status
    status_info = get_registration_status()

    if not status_info["claude_installed"]:
        console.print("[red]❌ Claude Desktop not found[/red]")
        console.print("Install Claude Desktop from: https://claude.ai/download")
        return

    # Register MCP server
    success, message = register_mcp_server()

    if success:
        console.print(f"[green]✅ {message}[/green]")

        # Show success summary
        summary = """MCP server registration complete!

[bold]What was configured:[/bold]
• Added tmux-orchestrator to Claude Desktop config
• Command: tmux-orc server start
• Environment: TMUX_ORC_MCP_MODE=claude

[bold]Next Steps:[/bold]
1. Restart Claude Desktop to load the MCP server
2. Test with: "List all tmux sessions" in Claude
3. Check status: tmux-orc server status

[bold]Available MCP Tools:[/bold]
• list → Show all active agents
• status → System overview
• quick_deploy → Deploy agent teams
• spawn_orc → Launch orchestrator
• execute → Run PRD with team
• reflect → CLI command discovery"""

        console.print(Panel(summary, title="Setup Complete", style="green"))

    else:
        console.print(f"[red]❌ {message}[/red]")

        # Show manual instructions
        manual_config = f"""You can manually add tmux-orchestrator to Claude Desktop config:

[bold]Config file location:[/bold]
{status_info["config_path"]}

[bold]Add this to mcpServers section:[/bold]
{{
  "tmux-orchestrator": {{
    "command": "tmux-orc",
    "args": ["server", "start"],
    "env": {{
      "TMUX_ORC_MCP_MODE": "claude"
    }},
    "disabled": false
  }}
}}"""

        console.print(Panel(manual_config, title="Manual Setup", style="yellow"))


@server.command()
@click.option("--enable/--disable", default=True, help="Enable or disable MCP server")
def toggle(enable):
    """Enable or disable MCP server in Claude Desktop."""
    from tmux_orchestrator.utils.claude_config import update_mcp_registration

    success = update_mcp_registration(enable)

    if success:
        status = "enabled" if enable else "disabled"
        console.print(f"[green]✅ MCP server {status} in Claude Desktop[/green]")
        console.print("Restart Claude Desktop to apply changes")
    else:
        console.print("[red]❌ Failed to update MCP server configuration[/red]")
        console.print("Check that Claude Desktop is installed and tmux-orchestrator is registered")


# Export for CLI registration
__all__ = ["server"]
