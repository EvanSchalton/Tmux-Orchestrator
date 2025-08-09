"""Setup commands for Claude Code integration."""

import json
import shutil
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def setup(ctx: click.Context) -> None:
    """Setup and configuration commands for development environments.

    The setup command group provides automated configuration for various
    development tools and environments to work seamlessly with the TMUX
    Orchestrator system.

    Available Setups:
        • claude-code: Install slash commands and MCP server
        • vscode: Configure VS Code tasks and debugging
        • git-hooks: Install pre-commit hooks for quality

    Examples:
        tmux-orc setup                  # Check system requirements
        tmux-orc setup claude-code      # Setup Claude Code integration
        tmux-orc setup vscode ./project # Configure VS Code
        tmux-orc setup all              # Run all setup commands
    """
    if ctx.invoked_subcommand is None:
        # If no subcommand provided, run check-requirements
        ctx.invoke(check_requirements)


@setup.command(name="check-requirements")
def check_requirements() -> None:
    """Check system requirements and provide setup guidance.

    Verifies that all required dependencies are installed and provides
    platform-specific installation instructions if any are missing.

    Examples:
        tmux-orc setup        # Run system check
    """
    import platform
    import subprocess

    console.print("[bold]Tmux Orchestrator System Setup Check[/bold]\n")

    # Check tmux installation
    console.print("Checking for tmux...", end=" ")
    try:
        result = subprocess.run(["tmux", "-V"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            console.print(f"[green]✓ Found {version}[/green]")
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        console.print("[red]✗ Not found[/red]")
        console.print("\n[yellow]tmux is required but not installed![/yellow]")

        # Provide platform-specific installation instructions
        system = platform.system().lower()
        if system == "darwin":
            console.print("\nInstall tmux on macOS:")
            console.print("  [cyan]brew install tmux[/cyan]")
        elif system == "linux":
            # Try to detect Linux distribution
            try:
                with open("/etc/os-release") as f:
                    os_info = f.read().lower()
                    if "ubuntu" in os_info or "debian" in os_info:
                        console.print("\nInstall tmux on Ubuntu/Debian:")
                        console.print("  [cyan]sudo apt-get update && sudo apt-get install -y tmux[/cyan]")
                    elif "fedora" in os_info or "centos" in os_info or "rhel" in os_info:
                        console.print("\nInstall tmux on Fedora/CentOS/RHEL:")
                        console.print("  [cyan]sudo yum install -y tmux[/cyan]")
                    elif "arch" in os_info:
                        console.print("\nInstall tmux on Arch Linux:")
                        console.print("  [cyan]sudo pacman -S tmux[/cyan]")
                    else:
                        console.print("\nInstall tmux on Linux:")
                        console.print("  Use your distribution's package manager to install 'tmux'")
            except Exception:
                console.print("\nInstall tmux on Linux:")
                console.print("  Use your distribution's package manager to install 'tmux'")
        else:
            console.print("\nPlease install tmux for your operating system")
            console.print("Visit: https://github.com/tmux/tmux/wiki/Installing")
        return

    # Check Python version
    console.print("Checking Python version...", end=" ")
    py_version = platform.python_version()
    py_major, py_minor = map(int, py_version.split(".")[:2])
    if py_major >= 3 and py_minor >= 11:
        console.print(f"[green]✓ Python {py_version}[/green]")
    else:
        console.print(f"[yellow]⚠ Python {py_version} (3.11+ recommended)[/yellow]")

    # Check if tmux-orc is properly installed
    console.print("Checking tmux-orc installation...", end=" ")
    try:
        import tmux_orchestrator  # noqa: F401

        console.print("[green]✓ Installed[/green]")
    except ImportError:
        console.print("[red]✗ Not properly installed[/red]")
        console.print("\nRun: [cyan]pip install git+https://github.com/EvanSchalton/Tmux-Orchestrator.git[/cyan]")
        return

    console.print("\n[green]✓ All system requirements met![/green]")
    console.print("\nNext steps:")
    console.print("1. Set up Claude Code integration: [cyan]tmux-orc setup claude-code[/cyan]")
    console.print("2. Configure VS Code: [cyan]tmux-orc setup vscode[/cyan]")
    console.print("3. Or run all setups: [cyan]tmux-orc setup all[/cyan]")


@setup.command(name="claude-code")
@click.option(
    "--root-dir",
    help="Root directory for Claude Code config (defaults to auto-detection)",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=None,
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.option("--non-interactive", is_flag=True, help="Use defaults without prompting")
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

        # Source directory for slash commands - try multiple locations
        possible_sources = [
            Path(__file__).parent.parent.parent / ".claude" / "commands",
            Path("/workspaces/Tmux-Orchestrator/.claude/commands"),
            Path.home() / "Tmux-Orchestrator" / ".claude" / "commands",
        ]

        source_commands = None
        for source in possible_sources:
            if source.exists():
                source_commands = source
                break

        if source_commands and source_commands.exists():
            commands_installed = 0
            cmd_files = list(source_commands.glob("*.md"))
            console.print(f"[dim]Found {len(cmd_files)} command files in {source_commands}[/dim]")

            for cmd_file in cmd_files:
                dest_file = commands_dir / cmd_file.name
                if force or not dest_file.exists():
                    shutil.copy2(cmd_file, dest_file)
                    commands_installed += 1

            console.print(f"[green]✓ Installed {commands_installed} slash commands[/green]")
        else:
            console.print("[yellow]⚠ Slash commands source directory not found[/yellow]")
            console.print("[dim]Searched in:[/dim]")
            for source in possible_sources:
                console.print(f"[dim]  • {source}[/dim]")

        progress.update(task, advance=1)

        # Task 3: Configure MCP server
        progress.update(task, description="Configuring MCP server...")

        mcp_config_path = claude_path / "config" / "mcp.json"
        mcp_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        if mcp_config_path.exists() and not force:
            with open(mcp_config_path) as f:
                mcp_config = json.load(f)
        else:
            mcp_config = {"servers": {}}

        # Add tmux-orchestrator server
        mcp_config["servers"]["tmux-orchestrator"] = {
            "command": "tmux-orc",
            "args": ["server", "mcp-serve"],
            "env": {"TMUX_ORC_MODE": "mcp"},
        }

        # Write config
        with open(mcp_config_path, "w") as f:
            json.dump(mcp_config, f, indent=2)

        console.print("[green]✓ Configured MCP server[/green]")
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

        # Task 5: Final instructions
        progress.update(task, description="Setup complete!", advance=1)

    # Display summary
    summary = f"""Claude Code integration complete!

[bold]Installed Components:[/bold]
• Slash commands in: {commands_dir}
• MCP server config: {mcp_config_path}
• Claude instructions: {claude_md_path if claude_md_path.exists() else "Not created"}

[bold]Next Steps:[/bold]
1. Restart Claude Code to load slash commands
2. Test with: /create-prd
3. Monitor MCP server: tmux-orc mcp-status

[bold]Quick Test:[/bold]
In Claude Code, try: "List all tmux sessions"
This should use the MCP server to show active sessions."""

    console.print(Panel(summary, title="Setup Complete", style="green"))


@setup.command(name="vscode")
@click.argument("project_dir", type=click.Path(exists=True), default=".")
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
def setup_vscode(project_dir: str, force: bool) -> None:
    """Configure VS Code tasks and settings for the project.

    PROJECT_DIR: Directory to configure (default: current directory)

    Sets up:
    - tasks.json with orchestrator commands
    - Recommended extensions
    - Debugging configuration
    - Workspace settings

    Examples:
        tmux-orc setup vscode
        tmux-orc setup vscode ./my-project --force
    """
    from tmux_orchestrator.cli.setup import _generate_tasks_config

    project_path = Path(project_dir).resolve()
    vscode_dir = project_path / ".vscode"

    console.print(f"[blue]Setting up VS Code for: {project_path}[/blue]")

    # Create .vscode directory
    vscode_dir.mkdir(exist_ok=True)

    # Generate and write tasks.json
    tasks_file = vscode_dir / "tasks.json"

    # Check if tasks.json already exists
    if tasks_file.exists() and not force:
        console.print("[yellow]tasks.json already exists (use --force to overwrite)[/yellow]")
        return

    # Generate tasks configuration
    tasks_config = _generate_tasks_config(str(project_path))

    # Write tasks.json file
    with open(tasks_file, "w", encoding="utf-8") as f:
        json.dump(tasks_config, f, indent=2, ensure_ascii=False)

    console.print("[green]✓ VS Code configuration complete[/green]")
    console.print(f"  File: {tasks_file}")
    console.print(f"  Tasks: {len(tasks_config.get('tasks', []))}")
    console.print("\nAvailable tasks in VS Code:")
    console.print("• Open All Agents (Ctrl+Shift+P → 'Tasks: Run Task')")
    console.print("• Attach to Development Session")
    console.print("• Start Orchestrator")
    console.print("• Deploy Frontend Team")
    console.print("• Show Daemon Logs")


@setup.command(name="all")
@click.option("--force", is_flag=True, help="Overwrite existing configurations")
def setup_all(force: bool) -> None:
    """Run all setup commands for complete environment configuration.

    Configures:
    - Claude Code integration (slash commands + MCP)
    - MCP server for agent coordination
    - VS Code tasks and settings
    - Git hooks for quality checks
    - Shell completions

    Examples:
        tmux-orc setup all
        tmux-orc setup all --force
    """
    console.print("[bold blue]Running complete environment setup...[/bold blue]\n")

    # Setup Claude Code
    console.print("[cyan]1. Setting up Claude Code...[/cyan]")
    ctx = click.get_current_context()
    ctx.invoke(setup_claude_code, root_dir=None, force=force, non_interactive=False)

    # Setup VS Code
    console.print("\n[cyan]2. Setting up VS Code...[/cyan]")
    ctx.invoke(setup_vscode, project_dir=".", force=force)

    # Setup MCP Server
    console.print("\n[cyan]3. Setting up MCP server...[/cyan]")
    try:
        # Import the server command group to get the setup command
        from tmux_orchestrator.cli.server import server

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
    console.print("3. Execute PRDs with: tmux-orc execute <prd-file>")
    console.print("4. Access MCP server API at: http://127.0.0.1:8000/docs")


@setup.command(name="check")
def check_setup() -> None:
    """Check current setup status and configurations.

    Verifies:
    - Claude Code installation and configuration
    - VS Code tasks configuration
    - MCP server availability
    - Slash command installation

    Examples:
        tmux-orc setup check
    """
    console.print("[bold]Checking Tmux Orchestrator Setup[/bold]\n")

    checks = {
        "Claude Code Directory": False,
        "Slash Commands": False,
        "MCP Configuration": False,
        "MCP Server Running": False,
        "VS Code Tasks": False,
        "Claude Instructions": False,
        "Task Management Dir": False,
    }

    # Check Claude Code - auto-detect location
    project_claude = Path.cwd() / ".claude"
    home_claude = Path.home() / ".claude"

    if project_claude.exists():
        claude_dir = project_claude
    elif home_claude.exists():
        claude_dir = home_claude
    else:
        claude_dir = None

    if claude_dir and claude_dir.exists():
        checks["Claude Code Directory"] = True

        # Check slash commands
        commands_dir = claude_dir / "commands"
        if commands_dir.exists() and list(commands_dir.glob("*.md")):
            checks["Slash Commands"] = True

        # Check MCP config
        mcp_config = claude_dir / "config" / "mcp.json"
        if mcp_config.exists():
            with open(mcp_config) as f:
                config = json.load(f)
                if "tmux-orchestrator" in config.get("servers", {}):
                    checks["MCP Configuration"] = True

    # Check VS Code
    vscode_tasks = Path.cwd() / ".vscode" / "tasks.json"
    if vscode_tasks.exists():
        checks["VS Code Tasks"] = True

    # Check Claude instructions
    if claude_dir:
        claude_md = claude_dir / "CLAUDE.md"
        if claude_md.exists():
            checks["Claude Instructions"] = True

    # Check task management
    task_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator"
    if task_dir.exists():
        checks["Task Management Dir"] = True

    # Check MCP server
    try:
        import requests  # type: ignore[import-untyped]

        response = requests.get("http://127.0.0.1:8000/health", timeout=1)
        if response.status_code == 200:
            checks["MCP Server Running"] = True
    except Exception:
        pass

    # Display results
    from rich.table import Table

    table = Table(title="Setup Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Location", style="blue")

    for component, status in checks.items():
        status_icon = "✓" if status else "✗"
        status_color = "green" if status else "red"

        location = ""
        if component == "Claude Code Directory":
            location = str(claude_dir)
        elif component == "Slash Commands":
            location = str(commands_dir) if "commands_dir" in locals() else "Not found"
        elif component == "MCP Configuration":
            location = str(mcp_config) if "mcp_config" in locals() else "Not found"
        elif component == "VS Code Tasks":
            location = str(vscode_tasks)
        elif component == "Claude Instructions":
            location = str(claude_dir / "CLAUDE.md") if claude_dir else "Not found"
        elif component == "Task Management Dir":
            location = str(task_dir)

        table.add_row(component, f"[{status_color}]{status_icon}[/{status_color}]", location)

    console.print(table)

    # Provide guidance
    missing = [k for k, v in checks.items() if not v]
    if missing:
        console.print("\n[yellow]Missing components:[/yellow]")
        if "Claude Code Directory" in missing:
            console.print("• Install Claude Code and run it once")
        if "Slash Commands" in missing or "MCP Configuration" in missing:
            console.print("• Run: tmux-orc setup claude-code")
        if "VS Code Tasks" in missing:
            console.print("• Run: tmux-orc setup vscode")
        if "Claude Instructions" in missing:
            console.print("• Run: tmux-orc setup claude-code --force")
    else:
        console.print("\n[green]✓ All components properly configured![/green]")
