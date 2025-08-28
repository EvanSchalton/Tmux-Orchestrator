"""Task export and listing commands."""

from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from tmux_orchestrator.cli.tasks_core import get_archive_dir, get_projects_dir

console = Console()


@click.command()
@click.argument("project_name")
@click.option(
    "--format",
    type=click.Choice(["md", "json", "html"]),
    default="md",
    help="Export format",
)
@click.option("--output", help="Output file path")
def export(project_name: str, format: str, output: str | None) -> None:
    """Export project task data.

    PROJECT_NAME: Project to export

    Exports task lists, status, and progress data in various formats
    for reporting and integration with other tools.

    Examples:
        tmux-orc tasks export my-project
        tmux-orc tasks export my-project --format json --output report.json
    """
    project_dir = get_projects_dir() / project_name

    if not project_dir.exists():
        console.print(f"[red]Project '{project_name}' not found[/red]")
        return

    # Gather all data
    data: dict[str, Any] = {
        "project": project_name,
        "exported": datetime.now().isoformat(),
        "tasks": {},
        "agents": {},
        "status": {},
    }

    # Read master tasks
    tasks_path = project_dir / "tasks.md"
    if tasks_path.exists():
        data["tasks"]["master"] = tasks_path.read_text()

    # Read agent tasks
    agents_dir = project_dir / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*-tasks.md"):
            agent_name = agent_file.stem.replace("-tasks", "")
            data["agents"][agent_name] = agent_file.read_text()

    # Read status
    summary_path = project_dir / "status" / "summary.md"
    if summary_path.exists():
        data["status"]["summary"] = summary_path.read_text()

    # Format output
    if format == "json":
        import json

        output_content = json.dumps(data, indent=2)
        extension = ".json"
    elif format == "html":
        # Simple HTML export
        output_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Task Report - {project_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        pre {{ background: #f4f4f4; padding: 10px; }}
        h2 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>Task Report - {project_name}</h1>
    <p>Exported: {data["exported"]}</p>

    <h2>Master Tasks</h2>
    <pre>{data["tasks"].get("master", "No tasks found")}</pre>

    <h2>Status Summary</h2>
    <pre>{data["status"].get("summary", "No status found")}</pre>
</body>
</html>"""
        extension = ".html"
    else:  # markdown
        output_content = f"""# Task Export - {project_name}

Exported: {data["exported"]}

## Master Task List

{data["tasks"].get("master", "_No tasks found_")}

## Status Summary

{data["status"].get("summary", "_No status found_")}

## Agent Tasks

"""
        for agent, tasks in data["agents"].items():
            output_content += f"### {agent.title()} Agent\n\n{tasks}\n\n"

        extension = ".md"

    # Write output
    if output:
        output_path = Path(output)
    else:
        output_path = Path(f"{project_name}-tasks-{datetime.now().strftime('%Y%m%d')}{extension}")

    output_path.write_text(output_content)
    console.print(f"[green]✓ Exported to: {output_path}[/green]")


@click.command(name="list")
@click.option("--active", is_flag=True, help="Show only active projects")
@click.option("--archived", is_flag=True, help="Show only archived projects")
def list_tasks(active: bool, archived: bool) -> None:
    """List all projects and their status."""
    projects = []

    # Active projects
    if not archived:
        projects_dir = get_projects_dir()
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir():
                    projects.append(
                        {"name": project_dir.name, "status": "Active", "path": str(project_dir), "type": "active"}
                    )

    # Archived projects
    if not active:
        archive_dir = get_archive_dir()
        if archive_dir.exists():
            for archived_project in archive_dir.iterdir():
                if archived_project.is_dir():
                    # Parse archived name (project-timestamp format)
                    name_parts = archived_project.name.split("-")
                    if len(name_parts) >= 2:
                        project_name = "-".join(name_parts[:-1])  # Everything except timestamp
                        timestamp = name_parts[-1]
                    else:
                        project_name = archived_project.name
                        timestamp = "Unknown"

                    projects.append(
                        {
                            "name": project_name,
                            "status": f"Archived ({timestamp})",
                            "path": str(archived_project),
                            "type": "archived",
                        }
                    )

    if not projects:
        console.print("[yellow]No projects found[/yellow]")
        return

    # Display table
    table = Table()
    table.add_column("Project", style="cyan", width=25)
    table.add_column("Status", style="green", width=20)
    table.add_column("Path", style="blue")

    for project in sorted(projects, key=lambda x: (x["type"], x["name"])):
        table.add_row(project["name"], project["status"], project["path"])

    console.print(table)
    console.print(f"\n[bold]Total projects: {len(projects)}[/bold]")

    # Summary by type
    active_count = len([p for p in projects if p["type"] == "active"])
    archived_count = len([p for p in projects if p["type"] == "archived"])

    if active_count > 0:
        console.print(f"Active: {active_count}")
    if archived_count > 0:
        console.print(f"Archived: {archived_count}")
