"""Project setup and initialization for PRD execution."""

import json
import shutil
from pathlib import Path

from rich.console import Console

console = Console()


def setup_project_structure(project_name: str, prd_path: Path, output_json: bool = False) -> tuple[bool, Path]:
    """Set up project directory structure and copy PRD.

    Args:
        project_name: Name of the project
        prd_path: Path to the PRD file
        output_json: Whether to output JSON

    Returns:
        Tuple of (success, project_dir)
    """
    project_base = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects"
    project_dir = project_base / project_name

    if not output_json:
        console.print(f"\n[blue]Setting up project structure for {project_name}...[/blue]")

    try:
        # Create directory structure
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "agents").mkdir(exist_ok=True)
        (project_dir / "status").mkdir(exist_ok=True)
        (project_dir / "logs").mkdir(exist_ok=True)

        # Copy PRD to project directory
        target_prd = project_dir / "prd.md"
        if prd_path.exists():
            shutil.copy2(prd_path, target_prd)
            if not output_json:
                console.print(f"  [green]✓[/green] PRD copied to {target_prd}")
        else:
            if not output_json:
                console.print(f"  [red]✗[/red] PRD file not found: {prd_path}")
            return False, project_dir

        # Create initial status file
        status_file = project_dir / "status" / "project.json"
        status_data = {
            "project_name": project_name,
            "prd_file": str(prd_path),
            "created_at": Path(prd_path).stat().st_mtime if prd_path.exists() else 0,
            "status": "initialized",
            "phase": "planning",
        }

        with open(status_file, "w") as f:
            json.dump(status_data, f, indent=2)

        if not output_json:
            console.print(f"  [green]✓[/green] Project structure created at {project_dir}")

        return True, project_dir

    except Exception as e:
        if not output_json:
            console.print(f"  [red]✗[/red] Failed to set up project: {e}")
        return False, project_dir


def validate_prd_file(prd_path: Path) -> tuple[bool, str]:
    """Validate PRD file exists and is readable.

    Args:
        prd_path: Path to the PRD file

    Returns:
        Tuple of (valid, error_message)
    """
    if not prd_path.exists():
        return False, f"PRD file does not exist: {prd_path}"

    if not prd_path.is_file():
        return False, f"PRD path is not a file: {prd_path}"

    try:
        # Try to read the file
        content = prd_path.read_text()
        if len(content) < 10:
            return False, "PRD file appears to be empty"

        return True, ""

    except Exception as e:
        return False, f"Cannot read PRD file: {e}"


def create_initial_tasks_file(project_dir: Path) -> bool:
    """Create initial tasks.md file for PM to populate.

    Args:
        project_dir: Project directory path

    Returns:
        True if created successfully
    """
    tasks_file = project_dir / "tasks.md"

    initial_content = """# Project Tasks

## Status: Pending PM Analysis

The Project Manager will analyze the PRD and generate tasks here.

This file will be populated with:
- [ ] Feature implementation tasks
- [ ] Testing requirements
- [ ] Documentation needs
- [ ] Infrastructure setup
- [ ] Quality assurance tasks

---
*Waiting for PM to read PRD and create task breakdown...*
"""

    try:
        tasks_file.write_text(initial_content)
        return True
    except Exception:
        return False


def check_session_availability(project_name: str) -> tuple[bool, str]:
    """Check if session name is available.

    Args:
        project_name: Proposed session name

    Returns:
        Tuple of (available, message)
    """
    import subprocess

    try:
        result = subprocess.run(["tmux", "has-session", "-t", project_name], capture_output=True, text=True)

        if result.returncode == 0:
            return False, f"Session '{project_name}' already exists"
        else:
            return True, f"Session '{project_name}' is available"

    except Exception as e:
        return False, f"Cannot check session: {e}"
