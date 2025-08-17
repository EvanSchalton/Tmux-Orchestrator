"""MCP server commands for Claude integration."""

import json
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


@click.group()
def server():
    """MCP server management for Claude integration.

    The MCP (Model Context Protocol) server provides tools for Claude Desktop
    to interact with tmux-orchestrator sessions and agents.

    Examples:
        tmux-orc server start          # Start MCP server for Claude
        tmux-orc server status         # Check registration status
        tmux-orc server tools          # List available MCP tools
        tmux-orc server tools --json   # JSON output for scripts
    """
    pass


@server.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--test", is_flag=True, help="Run in test mode with sample output")
@click.option("--json", "output_json", is_flag=True, help="Output status in JSON format")
def start(verbose: bool, test: bool, output_json: bool):
    """Start MCP server for Claude Desktop integration.

    This command is registered with Claude Desktop and will be
    executed automatically when Claude needs MCP tools.

    Runs in stdio mode: reads from stdin, writes to stdout.

    Examples:
        tmux-orc server start              # Normal operation
        tmux-orc server start --verbose    # Debug logging to stderr
        tmux-orc server start --test       # Test mode for verification
    """
    # Configure logging to stderr only (stdout is for MCP protocol)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    if test:
        # Test mode for verification
        test_response = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "result": {
                "status": "ready",
                "server": "tmux-orchestrator-mcp",
                "version": "1.0.0",
                "tools": ["list", "spawn", "status", "send", "kill"],
                "test_mode": True,
            },
        }

        if output_json:
            print(json.dumps(test_response))
        else:
            click.echo(json.dumps(test_response))
        return

    try:
        # Import here to avoid circular imports
        from tmux_orchestrator.mcp_server import sync_main

        logger.info("Starting MCP server in stdio mode...")

        # Run the server (sync_main handles the asyncio loop)
        sync_main()

    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
        if output_json:
            print(json.dumps({"status": "stopped", "reason": "user_interrupt"}))
    except ImportError as e:
        logger.error(f"Failed to import MCP server: {e}")
        if output_json:
            print(json.dumps({"status": "error", "error": f"Import failed: {e}"}))
        else:
            console.print(f"[red]Error: MCP server module not found: {e}[/red]")
            console.print("[yellow]Ensure tmux-orchestrator is properly installed[/yellow]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"MCP server failed: {e}", exc_info=True)
        if output_json:
            print(json.dumps({"status": "error", "error": str(e)}))
        else:
            console.print(f"[red]Error: MCP server failed: {e}[/red]")
        sys.exit(1)


@server.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def status(output_json: bool):
    """Check MCP server registration status with Claude Desktop.

    Verifies if the MCP server is properly registered in Claude Desktop's
    configuration and shows the current registration details.

    Examples:
        tmux-orc server status         # Human-readable status
        tmux-orc server status --json  # Machine-readable JSON
    """
    try:
        # Check if Claude config exists
        claude_config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

        if not claude_config_path.exists():
            result = {
                "registered": False,
                "config_exists": False,
                "config_path": str(claude_config_path),
                "message": "Claude Desktop configuration not found",
            }

            if output_json:
                console.print(json.dumps(result, indent=2))
            else:
                console.print("[red]❌ Claude Desktop configuration not found[/red]")
                console.print(f"   Expected at: {claude_config_path}")
                console.print("\n[yellow]Make sure Claude Desktop is installed[/yellow]")
            return

        # Read Claude config
        with open(claude_config_path) as f:
            config = json.load(f)

        # Check for MCP server registration
        mcp_servers = config.get("mcpServers", {})
        our_server = mcp_servers.get("tmux-orchestrator")

        if our_server:
            result = {
                "registered": True,
                "config_exists": True,
                "config_path": str(claude_config_path),
                "server_config": our_server,
                "disabled": our_server.get("disabled", False),
                "command": our_server.get("command"),
                "args": our_server.get("args", []),
            }

            if output_json:
                console.print(json.dumps(result, indent=2))
            else:
                console.print("[green]✅ MCP server is registered with Claude Desktop[/green]")
                console.print(f"   Config: {claude_config_path}")
                console.print(f"   Command: {our_server.get('command')} {' '.join(our_server.get('args', []))}")
                if our_server.get("disabled"):
                    console.print("[yellow]   ⚠️  Server is currently DISABLED in Claude[/yellow]")
                else:
                    console.print("[green]   ✓ Server is ENABLED[/green]")
        else:
            result = {
                "registered": False,
                "config_exists": True,
                "config_path": str(claude_config_path),
                "available_servers": list(mcp_servers.keys()),
                "message": "tmux-orchestrator MCP server not registered",
            }

            if output_json:
                console.print(json.dumps(result, indent=2))
            else:
                console.print("[red]❌ MCP server is NOT registered with Claude Desktop[/red]")
                console.print(f"   Config exists at: {claude_config_path}")
                if mcp_servers:
                    console.print(f"   Other servers: {', '.join(mcp_servers.keys())}")
                console.print("\n[yellow]Run 'tmux-orc setup claude' to register the MCP server[/yellow]")

    except json.JSONDecodeError as e:
        error_result = {
            "registered": False,
            "config_exists": True,
            "error": f"Invalid JSON in config: {e}",
            "config_path": str(claude_config_path),
        }

        if output_json:
            console.print(json.dumps(error_result, indent=2))
        else:
            console.print(f"[red]Error: Invalid Claude config JSON: {e}[/red]")
    except Exception as e:
        error_result = {"registered": False, "error": str(e), "error_type": type(e).__name__}

        if output_json:
            console.print(json.dumps(error_result, indent=2))
        else:
            console.print(f"[red]Error checking status: {e}[/red]")


@server.command()
@click.option("--json", "output_json", is_flag=True, help="Output tools in JSON format")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed tool information")
def tools(output_json: bool, verbose: bool):
    """List available MCP tools that Claude can use.

    Shows all CLI commands that are exposed as MCP tools for Claude Desktop
    to interact with tmux-orchestrator sessions and agents.

    Examples:
        tmux-orc server tools              # List tools
        tmux-orc server tools --json       # JSON format
        tmux-orc server tools --verbose    # Detailed info
    """
    try:
        # Quick tool discovery without full server startup
        import subprocess
        import time

        start_time = time.time()

        # Use tmux-orc reflect to get CLI structure
        result = subprocess.run(["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            raise Exception(f"Failed to discover CLI structure: {result.stderr}")

        cli_structure = json.loads(result.stdout)

        # Filter for commands (not groups)
        tools = []
        for cmd_name, cmd_info in cli_structure.items():
            if isinstance(cmd_info, dict) and cmd_info.get("type") == "command":
                tool_info = {
                    "name": f"cli_{cmd_name.replace('-', '_')}",
                    "cli_command": cmd_name,
                    "description": cmd_info.get("short_help", cmd_info.get("help", "No description"))[:100],
                }

                if verbose:
                    tool_info["full_help"] = cmd_info.get("help", "")

                tools.append(tool_info)

        # Sort tools by name
        tools.sort(key=lambda x: x["name"])

        discovery_time = (time.time() - start_time) * 1000

        if output_json:
            result = {
                "tools": tools,
                "total_tools": len(tools),
                "discovery_time_ms": discovery_time,
                "server_type": "cli-reflection",
                "timestamp": time.time(),
            }
            console.print(json.dumps(result, indent=2))
        else:
            console.print("\n[bold]Available MCP Tools for Claude Desktop[/bold]")
            console.print(f"[dim]Discovered {len(tools)} tools in {discovery_time:.1f}ms[/dim]\n")

            if verbose:
                # Detailed view
                for tool in tools:
                    console.print(f"[cyan]{tool['name']}[/cyan]")
                    console.print(f"  CLI: tmux-orc {tool['cli_command']}")
                    console.print(f"  Description: {tool['description']}")
                    if tool.get("full_help"):
                        console.print(f"  [dim]{tool['full_help'][:200]}...[/dim]")
                    console.print()
            else:
                # Table view
                table = Table(title="MCP Tools")
                table.add_column("Tool Name", style="cyan", width=30)
                table.add_column("CLI Command", style="green", width=25)
                table.add_column("Description", style="white", width=50)

                for tool in tools[:20]:  # Show first 20
                    table.add_row(tool["name"], f"tmux-orc {tool['cli_command']}", tool["description"])

                if len(tools) > 20:
                    table.add_row("...", f"... and {len(tools) - 20} more", "Use --verbose to see all tools")

                console.print(table)

            console.print(f"\n[dim]Total tools available: {len(tools)}[/dim]")
            console.print("[dim]These tools are automatically available to Claude when MCP server is running[/dim]")

    except subprocess.TimeoutExpired:
        error_result = {"error": "Tool discovery timed out", "timeout": 10}

        if output_json:
            console.print(json.dumps(error_result, indent=2))
        else:
            console.print("[red]Error: Tool discovery timed out[/red]")
    except Exception as e:
        error_result = {"error": str(e), "error_type": type(e).__name__}

        if output_json:
            console.print(json.dumps(error_result, indent=2))
        else:
            console.print(f"[red]Error discovering tools: {e}[/red]")
            console.print("[yellow]Make sure tmux-orchestrator is properly installed[/yellow]")
