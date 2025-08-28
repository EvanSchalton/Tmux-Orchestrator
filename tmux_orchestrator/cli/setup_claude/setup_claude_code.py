"""Install slash commands and MCP server for Claude Code."""

import importlib.resources
import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

try:
    import pkg_resources  # type: ignore[import-untyped]
except ImportError:
    pkg_resources = None  # type: ignore[assignment]

from .detect_claude_environment import detect_claude_environment
from .detect_claude_executable import detect_claude_executable
from .register_mcp_with_claude_cli import register_mcp_with_claude_cli
from .restart_claude_if_running import restart_claude_if_running

console = Console()


def setup_claude_code(root_dir: str | None, force: bool, non_interactive: bool) -> None:
    """Install slash commands and MCP server for Claude Code.

    Sets up complete Claude Code integration including:
    - Slash commands for PRD creation and task management
    - MCP server configuration for agent control
    - Auto-restart of Claude Code if needed

    Examples:
        tmux-orc setup claude-code
        tmux-orc setup claude-code --force
        tmux-orc setup claude-code --root-dir /workspaces/myproject
    """
    # Determine Claude directory location
    if root_dir is None:
        # Check for existing directories
        project_claude = Path.cwd() / ".claude"
        home_claude = Path.home() / ".claude"

        # Determine default based on what exists
        default_choice = 1  # Default to project directory
        existing_locations = []

        if project_claude.exists():
            existing_locations.append(f"Project: {project_claude}")
            default_choice = 1
        if home_claude.exists():
            existing_locations.append(f"Home: {home_claude}")
            if not project_claude.exists():
                default_choice = 2

        # Show current state
        if existing_locations:
            console.print("[yellow]Found existing Claude directories:[/yellow]")
            for loc in existing_locations:
                console.print(f"  • {loc}")
        else:
            console.print("[yellow]No existing Claude directories found.[/yellow]")

        # Ask for user preference unless non-interactive
        if non_interactive:
            # Use default choice without prompting
            if default_choice == 2:
                claude_path = home_claude
            else:
                claude_path = project_claude
            console.print(f"[green]Using default Claude directory: {claude_path}[/green]")
        else:
            # Determine the default path based on what exists
            if default_choice == 2:
                default_path = str(home_claude)
            else:
                default_path = str(project_claude)

            console.print("\n[yellow]Enter Claude configuration directory:[/yellow]")
            console.print(f"[dim](Press Enter to use: {default_path})[/dim]")

            user_input = click.prompt(
                "Path",
                default=default_path,
                show_default=False,  # We're showing it above in a nicer format
                type=click.Path(resolve_path=True),
            )

            if user_input.lower() in ["cancel", "quit", "exit", "q"]:
                console.print("[yellow]Setup cancelled.[/yellow]")
                return

            # Handle the path - if user already included .claude, don't add it again
            user_path = Path(user_input)
            if user_path.name == ".claude":
                claude_path = user_path
            else:
                claude_path = user_path / ".claude"
            console.print(f"\n[green]Using Claude directory: {claude_path}[/green]")
    else:
        # Use provided root directory
        claude_path = Path(root_dir) / ".claude"
        console.print(f"[green]Using specified root directory: {claude_path}[/green]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Task 1: Check/Create Claude Code directory
        task = progress.add_task("Setting up Claude Code directory...", total=5)

        # Ensure directory exists (especially for devcontainers)
        if not claude_path.exists():
            claude_path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]✓ Created Claude directory: {claude_path}[/green]")

        progress.update(task, advance=1)

        # Task 2: Install slash commands
        progress.update(task, description="Installing slash commands...")

        commands_dir = claude_path / "commands"
        commands_dir.mkdir(exist_ok=True)

        # Install slash commands from package data
        commands_installed = 0
        try:
            # For Python 3.11+, use files() API
            if hasattr(importlib.resources, "files"):
                command_files = importlib.resources.files("tmux_orchestrator.claude_commands")
                # Get all .md files in the package
                command_list = [f for f in command_files.iterdir() if f.name.endswith(".md")]
                console.print(f"[dim]Installing {len(command_list)} slash commands[/dim]")

                # Copy each command file
                for cmd_file in command_list:
                    dest_file = commands_dir / cmd_file.name
                    if force or not dest_file.exists():
                        content = cmd_file.read_text()
                        dest_file.write_text(content)
                        commands_installed += 1
            else:
                # Fallback for older Python versions
                if pkg_resources is None:
                    console.print("[red]Error: pkg_resources not available for Python < 3.11[/red]")
                    return
                command_names = []
                for resource in pkg_resources.resource_listdir("tmux_orchestrator", "claude_commands"):
                    if resource.endswith(".md"):
                        command_names.append(resource)

                console.print(f"[dim]Installing {len(command_names)} slash commands[/dim]")

                # Copy each command file
                for cmd_name in command_names:
                    dest_file = commands_dir / cmd_name
                    if force or not dest_file.exists():
                        content = pkg_resources.resource_string("tmux_orchestrator.claude_commands", cmd_name).decode(
                            "utf-8"
                        )
                        dest_file.write_text(content)
                        commands_installed += 1

        except Exception as e:
            console.print(f"[red]Error installing slash commands: {e}[/red]")
            console.print("[yellow]Commands may not be available[/yellow]")

        console.print(f"[green]✓ Installed {commands_installed} slash commands[/green]")

        progress.update(task, advance=1)

        # Task 3: Configure MCP server (CLI-first approach)
        progress.update(task, description="Configuring MCP server...")

        # Detect available Claude environments
        claude_env = detect_claude_environment()

        if claude_env["cli_available"]:
            # Priority 1: Claude Code CLI
            console.print("[green]✓ Found Claude Code CLI[/green]")
            success, message = register_mcp_with_claude_cli()
            if success:
                console.print(f"[green]✓ {message}[/green]")
                console.print("[dim]   Project-scoped MCP server now available[/dim]")
            else:
                console.print(f"[yellow]⚠ CLI registration failed: {message}[/yellow]")
                console.print("[yellow]   Will create local config as fallback[/yellow]")

        elif claude_env["desktop_available"]:
            # Priority 2: Claude Desktop (existing logic)
            from tmux_orchestrator.utils.claude_config import (
                check_claude_installation,
                get_registration_status,
                register_mcp_server,
            )

            is_installed, config_path = check_claude_installation()
            console.print(f"[green]✓ Found Claude Desktop config: {config_path}[/green]")

            # Attempt registration
            success, message = register_mcp_server()
            if success:
                console.print(f"[green]✓ {message}[/green]")

                # Show status after registration
                status = get_registration_status()
                if status["mcp_registered"]:
                    console.print("[green]✓ MCP server successfully registered with Claude Desktop[/green]")
                    console.print("[dim]   Restart Claude Desktop to activate the MCP server[/dim]")
            else:
                console.print(f"[yellow]⚠ {message}[/yellow]")
                console.print("[yellow]   Will create local MCP config as fallback[/yellow]")

        else:
            # Priority 3: Create local configs for future use
            console.print("[yellow]⚠ No Claude environment detected[/yellow]")
            console.print("[dim]   Creating local MCP configs for future use...[/dim]")

        # Always create local MCP configs for reference/fallback
        # Create Claude Desktop format config
        mcp_config_path = claude_path / "config" / "mcp.json"
        mcp_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        if mcp_config_path.exists() and not force:
            with open(mcp_config_path) as f:
                mcp_config = json.load(f)
        else:
            mcp_config = {"servers": {}}

        # Add tmux-orchestrator server with enhanced config
        mcp_config["servers"]["tmux-orchestrator"] = {
            "command": "tmux-orc",
            "args": ["server", "start"],
            "env": {
                "TMUX_ORC_MCP_MODE": "claude",
                "PYTHONUNBUFFERED": "1",  # Ensure real-time output
            },
            "disabled": False,
            "description": "AI-powered tmux session orchestrator",
        }

        # Write config with proper formatting
        with open(mcp_config_path, "w") as f:
            json.dump(mcp_config, f, indent=2)

        console.print(f"[green]✓ Created local MCP config: {mcp_config_path}[/green]")

        # Create Claude Code CLI format config (.mcp.json in project root)
        project_mcp_path = Path.cwd() / ".mcp.json"
        cli_mcp_config = {
            "mcpServers": {
                "tmux-orchestrator": {
                    "type": "stdio",
                    "command": "tmux-orc",
                    "args": ["server", "start"],
                    "env": {"TMUX_ORC_MCP_MODE": "claude", "PYTHONUNBUFFERED": "1"},
                }
            }
        }

        with open(project_mcp_path, "w") as f:
            json.dump(cli_mcp_config, f, indent=2)

        console.print(f"[green]✓ Created CLI MCP config: {project_mcp_path}[/green]")

        progress.update(task, advance=1)

        # Task 4: Create CLAUDE.md in .claude directory
        progress.update(task, description="Creating Claude instructions...")

        claude_md_path = claude_path / "CLAUDE.md"
        if not claude_md_path.exists() or force:
            claude_content = """# Claude Code Instructions for This Project

## Tmux Orchestrator Integration

This project has Tmux Orchestrator installed for managing AI agent teams.

### Quick Start Commands

1. **Create PRD from description**:
   ```
   /create-prd project_description.md
   ```

2. **Generate tasks from PRD**:
   ```
   /generate-tasks
   ```

3. **Execute PRD with agent team**:
   - Via MCP: "Execute the PRD at ./prd.md"
   - Via CLI: `tmux-orc execute ./prd.md`

### Monitoring Agents

- View all agents: `tmux-orc list`
- Check team status: `tmux-orc team status <session>`
- View agent output: `tmux-orc read --session <session:window>`

### Task Management

All tasks are organized in `.tmux_orchestrator/projects/`:
- Master task list: `tasks.md`
- Agent tasks: `agents/{agent}-tasks.md`
- Status tracking: `status/summary.md`

### Available Slash Commands

- `/create-prd` - Generate PRD from feature description
- `/generate-tasks` - Create task list from PRD
- `/process-task-list` - Execute tasks systematically

## Project-Specific Instructions

[Add your project-specific Claude instructions here]
"""
            claude_md_path.write_text(claude_content)
            console.print(f"[green]✓ Created CLAUDE.md in {claude_path}[/green]")
        else:
            console.print("[yellow]⚠ CLAUDE.md already exists (use --force to overwrite)[/yellow]")

        progress.update(task, advance=1)

        # Task 5: Detect and handle Claude Code
        progress.update(task, description="Checking Claude Code installation...")

        claude_exe = detect_claude_executable()
        claude_detected = claude_exe is not None
        claude_restarted = False

        if claude_detected:
            console.print(f"[green]✓ Found Claude Code: {claude_exe}[/green]")

            # Offer to restart Claude to load new configuration
            if not non_interactive:
                should_restart = Confirm.ask("Restart Claude Code to load new configuration?", default=True)
                if should_restart:
                    claude_restarted = restart_claude_if_running()
                    if claude_restarted:
                        console.print("[green]✓ Claude Code will reload with new config[/green]")
        else:
            console.print("[yellow]⚠ Claude Code executable not found[/yellow]")
            console.print("[dim]You may need to restart Claude Code manually to load configuration[/dim]")

        progress.update(task, description="Setup complete!", advance=1)

    # Display summary
    claude_status = ""
    if claude_detected:
        if claude_restarted:
            claude_status = f"• Claude Code: {claude_exe} (restarted)"
        else:
            claude_status = f"• Claude Code: {claude_exe} (restart manually)"
    else:
        claude_status = "• Claude Code: Not detected (install and restart manually)"

    summary = f"""Claude Code integration complete!

[bold]Installed Components:[/bold]
• Slash commands in: {commands_dir}
• MCP server config: {mcp_config_path}
• Claude instructions: {claude_md_path if claude_md_path.exists() else "Not created"}
{claude_status}

[bold]Next Steps:[/bold]
1. {"Claude Code should reload automatically" if claude_restarted else "Restart Claude Code to load slash commands"}
2. Test with: /create-prd
3. Monitor MCP server: tmux-orc server status

[bold]Quick Test:[/bold]
In Claude Code, try: "List all tmux sessions"
This should use the MCP server to show active sessions."""

    console.print(Panel(summary, title="Setup Complete", style="green"))
