"""MCP server management commands."""

import os
import subprocess
import time
from pathlib import Path
from typing import Any

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
        process = subprocess.Popen(
            ["python", "-m", "tmux_orchestrator.server"],
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
            subprocess.run(
                ["python", "-m", "tmux_orchestrator.server"],
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


@server.command()
def setup() -> None:
    """Setup MCP server configuration for Claude Desktop.

    This command will:
    1. Create MCP server configuration
    2. Add it to Claude Desktop's config
    3. Start the server if not running
    """
    console.print("[blue]Setting up MCP server for Claude Desktop...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Check Claude Desktop config
        task = progress.add_task("Checking Claude Desktop configuration...", total=4)

        claude_config_dir = Path.home() / "Library" / "Application Support" / "Claude"
        if not claude_config_dir.exists():
            claude_config_dir = Path.home() / ".config" / "claude"  # Linux fallback

        claude_config_file = claude_config_dir / "claude_desktop_config.json"

        if not claude_config_file.exists():
            console.print("[yellow]⚠ Claude Desktop config not found. Creating default config...[/yellow]")
            claude_config_dir.mkdir(parents=True, exist_ok=True)
            claude_config: dict[str, Any] = {"mcpServers": {}}
        else:
            import json

            claude_config = json.loads(claude_config_file.read_text())
            if "mcpServers" not in claude_config:
                claude_config["mcpServers"] = {}

        progress.update(task, advance=1)

        # Step 2: Add MCP server configuration
        progress.update(task, description="Adding MCP server to Claude config...")

        claude_config["mcpServers"]["tmux-orchestrator"] = {
            "command": "python",
            "args": ["-m", "tmux_orchestrator.server"],
            "env": {"TMUX_ORC_SERVER_HOST": "127.0.0.1", "TMUX_ORC_SERVER_PORT": "8000"},
        }

        # Save updated config
        import json

        claude_config_file.write_text(json.dumps(claude_config, indent=2))

        progress.update(task, advance=1)

        # Step 3: Start server if not running
        progress.update(task, description="Starting MCP server...")

        try:
            import requests  # type: ignore[import-untyped]

            response = requests.get("http://127.0.0.1:8000/health", timeout=2)
            if response.status_code == 200:
                console.print("[green]✓ MCP server already running[/green]")
            else:
                raise requests.exceptions.RequestException()
        except requests.exceptions.RequestException:
            # Start server in background
            subprocess.Popen(
                ["python", "-m", "tmux_orchestrator.server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(3)

        progress.update(task, advance=1)

        # Step 4: Verify setup
        progress.update(task, description="Verifying setup...")

        try:
            import requests  # type: ignore[import-untyped]

            response = requests.get("http://127.0.0.1:8000/health", timeout=2)
            if response.status_code == 200:
                progress.update(task, advance=1)
            else:
                raise Exception("Server not responding")
        except Exception as e:
            console.print(f"[red]✗ Setup failed: {e}[/red]")
            return

    # Success message
    console.print(
        Panel(
            "[green]✓ MCP server setup complete![/green]\n\n"
            "The server is now available to Claude Desktop.\n"
            "You may need to restart Claude Desktop for changes to take effect.\n\n"
            "[bold]Server endpoints:[/bold]\n"
            "• Health: http://127.0.0.1:8000/health\n"
            "• API Docs: http://127.0.0.1:8000/docs\n"
            "• OpenAPI: http://127.0.0.1:8000/openapi.json\n\n"
            "[bold]Available tools:[/bold]\n"
            "• spawn_agent, restart_agent, kill_agent\n"
            "• send_message, broadcast_message\n"
            "• deploy_team, coordinate_standup\n"
            "• create_task, track_task_status\n"
            "• And many more...",
            title="MCP Server Setup Complete",
            style="green",
        )
    )


# Export for CLI registration
__all__ = ["server"]
