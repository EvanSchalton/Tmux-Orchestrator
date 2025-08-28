"""Project management commands for task workflow."""

import shutil
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree

from tmux_orchestrator.cli.tasks_core import get_archive_dir, get_projects_dir, get_templates_dir

console = Console()


@click.command()
@click.argument("project_name")
@click.option("--prd", help="Path to existing PRD file to import")
@click.option("--template", is_flag=True, help="Use template for new PRD")
def create(project_name: str, prd: str | None, template: bool) -> None:
    """Create a new project task structure.

    PROJECT_NAME: Name of the project (will be directory name)

    Creates the complete directory structure for a new project including
    folders for PRD, tasks, agent sub-tasks, and status tracking.

    Examples:
        tmux-orc tasks create user-auth
        tmux-orc tasks create payment-system --prd ./payment-prd.md
        tmux-orc tasks create new-feature --template
    """
    project_dir = get_projects_dir() / project_name

    if project_dir.exists():
        console.print(f"[red]Project '{project_name}' already exists[/red]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating project structure...", total=5)

        # Create directories
        project_dir.mkdir(parents=True)
        progress.update(task, advance=1, description="Created project directory")

        (project_dir / "agents").mkdir()
        progress.update(task, advance=1, description="Created agents directory")

        (project_dir / "status").mkdir()
        (project_dir / "status" / "daily").mkdir()
        progress.update(task, advance=1, description="Created status directories")

        # Handle PRD
        prd_path = project_dir / "prd.md"
        if prd:
            # Import existing PRD
            try:
                shutil.copy(prd, prd_path)
                progress.update(task, advance=1, description="Imported PRD")
            except Exception as e:
                console.print(f"[red]Failed to import PRD: {e}[/red]")
                return
        elif template:
            # Use template
            template_path = get_templates_dir() / "prd-template.md"
            if template_path.exists():
                shutil.copy(template_path, prd_path)
            else:
                # Create basic PRD
                prd_path.write_text(f"# Product Requirements Document\n\n## Project: {project_name}\n")
            progress.update(task, advance=1, description="Created PRD from template")
        else:
            # Create minimal PRD
            prd_path.write_text(f"# Product Requirements Document\n\n## Project: {project_name}\n")
            progress.update(task, advance=1, description="Created minimal PRD")

        # Create initial files
        tasks_path = project_dir / "tasks.md"
        tasks_path.write_text(
            f"""# Tasks - {project_name}

Generated from: prd.md
Date: {datetime.now().strftime("%Y-%m-%d")}

## Task Summary
- Total: 0
- Completed: 0
- In Progress: 0
- Pending: 0

## Relevant Files
_To be updated as implementation progresses_

## Tasks
_To be generated from PRD_
"""
        )

        # Create status summary
        summary_path = project_dir / "status" / "summary.md"
        summary_path.write_text(
            f"""# Project Status Summary - {project_name}

Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Overall Progress
- Phase: Planning
- Health: 🟢 On Track

## Team Status
- Frontend: Not started
- Backend: Not started
- QA: Not started
- Test: Not started

## Key Metrics
- Tasks Completed: 0/0 (0%)
- Test Coverage: N/A
- Bugs Found: 0
- Bugs Fixed: 0
"""
        )
        progress.update(task, advance=1, description="Created initial files")

    console.print(f"[green]✓ Created project structure for '{project_name}'[/green]")
    console.print(f"\nProject location: {project_dir}")
    console.print("\nNext steps:")
    console.print("1. Edit the PRD: " + str(prd_path))
    console.print("2. Generate tasks: [bold]tmux-orc tasks generate " + project_name + "[/bold]")
    console.print("3. Distribute tasks: [bold]tmux-orc tasks distribute " + project_name + "[/bold]")


@click.command()
@click.argument("project_name")
@click.option("--agent", help="Filter by specific agent")
@click.option("--tree", is_flag=True, help="Display as tree structure")
def status(project_name: str, agent: str | None, tree: bool) -> None:
    """Display project status and progress tracking."""
    project_dir = get_projects_dir() / project_name

    if not project_dir.exists():
        console.print(f"[red]Project '{project_name}' not found[/red]")
        return

    # Load status summary
    summary_path = project_dir / "status" / "summary.md"
    if summary_path.exists():
        console.print(f"[bold blue]📊 Project Status: {project_name}[/bold blue]")

        # Parse and display summary
        content = summary_path.read_text()
        console.print(Panel(content, title="Status Summary", border_style="blue"))

    # Show agent-specific status if requested
    if agent:
        agent_dir = project_dir / "agents" / agent
        if agent_dir.exists():
            console.print(f"\n[bold green]Agent Status: {agent}[/bold green]")
            # Display agent-specific files
        else:
            console.print(f"[yellow]Agent '{agent}' not found in project[/yellow]")

    # Tree view of project structure
    if tree:
        console.print("\n[bold]📁 Project Structure:[/bold]")
        project_tree = Tree(f"📂 {project_name}")

        for item in sorted(project_dir.iterdir()):
            if item.is_dir():
                dir_node = project_tree.add(f"📁 {item.name}/")
                for sub_item in sorted(item.iterdir()):
                    if sub_item.is_file():
                        dir_node.add(f"📄 {sub_item.name}")
            else:
                project_tree.add(f"📄 {item.name}")

        console.print(project_tree)


@click.command()
@click.argument("project_name")
@click.option("--force", is_flag=True, help="Force archive without confirmation")
def archive(project_name: str, force: bool) -> None:
    """Archive a completed project."""
    project_dir = get_projects_dir() / project_name

    if not project_dir.exists():
        console.print(f"[red]Project '{project_name}' not found[/red]")
        return

    # Confirmation unless forced
    if not force:
        console.print(f"[yellow]Archive project '{project_name}'?[/yellow]")
        if not click.confirm("This will move the project to archive"):
            console.print("[green]Archive cancelled[/green]")
            return

    # Create archive directory if needed
    archive_dir = get_archive_dir()
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Move to archive with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = archive_dir / f"{project_name}-{timestamp}"

    try:
        shutil.move(str(project_dir), str(archive_path))
        console.print(f"[green]✓ Project archived to: {archive_path}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to archive project: {e}[/red]")
