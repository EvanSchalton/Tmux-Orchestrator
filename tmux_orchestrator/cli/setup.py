"""VS Code integration setup commands for TMUX Orchestrator."""

import json
from pathlib import Path
from typing import Any, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

console: Console = Console()


@click.group(name="vscode-setup")
def vscode_setup() -> None:
    """VS Code integration and project setup."""
    pass


@vscode_setup.command("vscode")
@click.option("--project-dir", help="Project directory (defaults to current)")
@click.option("--force", is_flag=True, help="Overwrite existing tasks.json")
@click.option("--minimal", is_flag=True, help="Generate minimal task set")
@click.pass_context
def vscode(ctx: click.Context, project_dir: Optional[str], force: bool, minimal: bool) -> None:
    """Generate VS Code tasks.json for TMUX Orchestrator commands.

    Creates a comprehensive tasks.json file with all CLI commands accessible
    from VS Code's Command Palette and task runner.
    """
    if not project_dir:
        project_dir = str(Path.cwd())

    project_path = Path(project_dir)
    vscode_dir = project_path / ".vscode"
    tasks_file = vscode_dir / "tasks.json"

    console.print(f"[blue]Setting up VS Code integration for: {project_path}[/blue]")

    # Check if .vscode directory exists
    if not vscode_dir.exists():
        console.print("[yellow]Creating .vscode directory...[/yellow]")
        vscode_dir.mkdir(parents=True, exist_ok=True)

    # Check if tasks.json already exists
    if tasks_file.exists() and not force:
        if not Confirm.ask("tasks.json already exists. Overwrite?", default=False):
            console.print("[yellow]Setup cancelled[/yellow]")
            return

    # Generate tasks configuration
    console.print("[blue]Generating VS Code tasks configuration...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task_progress = progress.add_task("Creating tasks...", total=None)

        # Generate tasks based on CLI structure
        tasks_config = _generate_tasks_config(project_dir, minimal)

        progress.update(task_progress, description="Writing tasks.json...")

        # Write tasks.json file
        with open(tasks_file, "w", encoding="utf-8") as f:
            json.dump(tasks_config, f, indent=2, ensure_ascii=False)

        progress.update(task_progress, description="Complete!", completed=100)

    console.print("[green]✓ VS Code tasks.json created successfully![/green]")
    console.print(f"  File: {tasks_file}")
    console.print(f"  Tasks: {len(tasks_config['tasks'])}")

    # Show usage instructions
    _show_usage_instructions()


@vscode_setup.command("workspace")
@click.option("--project-dir", help="Project directory (defaults to current)")
@click.option("--name", help="Workspace name (defaults to directory name)")
@click.pass_context
def workspace(ctx: click.Context, project_dir: Optional[str], name: Optional[str]) -> None:
    """Generate VS Code workspace file with TMUX Orchestrator settings.

    Creates a .code-workspace file with optimized settings for agent development.
    """
    if not project_dir:
        project_dir = str(Path.cwd())

    project_path = Path(project_dir)
    if not name:
        name = project_path.name

    workspace_file = project_path / f"{name}.code-workspace"

    console.print(f"[blue]Creating VS Code workspace: {name}[/blue]")

    # Generate workspace configuration
    workspace_config = _generate_workspace_config(project_dir, name)

    # Write workspace file
    with open(workspace_file, "w", encoding="utf-8") as f:
        json.dump(workspace_config, f, indent=2, ensure_ascii=False)

    console.print(f"[green]✓ VS Code workspace created: {workspace_file}[/green]")
    console.print(f"  Open with: [bold]code {workspace_file}[/bold]")


@vscode_setup.command("extensions")
@click.pass_context
def extensions(ctx: click.Context) -> None:
    """List recommended VS Code extensions for TMUX Orchestrator development."""

    extensions = [
        {
            "id": "ms-python.python",
            "name": "Python",
            "description": "Python language support with IntelliSense",
        },
        {
            "id": "ms-python.mypy-type-checker",
            "name": "Mypy Type Checker",
            "description": "Type checking for Python code",
        },
        {
            "id": "charliermarsh.ruff",
            "name": "Ruff",
            "description": "Fast Python linter and formatter",
        },
        {
            "id": "ms-vscode.terminal-tabs",
            "name": "Terminal Tabs",
            "description": "Enhanced terminal management",
        },
        {
            "id": "alefragnani.project-manager",
            "name": "Project Manager",
            "description": "Manage multiple projects easily",
        },
        {
            "id": "gruntfuggly.todo-tree",
            "name": "TODO Tree",
            "description": "Track TODO comments and tasks",
        },
    ]

    console.print("[bold blue]🔌 Recommended VS Code Extensions[/bold blue]")
    console.print()

    for ext in extensions:
        console.print(f"[cyan]{ext['name']}[/cyan] ([dim]{ext['id']}[/dim])")
        console.print(f"  {ext['description']}")
        console.print()

    console.print("[yellow]To install all extensions:[/yellow]")
    install_cmd = " && ".join([f"code --install-extension {ext['id']}" for ext in extensions])
    console.print(f"[dim]{install_cmd}[/dim]")


@vscode_setup.command("config")
@click.option("--project-dir", help="Project directory (defaults to current)")
@click.option("--interactive", is_flag=True, help="Interactive configuration setup")
@click.pass_context
def config(ctx: click.Context, project_dir: Optional[str], interactive: bool) -> None:
    """Generate VS Code settings.json with TMUX Orchestrator optimizations.

    Creates optimized VS Code settings for agent development workflow.
    """
    if not project_dir:
        project_dir = str(Path.cwd())

    project_path = Path(project_dir)
    vscode_dir = project_path / ".vscode"
    settings_file = vscode_dir / "settings.json"

    # Ensure .vscode directory exists
    vscode_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[blue]Configuring VS Code settings for: {project_path}[/blue]")

    # Base configuration
    settings = {
        "python.defaultInterpreterPath": "./venv/bin/python",
        "python.terminal.activateEnvironment": True,
        "python.testing.pytestEnabled": True,
        "python.testing.unittestEnabled": False,
        "python.linting.enabled": True,
        "python.linting.mypyEnabled": True,
        "python.formatting.provider": "none",
        "python.analysis.typeCheckingMode": "strict",
        "[python]": {
            "editor.defaultFormatter": "charliermarsh.ruff",
            "editor.formatOnSave": True,
            "editor.codeActionsOnSave": {"source.organizeImports": True},
        },
        "files.exclude": {
            "**/__pycache__": True,
            "**/.pytest_cache": True,
            "**/.mypy_cache": True,
            "**/.coverage": True,
            "**/htmlcov": True,
            "**/.ruff_cache": True,
        },
        "terminal.integrated.defaultProfile.linux": "bash",
        "terminal.integrated.defaultProfile.osx": "zsh",
        "workbench.colorTheme": "Default Dark+",
        "editor.rulers": [88],
        "editor.wordWrap": "bounded",
        "editor.wordWrapColumn": 88,
    }

    if interactive:
        console.print("[yellow]Interactive configuration mode[/yellow]")

        # Ask for Python interpreter path
        python_path = Prompt.ask("Python interpreter path", default="./venv/bin/python")
        settings["python.defaultInterpreterPath"] = python_path

        # Ask for additional settings
        if Confirm.ask("Enable format on save?", default=True):
            settings["editor.formatOnSave"] = True

        if Confirm.ask("Enable type checking?", default=True):
            settings["python.analysis.typeCheckingMode"] = "strict"

    # Write settings file
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    console.print(f"[green]✓ VS Code settings configured: {settings_file}[/green]")


def _generate_tasks_config(project_dir: str, minimal: bool = False) -> dict[str, Any]:
    """Generate VS Code tasks configuration."""

    tasks = []

    # Core orchestrator tasks
    orchestrator_tasks = [
        {
            "label": "🎭 Start Orchestrator",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["orchestrator", "start"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Start the main TMUX Orchestrator session",
        },
        {
            "label": "📊 System Status",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["orchestrator", "status"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Show comprehensive system status",
        },
        {
            "label": "⏰ Schedule Reminder",
            "type": "shell",
            "command": "tmux-orc",
            "args": [
                "orchestrator",
                "schedule",
                "${input:minutes}",
                "${input:reminderNote}",
            ],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Schedule a reminder message",
        },
    ]

    # Team management tasks
    team_tasks = [
        {
            "label": "🚀 Deploy Frontend Team",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["team", "deploy", "frontend", "${input:teamSize}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Deploy a frontend development team",
        },
        {
            "label": "🚀 Deploy Backend Team",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["team", "deploy", "backend", "${input:teamSize}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Deploy a backend development team",
        },
        {
            "label": "🔄 Recover Team",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["team", "recover", "${input:sessionName}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Recover failed agents in a team",
        },
    ]

    # Agent management tasks
    agent_tasks = [
        {
            "label": "🤖 Agent Status",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["agent", "status"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Show all agent statuses",
        },
        {
            "label": "🔄 Restart Agent",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["agent", "restart", "${input:agentTarget}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Restart a specific agent",
        },
        {
            "label": "💬 Message Agent",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["agent", "message", "${input:agentTarget}", "${input:message}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Send message to specific agent",
        },
    ]

    # Monitoring tasks
    monitor_tasks = [
        {
            "label": "📈 Monitoring Dashboard",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["monitor", "dashboard"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Open monitoring dashboard",
        },
        {
            "label": "🏁 Start Recovery Daemon",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["monitor", "recovery-start"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Start the agent recovery daemon",
        },
    ]

    # Project Manager tasks
    pm_tasks = [
        {
            "label": "👔 Create Project Manager",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["pm", "create", "${input:sessionName}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Create new Project Manager",
        },
        {
            "label": "📋 PM Status Check",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["pm", "status"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Check Project Manager status",
        },
    ]

    # Build all tasks
    tasks.extend(orchestrator_tasks)

    if not minimal:
        tasks.extend(team_tasks)
        tasks.extend(agent_tasks)
        tasks.extend(monitor_tasks)
        tasks.extend(pm_tasks)

    # Input definitions for interactive tasks
    inputs = [
        {
            "id": "teamSize",
            "description": "Team size",
            "default": "3",
            "type": "promptString",
        },
        {
            "id": "sessionName",
            "description": "Session name",
            "default": "my-project",
            "type": "promptString",
        },
        {
            "id": "agentTarget",
            "description": "Agent target (session:window)",
            "default": "my-project:0",
            "type": "promptString",
        },
        {
            "id": "message",
            "description": "Message text",
            "default": "Status update request",
            "type": "promptString",
        },
        {
            "id": "minutes",
            "description": "Minutes from now",
            "default": "15",
            "type": "promptString",
        },
        {
            "id": "reminderNote",
            "description": "Reminder note",
            "default": "Check progress",
            "type": "promptString",
        },
    ]

    return {"version": "2.0.0", "tasks": tasks, "inputs": inputs}


def _generate_workspace_config(project_dir: str, name: str) -> dict[str, Any]:
    """Generate VS Code workspace configuration."""

    return {
        "folders": [{"path": "."}],
        "settings": {
            "python.defaultInterpreterPath": "./venv/bin/python",
            "python.terminal.activateEnvironment": True,
            "terminal.integrated.defaultProfile.linux": "bash",
            "terminal.integrated.defaultProfile.osx": "zsh",
            "files.exclude": {
                "**/__pycache__": True,
                "**/.pytest_cache": True,
                "**/.mypy_cache": True,
            },
        },
        "extensions": {
            "recommendations": [
                "ms-python.python",
                "ms-python.mypy-type-checker",
                "charliermarsh.ruff",
                "ms-vscode.terminal-tabs",
                "alefragnani.project-manager",
            ]
        },
        "launch": {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "TMUX Orchestrator CLI",
                    "type": "python",
                    "request": "launch",
                    "module": "tmux_orchestrator.cli",
                    "args": ["--help"],
                    "console": "integratedTerminal",
                    "cwd": "${workspaceFolder}",
                }
            ],
        },
    }


def _show_usage_instructions() -> None:
    """Show VS Code integration usage instructions."""

    instructions = """
🎯 **VS Code Integration Ready!**

**How to use:**
1. Open Command Palette: `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type: `Tasks: Run Task`
3. Select any TMUX Orchestrator task from the list

**Quick Access:**
- `Ctrl+Shift+P` → "🎭 Start Orchestrator"
- `Ctrl+Shift+P` → "📊 System Status"
- `Ctrl+Shift+P` → "🚀 Deploy Frontend Team"

**Keyboard Shortcuts:**
- Press `Ctrl+` ` to open integrated terminal
- Use `F1` for Command Palette
- Press `Ctrl+Shift+` ` for new terminal

**Task Categories:**
- 🎭 **Orchestrator** - System management and coordination
- 🚀 **Team** - Deploy and manage agent teams
- 🤖 **Agent** - Individual agent operations
- 📈 **Monitor** - System monitoring and health
- 👔 **PM** - Project manager operations
"""

    panel = Panel(
        instructions.strip(),
        title="[bold green]VS Code Integration Guide[/bold green]",
        border_style="green",
    )
    console.print(panel)
