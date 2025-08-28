"""Configure VS Code tasks and settings for the project."""

import json
from pathlib import Path

from rich.console import Console

console = Console()


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
    from .generate_tasks_config import generate_tasks_config

    project_path = Path(project_dir).resolve()
    vscode_dir = project_path / ".vscode"

    console.print(f"[blue]Setting up VS Code for: {project_path}[/blue]")

    # Create .vscode directory
    vscode_dir.mkdir(exist_ok=True)

    # Generate and write tasks.json
    tasks_file = vscode_dir / "tasks.json"

    # Handle tasks.json
    if tasks_file.exists() and not force:
        console.print("[yellow]tasks.json already exists (use --force to overwrite)[/yellow]")
        tasks_created = False
    else:
        # Generate tasks configuration
        tasks_config = generate_tasks_config(str(project_path))
        # Write tasks.json file
        with open(tasks_file, "w", encoding="utf-8") as f:
            json.dump(tasks_config, f, indent=2, ensure_ascii=False)
        tasks_created = True
        console.print("[green]✓ Created tasks.json[/green]")

    # Handle settings.json to prevent VS Code auto-activation issues
    settings_file = vscode_dir / "settings.json"
    if settings_file.exists() and not force:
        console.print("[yellow]settings.json already exists (use --force to overwrite)[/yellow]")
        settings_created = False
    else:
        # Load template settings
        import importlib.resources

        template_data = importlib.resources.read_text("tmux_orchestrator.templates", "vscode_settings.json")
        settings_config = json.loads(template_data)

        # Write settings.json file
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_config, f, indent=2, ensure_ascii=False)
        settings_created = True
        console.print("[green]✓ Created settings.json (disabled auto-activation)[/green]")

    if tasks_created or settings_created:
        console.print("\n[green]✓ VS Code configuration complete[/green]")
        if tasks_created:
            console.print(f"  Tasks file: {tasks_file}")
        if settings_created:
            console.print(f"  Settings file: {settings_file}")
    console.print("\nAvailable tasks in VS Code:")
    console.print("• Open All Agents (Ctrl+Shift+P → 'Tasks: Run Task')")
    console.print("• Attach to Development Session")
    console.print("• Start Orchestrator")
    console.print("• Deploy Frontend Team")
    console.print("• Show Daemon Logs")
