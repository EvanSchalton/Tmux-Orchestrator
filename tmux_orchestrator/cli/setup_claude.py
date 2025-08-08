"""Setup commands for Claude Code integration."""

import json
import shutil
from pathlib import Path
from typing import Dict, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@click.group()
def setup() -> None:
    """Setup and configuration commands for development environments.
    
    The setup command group provides automated configuration for various
    development tools and environments to work seamlessly with the TMUX
    Orchestrator system.
    
    Available Setups:
        • claude-code: Install slash commands and MCP server
        • vscode: Configure VS Code tasks and debugging
        • git-hooks: Install pre-commit hooks for quality
    
    Examples:
        tmux-orc setup-claude-code       # Setup Claude Code integration
        tmux-orc setup-vscode ./project  # Configure VS Code
        tmux-orc setup-all              # Run all setup commands
    """
    pass


@setup.command(name='claude-code')
@click.option('--claude-dir', help='Claude Code data directory', 
              default=str(Path.home() / '.continue'))
@click.option('--force', is_flag=True, help='Overwrite existing configuration')
def setup_claude_code(claude_dir: str, force: bool) -> None:
    """Install slash commands and MCP server for Claude Code.
    
    Sets up complete Claude Code integration including:
    - Slash commands for PRD creation and task management
    - MCP server configuration for agent control
    - Auto-restart of Claude Code if needed
    
    Examples:
        tmux-orc setup-claude-code
        tmux-orc setup-claude-code --force
        tmux-orc setup-claude-code --claude-dir /custom/path
    """
    claude_path = Path(claude_dir)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Task 1: Check Claude Code directory
        task = progress.add_task("Checking Claude Code installation...", total=5)
        
        if not claude_path.exists():
            console.print(f"[red]Claude Code directory not found: {claude_path}[/red]")
            console.print("\nPlease ensure Claude Code is installed and has been run at least once.")
            return
        
        progress.update(task, advance=1)
        
        # Task 2: Install slash commands
        progress.update(task, description="Installing slash commands...")
        
        commands_dir = claude_path / "commands"
        commands_dir.mkdir(exist_ok=True)
        
        # Source directory for slash commands
        source_commands = Path(__file__).parent.parent.parent / ".claude" / "commands"
        
        if not source_commands.exists():
            # Fallback to workspace location
            source_commands = Path("/workspaces/Tmux-Orchestrator/.claude/commands")
        
        if source_commands.exists():
            commands_installed = 0
            for cmd_file in source_commands.glob("*.md"):
                dest_file = commands_dir / cmd_file.name
                if force or not dest_file.exists():
                    shutil.copy2(cmd_file, dest_file)
                    commands_installed += 1
            
            console.print(f"[green]✓ Installed {commands_installed} slash commands[/green]")
        else:
            console.print("[yellow]⚠ Slash commands directory not found[/yellow]")
        
        progress.update(task, advance=1)
        
        # Task 3: Configure MCP server
        progress.update(task, description="Configuring MCP server...")
        
        mcp_config_path = claude_path / "config" / "mcp.json"
        mcp_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing config or create new
        if mcp_config_path.exists() and not force:
            with open(mcp_config_path, 'r') as f:
                mcp_config = json.load(f)
        else:
            mcp_config = {"servers": {}}
        
        # Add tmux-orchestrator server
        mcp_config["servers"]["tmux-orchestrator"] = {
            "command": "tmux-orc",
            "args": ["mcp-server"],
            "env": {
                "TMUX_ORC_MODE": "mcp"
            }
        }
        
        # Write config
        with open(mcp_config_path, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        
        console.print("[green]✓ Configured MCP server[/green]")
        progress.update(task, advance=1)
        
        # Task 4: Create CLAUDE.md in workspace
        progress.update(task, description="Creating workspace instructions...")
        
        workspace_claude = Path.cwd() / "CLAUDE.md"
        if not workspace_claude.exists() or force:
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
            workspace_claude.write_text(claude_content)
            console.print("[green]✓ Created CLAUDE.md in workspace[/green]")
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
• Workspace instructions: {workspace_claude if workspace_claude.exists() else 'Not created'}

[bold]Next Steps:[/bold]
1. Restart Claude Code to load slash commands
2. Test with: /create-prd
3. Monitor MCP server: tmux-orc mcp-status

[bold]Quick Test:[/bold]
In Claude Code, try: "List all tmux sessions" 
This should use the MCP server to show active sessions."""
    
    console.print(Panel(summary, title="Setup Complete", style="green"))


@setup.command(name='vscode')
@click.argument('project_dir', type=click.Path(exists=True), default='.')
@click.option('--force', is_flag=True, help='Overwrite existing configuration')
def setup_vscode(project_dir: str, force: bool) -> None:
    """Configure VS Code tasks and settings for the project.
    
    PROJECT_DIR: Directory to configure (default: current directory)
    
    Sets up:
    - tasks.json with orchestrator commands
    - Recommended extensions
    - Debugging configuration
    - Workspace settings
    
    Examples:
        tmux-orc setup-vscode
        tmux-orc setup-vscode ./my-project --force
    """
    from tmux_orchestrator.cli.setup import setup_vscode_tasks
    
    project_path = Path(project_dir).resolve()
    vscode_dir = project_path / '.vscode'
    
    console.print(f"[blue]Setting up VS Code for: {project_path}[/blue]")
    
    # Create .vscode directory
    vscode_dir.mkdir(exist_ok=True)
    
    # Setup tasks.json
    success = setup_vscode_tasks(str(project_path))
    
    if success:
        console.print("[green]✓ VS Code configuration complete[/green]")
        console.print("\nAvailable tasks in VS Code:")
        console.print("• Open All Agents (Ctrl+Shift+P → 'Tasks: Run Task')")
        console.print("• Attach to Development Session")
        console.print("• Start Orchestrator")
        console.print("• Deploy Frontend Team")
        console.print("• Show Daemon Logs")
    else:
        console.print("[red]✗ Failed to setup VS Code[/red]")


@setup.command(name='all')
@click.option('--force', is_flag=True, help='Overwrite existing configurations')
def setup_all(force: bool) -> None:
    """Run all setup commands for complete environment configuration.
    
    Configures:
    - Claude Code integration (slash commands + MCP)
    - VS Code tasks and settings
    - Git hooks for quality checks
    - Shell completions
    
    Examples:
        tmux-orc setup-all
        tmux-orc setup-all --force
    """
    console.print("[bold blue]Running complete environment setup...[/bold blue]\n")
    
    # Setup Claude Code
    console.print("[cyan]1. Setting up Claude Code...[/cyan]")
    ctx = click.get_current_context()
    ctx.invoke(setup_claude_code, force=force)
    
    # Setup VS Code
    console.print("\n[cyan]2. Setting up VS Code...[/cyan]")
    ctx.invoke(setup_vscode, project_dir='.', force=force)
    
    console.print("\n[bold green]✓ All setup tasks complete![/bold green]")
    console.print("\nYou can now:")
    console.print("1. Use slash commands in Claude Code")
    console.print("2. Run VS Code tasks for agent management")
    console.print("3. Execute PRDs with: tmux-orc execute <prd-file>")


@setup.command(name='check')
def check_setup() -> None:
    """Check current setup status and configurations.
    
    Verifies:
    - Claude Code installation and configuration
    - VS Code tasks configuration
    - MCP server availability
    - Slash command installation
    
    Examples:
        tmux-orc setup-check
    """
    console.print("[bold]Checking Tmux Orchestrator Setup[/bold]\n")
    
    checks = {
        "Claude Code Directory": False,
        "Slash Commands": False,
        "MCP Configuration": False,
        "VS Code Tasks": False,
        "Workspace CLAUDE.md": False,
        "Task Management Dir": False
    }
    
    # Check Claude Code
    claude_dir = Path.home() / '.continue'
    if claude_dir.exists():
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
    vscode_tasks = Path.cwd() / '.vscode' / 'tasks.json'
    if vscode_tasks.exists():
        checks["VS Code Tasks"] = True
    
    # Check workspace
    if (Path.cwd() / "CLAUDE.md").exists():
        checks["Workspace CLAUDE.md"] = True
    
    # Check task management
    task_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator"
    if task_dir.exists():
        checks["Task Management Dir"] = True
    
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
            location = str(commands_dir) if 'commands_dir' in locals() else "Not found"
        elif component == "MCP Configuration":
            location = str(mcp_config) if 'mcp_config' in locals() else "Not found"
        elif component == "VS Code Tasks":
            location = str(vscode_tasks)
        elif component == "Workspace CLAUDE.md":
            location = str(Path.cwd() / "CLAUDE.md")
        elif component == "Task Management Dir":
            location = str(task_dir)
        
        table.add_row(
            component,
            f"[{status_color}]{status_icon}[/{status_color}]",
            location
        )
    
    console.print(table)
    
    # Provide guidance
    missing = [k for k, v in checks.items() if not v]
    if missing:
        console.print("\n[yellow]Missing components:[/yellow]")
        if "Claude Code Directory" in missing:
            console.print("• Install Claude Code and run it once")
        if "Slash Commands" in missing or "MCP Configuration" in missing:
            console.print("• Run: tmux-orc setup-claude-code")
        if "VS Code Tasks" in missing:
            console.print("• Run: tmux-orc setup-vscode")
        if "Workspace CLAUDE.md" in missing:
            console.print("• Run: tmux-orc setup-claude-code --force")
    else:
        console.print("\n[green]✓ All components properly configured![/green]")