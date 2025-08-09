"""MCP server management commands."""

import os
import subprocess
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@click.group()
def server() -> None:
    """Manage the MCP (Model Context Protocol) server."""
    pass


@server.command()
@click.option("--host", default="127.0.0.1", help="Host to bind the server to")
@click.option("--port", default=8000, help="Port to bind the server to")
@click.option("--background", is_flag=True, help="Run server in background")
def start(host: str, port: int, background: bool) -> None:
    """Start the MCP server for agent coordination.

    The MCP server provides:
    - RESTful API for agent management
    - Real-time agent coordination
    - Task assignment and tracking
    - Team deployment capabilities
    - Health monitoring endpoints

    Examples:
        tmux-orc server start
        tmux-orc server start --port 8080
        tmux-orc server start --background
    """
    console.print(f"[blue]Starting MCP server on {host}:{port}...[/blue]")

    if background:
        # Run in background using subprocess
        # Try the console script first, fall back to module if not found
        try:
            process = subprocess.Popen(
                ["tmux-orc-server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "TMUX_ORC_SERVER_HOST": host, "TMUX_ORC_SERVER_PORT": str(port)},
            )
        except FileNotFoundError:
            # Fall back to running as module
            process = subprocess.Popen(
                [sys.executable, "-m", "tmux_orchestrator.server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "TMUX_ORC_SERVER_HOST": host, "TMUX_ORC_SERVER_PORT": str(port)},
            )

        # Wait a moment to check if it started
        time.sleep(2)

        if process.poll() is None:
            console.print(f"[green]✓ MCP server started in background (PID: {process.pid})[/green]")
            console.print(f"[dim]API docs available at: http://{host}:{port}/docs[/dim]")

            # Save PID for later
            pid_file = Path.home() / ".tmux_orchestrator" / "mcp_server.pid"
            pid_file.parent.mkdir(exist_ok=True)
            pid_file.write_text(str(process.pid))
        else:
            console.print("[red]✗ Failed to start MCP server[/red]")
    else:
        # Run in foreground
        console.print("[green]✓ Starting MCP server...[/green]")
        console.print(f"[dim]API docs will be available at: http://{host}:{port}/docs[/dim]")
        console.print("[yellow]Press Ctrl+C to stop the server[/yellow]\n")

        try:
            # Try console script first
            try:
                subprocess.run(
                    ["tmux-orc-server"],
                    env={**os.environ, "TMUX_ORC_SERVER_HOST": host, "TMUX_ORC_SERVER_PORT": str(port)},
                )
            except FileNotFoundError:
                # Fall back to module
                subprocess.run(
                    [sys.executable, "-m", "tmux_orchestrator.server"],
                    env={**os.environ, "TMUX_ORC_SERVER_HOST": host, "TMUX_ORC_SERVER_PORT": str(port)},
                )
        except KeyboardInterrupt:
            console.print("\n[yellow]Server stopped[/yellow]")


@server.command()
def stop() -> None:
    """Stop the MCP server running in background."""
    pid_file = Path.home() / ".tmux_orchestrator" / "mcp_server.pid"

    if not pid_file.exists():
        console.print("[yellow]No MCP server PID file found[/yellow]")
        return

    try:
        pid = int(pid_file.read_text().strip())
        subprocess.run(["kill", str(pid)], check=True)
        pid_file.unlink()
        console.print("[green]✓ MCP server stopped[/green]")
    except (ValueError, subprocess.CalledProcessError):
        console.print("[red]✗ Failed to stop MCP server[/red]")
        if pid_file.exists():
            pid_file.unlink()


@server.command()
def status() -> None:
    """Check MCP server status."""
    import requests  # type: ignore[import-untyped]

    # Check if background process is running
    pid_file = Path.home() / ".tmux_orchestrator" / "mcp_server.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            # Check if process is still running
            subprocess.run(["kill", "-0", str(pid)], check=True, capture_output=True)
            console.print(f"[green]✓ MCP server is running (PID: {pid})[/green]")
        except (ValueError, subprocess.CalledProcessError):
            console.print("[yellow]⚠ PID file exists but server is not running[/yellow]")
            pid_file.unlink()

    # Try to connect to the server
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=2)
        if response.status_code == 200:
            console.print("[green]✓ MCP server is responding on port 8000[/green]")
            console.print("[dim]API docs: http://127.0.0.1:8000/docs[/dim]")
        else:
            console.print("[yellow]⚠ MCP server returned unexpected status[/yellow]")
    except requests.exceptions.RequestException:
        console.print("[red]✗ Cannot connect to MCP server on port 8000[/red]")


@server.command(name="mcp-serve")
def mcp_serve() -> None:
    """Run the MCP server in stdio mode for Claude Code.

    This command starts the MCP server using stdio transport,
    which Claude Code can use directly via the 'tmux-orc server mcp-serve' command.

    This is the preferred way to use tmux-orchestrator with Claude Code.
    """
    import asyncio

    from tmux_orchestrator.mcp_server import main

    # Run the MCP server
    asyncio.run(main())


@server.command()
def setup() -> None:
    """Setup MCP server configuration for Claude Code.

    This command will:
    1. Configure Claude Code to use the stdio MCP server
    2. Verify the configuration
    """
    console.print("[blue]Setting up MCP server for Claude Code...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Check if tmux-orc command is available
        task = progress.add_task("Checking tmux-orc installation...", total=3)

        try:
            result = subprocess.run(["tmux-orc", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                console.print("[red]✗ tmux-orc command not found[/red]")
                console.print("[yellow]Make sure tmux-orchestrator is installed correctly[/yellow]")
                return
            console.print("[green]✓ tmux-orc command is available[/green]")
        except FileNotFoundError:
            console.print("[red]✗ tmux-orc command not found[/red]")
            console.print("[yellow]Make sure tmux-orchestrator is installed correctly[/yellow]")
            return

        progress.update(task, advance=1)

        # Step 2: Add MCP server to Claude Code
        progress.update(task, description="Configuring Claude Code...")

        # Check if already added
        try:
            result = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True, check=True)
            if "tmux-orchestrator" in result.stdout:
                console.print("[yellow]⚠ tmux-orchestrator already configured in Claude Code[/yellow]")
                # Remove existing to update it
                subprocess.run(["claude", "mcp", "remove", "tmux-orchestrator"], capture_output=True, check=False)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # Claude CLI might not be installed or no servers configured

        # Add the MCP server using stdio transport
        try:
            result = subprocess.run(
                ["claude", "mcp", "add", "tmux-orchestrator", "tmux-orc", "server", "mcp-serve"],
                capture_output=True,
                text=True,
                check=True,
            )
            if result.returncode == 0:
                console.print("[green]✓ Added tmux-orchestrator to Claude Code[/green]")
            else:
                raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
        except FileNotFoundError:
            console.print("[red]✗ Claude CLI not found. Is Claude Code installed?[/red]")
            console.print("[yellow]Install Claude Code from: https://claude.ai/download[/yellow]")
            return
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Failed to add MCP server to Claude Code: {e.stderr or e.stdout}[/red]")
            return

        progress.update(task, advance=1)

        # Step 3: Verify setup
        progress.update(task, description="Verifying setup...")

        try:
            # Verify Claude Code configuration
            result = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True, check=True)
            if "tmux-orchestrator" in result.stdout:
                console.print("[green]✓ tmux-orchestrator is configured in Claude Code[/green]")
            else:
                console.print("[yellow]⚠ tmux-orchestrator may not be properly configured[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not verify setup: {e}[/yellow]")

        progress.update(task, advance=1)

    # Success message
    console.print(
        Panel(
            "[green]✓ MCP server setup complete![/green]\n\n"
            "The tmux-orchestrator MCP server is now available to Claude Code.\n"
            "You may need to restart Claude Code or run /mcp to see the tools.\n\n"
            "[bold]Available MCP tools:[/bold]\n"
            "• list_agents - List all active tmux sessions\n"
            "• spawn_agent - Create new Claude agents\n"
            "• send_message - Send messages to agents\n"
            "• restart_agent - Restart agents\n"
            "• deploy_team - Deploy agent teams\n"
            "• get_agent_status - Check agent status\n\n"
            "[bold]Usage in Claude Code:[/bold]\n"
            "• Run /mcp to see available tools\n"
            "• Tools will appear with 'tmux-orchestrator' prefix\n\n"
            "[bold]Manual testing:[/bold]\n"
            "You can test the MCP server directly:\n"
            "tmux-orc server mcp-serve",
            title="MCP Server Setup Complete",
            style="green",
        )
    )


# Export for CLI registration
__all__ = ["server"]
