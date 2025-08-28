"""Task generation and distribution monitoring utilities."""

import time
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def wait_for_task_generation(project_name: str, timeout: int = 300) -> bool:
    """Wait for PM to generate tasks from PRD.

    Args:
        project_name: Name of the project
        timeout: Maximum time to wait in seconds

    Returns:
        True if tasks were generated, False if timeout
    """
    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name
    tasks_file = project_dir / "tasks.md"

    console.print(f"\n[yellow]Waiting for PM to generate tasks from PRD (timeout: {timeout}s)...[/yellow]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]PM analyzing PRD and creating tasks...", total=None)

        start_time = time.time()
        last_check = 0

        while time.time() - start_time < timeout:
            # Check if tasks file exists and has content
            if tasks_file.exists():
                content = tasks_file.read_text()
                if len(content) > 100 and "[ ]" in content:  # Has actual tasks
                    progress.update(task, description="[green]✓ Tasks generated successfully!")
                    return True

            # Update progress message periodically
            elapsed = int(time.time() - start_time)
            if elapsed - last_check >= 10:
                progress.update(task, description=f"[cyan]Waiting... ({elapsed}s elapsed)")
                last_check = elapsed

            time.sleep(2)

    console.print("[red]✗ Timeout waiting for task generation[/red]")
    return False


def monitor_task_distribution(project_name: str) -> bool:
    """Monitor task distribution to team members.

    Args:
        project_name: Name of the project

    Returns:
        True if tasks were distributed successfully
    """
    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name
    agents_dir = project_dir / "agents"

    if not agents_dir.exists():
        console.print("[red]✗ Agents directory not found[/red]")
        return False

    console.print("\n[blue]Monitoring task distribution...[/blue]")

    # Check for agent task files
    task_files = list(agents_dir.glob("*-tasks.md"))

    if not task_files:
        console.print("[yellow]⚠ No task files found yet[/yellow]")
        return False

    console.print(f"[green]✓ Found {len(task_files)} agent task files:[/green]")
    for task_file in task_files:
        agent_name = task_file.stem.replace("-tasks", "")
        try:
            content = task_file.read_text()
            task_count = content.count("[ ]") + content.count("[x]")
            console.print(f"  • {agent_name}: {task_count} tasks")
        except Exception:
            console.print(f"  • {agent_name}: [error reading file]")

    return True


def check_project_status(project_name: str) -> dict:
    """Check overall project status.

    Args:
        project_name: Name of the project

    Returns:
        Dictionary with status information
    """
    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name

    status = {
        "prd_exists": (project_dir / "prd.md").exists(),
        "tasks_generated": False,
        "tasks_distributed": False,
        "agents_active": 0,
        "total_tasks": 0,
        "completed_tasks": 0,
    }

    # Check tasks file
    tasks_file = project_dir / "tasks.md"
    if tasks_file.exists():
        try:
            content = tasks_file.read_text()
            status["tasks_generated"] = True
            status["total_tasks"] = content.count("[ ]") + content.count("[x]")
            status["completed_tasks"] = content.count("[x]")
        except Exception:
            pass

    # Check agent tasks
    agents_dir = project_dir / "agents"
    if agents_dir.exists():
        task_files = list(agents_dir.glob("*-tasks.md"))
        if task_files:
            status["tasks_distributed"] = True
            status["agents_active"] = len(task_files)

    return status


def display_project_summary(project_name: str, status: dict) -> None:
    """Display project status summary.

    Args:
        project_name: Name of the project
        status: Status dictionary from check_project_status
    """
    from rich.table import Table

    table = Table(title=f"Project Status: {project_name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Status", style="green")

    table.add_row("PRD Loaded", "✓" if status["prd_exists"] else "✗")
    table.add_row("Tasks Generated", "✓" if status["tasks_generated"] else "✗")
    table.add_row("Tasks Distributed", "✓" if status["tasks_distributed"] else "✗")
    table.add_row("Active Agents", str(status["agents_active"]))
    table.add_row("Total Tasks", str(status["total_tasks"]))
    table.add_row("Completed Tasks", str(status["completed_tasks"]))

    if status["total_tasks"] > 0:
        progress = (status["completed_tasks"] / status["total_tasks"]) * 100
        table.add_row("Progress", f"{progress:.1f}%")

    console.print(table)
