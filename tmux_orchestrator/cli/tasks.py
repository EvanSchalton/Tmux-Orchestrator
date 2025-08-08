"""Task list management commands for orchestrating PRD-driven development."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

console = Console()

# Base directory for all task management
def get_orchestrator_home() -> Path:
    """Get the orchestrator home directory from environment or default."""
    if 'TMUX_ORCHESTRATOR_HOME' in os.environ:
        return Path(os.environ['TMUX_ORCHESTRATOR_HOME'])
    return Path.home() / ".tmux_orchestrator"

# Directory getters that respect environment variable
def get_projects_dir() -> Path:
    """Get projects directory."""
    return get_orchestrator_home() / "projects"

def get_templates_dir() -> Path:
    """Get templates directory."""
    return get_orchestrator_home() / "templates"

def get_archive_dir() -> Path:
    """Get archive directory."""
    return get_orchestrator_home() / "archive"


@click.group()
def tasks() -> None:
    """Task list management for PRD-driven development workflow.
    
    The tasks command group provides comprehensive task management
    capabilities for organizing PRDs, master task lists, and agent-specific
    sub-tasks across development teams.
    
    Directory Structure:
        .tmux_orchestrator/
        ├── projects/           # Active projects
        │   └── {project}/      # Per-project organization
        │       ├── prd.md      # Product Requirements
        │       ├── tasks.md    # Master task list
        │       └── agents/     # Agent sub-tasks
        ├── templates/          # Reusable templates
        └── archive/            # Completed projects
    
    Workflow:
        1. Create project structure
        2. Import or create PRD
        3. Generate master task list
        4. Distribute to agent teams
        5. Track progress
        6. Archive when complete
    
    Examples:
        tmux-orc tasks create my-feature
        tmux-orc tasks import-prd my-feature ./prd.md
        tmux-orc tasks distribute my-feature
        tmux-orc tasks status my-feature
    """
    # Ensure directories exist
    get_projects_dir().mkdir(parents=True, exist_ok=True)
    get_templates_dir().mkdir(parents=True, exist_ok=True)
    get_archive_dir().mkdir(parents=True, exist_ok=True)


@tasks.command()
@click.argument('project_name')
@click.option('--prd', help='Path to existing PRD file to import')
@click.option('--template', is_flag=True, help='Use template for new PRD')
def create(project_name: str, prd: Optional[str], template: bool) -> None:
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
        console=console
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
        tasks_path.write_text(f"""# Tasks - {project_name}

Generated from: prd.md
Date: {datetime.now().strftime('%Y-%m-%d')}

## Task Summary
- Total: 0
- Completed: 0
- In Progress: 0
- Pending: 0

## Relevant Files
_To be updated as implementation progresses_

## Tasks
_To be generated from PRD_
""")
        
        # Create status summary
        summary_path = project_dir / "status" / "summary.md"
        summary_path.write_text(f"""# Project Status Summary - {project_name}

Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

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
""")
        progress.update(task, advance=1, description="Created initial files")
    
    console.print(f"[green]✓ Created project structure for '{project_name}'[/green]")
    console.print(f"\nProject location: {project_dir}")
    console.print("\nNext steps:")
    console.print("1. Edit the PRD: " + str(prd_path))
    console.print("2. Generate tasks: [bold]tmux-orc tasks generate " + project_name + "[/bold]")
    console.print("3. Distribute tasks: [bold]tmux-orc tasks distribute " + project_name + "[/bold]")


@tasks.command()
@click.argument('project_name')
@click.option('--agent', help='Specific agent to show tasks for')
@click.option('--tree', is_flag=True, help='Show as tree structure')
def status(project_name: str, agent: Optional[str], tree: bool) -> None:
    """Display task status for a project.
    
    PROJECT_NAME: Name of the project to check
    
    Shows comprehensive task status including master task list progress,
    agent-specific progress, and overall project health.
    
    Examples:
        tmux-orc tasks status my-project
        tmux-orc tasks status my-project --agent frontend
        tmux-orc tasks status my-project --tree
    """
    project_dir = get_projects_dir() / project_name
    
    if not project_dir.exists():
        console.print(f"[red]Project '{project_name}' not found[/red]")
        return
    
    # Read master task list
    tasks_path = project_dir / "tasks.md"
    if not tasks_path.exists():
        console.print(f"[yellow]No task list found for '{project_name}'[/yellow]")
        return
    
    tasks_content = tasks_path.read_text()
    
    # Count task states
    total_tasks = tasks_content.count("- [ ]") + tasks_content.count("- [-]") + tasks_content.count("- [x]")
    completed = tasks_content.count("- [x]")
    in_progress = tasks_content.count("- [-]")
    pending = tasks_content.count("- [ ]")
    
    # Display header
    console.print(f"\n[bold blue]📋 Task Status - {project_name}[/bold blue]")
    
    # Summary panel
    if total_tasks > 0:
        completion_pct = (completed / total_tasks) * 100
        health = "🟢 On Track" if completion_pct > 30 or in_progress > 0 else "🟡 Needs Attention"
    else:
        completion_pct = 0
        health = "⚫ Not Started"
    
    summary = f"""Total Tasks: {total_tasks}
Completed: {completed} ({completion_pct:.1f}%)
In Progress: {in_progress}
Pending: {pending}
Health: {health}"""
    
    console.print(Panel(summary, title="Master Task Summary", style="green"))
    
    # Show tree view if requested
    if tree:
        tree_view = Tree(f"[bold]{project_name}[/bold]")
        
        # Parse tasks into tree structure
        lines = tasks_content.split('\n')
        current_parent = None
        
        for line in lines:
            if line.strip().startswith("- [ ]") or line.strip().startswith("- [-]") or line.strip().startswith("- [x]"):
                indent_level = len(line) - len(line.lstrip())
                task_text = line.strip()[6:]  # Remove checkbox
                
                if line.strip().startswith("- [x]"):
                    status_icon = "✅"
                elif line.strip().startswith("- [-]"):
                    status_icon = "🔄"
                else:
                    status_icon = "⭕"
                
                if indent_level == 0:
                    current_parent = tree_view.add(f"{status_icon} {task_text}")
                elif current_parent and indent_level > 0:
                    current_parent.add(f"{status_icon} {task_text}")
        
        console.print(tree_view)
    
    # Agent status
    if agent:
        # Show specific agent
        agent_file = project_dir / "agents" / f"{agent}-tasks.md"
        if agent_file.exists():
            agent_content = agent_file.read_text()
            agent_total = agent_content.count("- [ ]") + agent_content.count("- [-]") + agent_content.count("- [x]")
            agent_complete = agent_content.count("- [x]")
            agent_progress = agent_content.count("- [-]")
            
            console.print(f"\n[bold]{agent.title()} Agent Status:[/bold]")
            console.print(f"Tasks: {agent_complete}/{agent_total} complete, {agent_progress} in progress")
        else:
            console.print(f"\n[yellow]No tasks found for {agent} agent[/yellow]")
    else:
        # Show all agents
        agents_dir = project_dir / "agents"
        if agents_dir.exists():
            agent_files = list(agents_dir.glob("*-tasks.md"))
            
            if agent_files:
                console.print("\n[bold]Agent Task Distribution:[/bold]")
                
                table = Table()
                table.add_column("Agent", style="cyan")
                table.add_column("Total", style="yellow")
                table.add_column("Complete", style="green")
                table.add_column("In Progress", style="blue")
                table.add_column("Pending", style="red")
                
                for agent_file in agent_files:
                    agent_name = agent_file.stem.replace("-tasks", "")
                    content = agent_file.read_text()
                    
                    a_total = content.count("- [ ]") + content.count("- [-]") + content.count("- [x]")
                    a_complete = content.count("- [x]")
                    a_progress = content.count("- [-]")
                    a_pending = content.count("- [ ]")
                    
                    table.add_row(
                        agent_name.title(),
                        str(a_total),
                        str(a_complete),
                        str(a_progress),
                        str(a_pending)
                    )
                
                console.print(table)


@tasks.command()
@click.argument('project_name')
@click.option('--frontend', default=2, help='Number of frontend tasks')
@click.option('--backend', default=2, help='Number of backend tasks')
@click.option('--qa', default=1, help='Number of QA tasks')
@click.option('--test', default=1, help='Number of test automation tasks')
def distribute(project_name: str, frontend: int, backend: int, qa: int, test: int) -> None:
    """Distribute tasks from master list to agent teams.
    
    PROJECT_NAME: Project to distribute tasks for
    
    Creates agent-specific task files by analyzing the master task list
    and distributing work according to agent specializations.
    
    Examples:
        tmux-orc tasks distribute my-project
        tmux-orc tasks distribute my-project --frontend 3 --backend 3
    """
    project_dir = get_projects_dir() / project_name
    
    if not project_dir.exists():
        console.print(f"[red]Project '{project_name}' not found[/red]")
        return
    
    tasks_path = project_dir / "tasks.md"
    if not tasks_path.exists():
        console.print(f"[red]No master task list found[/red]")
        return
    
    # Read master tasks
    tasks_content = tasks_path.read_text()
    
    # Parse tasks (simplified - in real implementation would parse more intelligently)
    all_tasks = []
    for line in tasks_content.split('\n'):
        if line.strip().startswith("- [ ]"):
            all_tasks.append(line.strip())
    
    if not all_tasks:
        console.print("[yellow]No pending tasks found to distribute[/yellow]")
        return
    
    console.print(f"[blue]Distributing {len(all_tasks)} tasks across teams...[/blue]")
    
    # Create agent task files
    agents_dir = project_dir / "agents"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # Helper to create agent task file
    def create_agent_tasks(agent_type: str, task_count: int) -> None:
        agent_file = agents_dir / f"{agent_type}-tasks.md"
        
        # Select tasks for this agent (simplified distribution)
        agent_tasks = all_tasks[:task_count] if task_count <= len(all_tasks) else all_tasks
        
        content = f"""# {agent_type.title()} Tasks - {project_name}

Assigned: {timestamp}
PM Session: orchestrator:0
Master Task List: ../tasks.md

## Instructions

See template for detailed instructions on:
- Marking task progress
- Quality gates
- Status reporting

## Current Sprint Tasks

### Priority 1 - Critical Path
"""
        
        for task in agent_tasks[:task_count//2]:
            content += f"{task}\n"
        
        content += "\n### Priority 2 - Important\n"
        
        for task in agent_tasks[task_count//2:task_count]:
            content += f"{task}\n"
        
        content += """

## Completed Tasks
_Move tasks here when complete_

## Quality Checklist

Before marking ANY task complete:
- [ ] Tests written and passing
- [ ] Linting clean
- [ ] Type checking passes
- [ ] Changes committed
- [ ] PM notified

## Daily Status Log

### {timestamp}
**Starting work on assigned tasks**

---
"""
        
        agent_file.write_text(content)
        console.print(f"  [green]✓ Created {agent_type} task list ({len(agent_tasks[:task_count])} tasks)[/green]")
    
    # Distribute to each agent type
    create_agent_tasks("frontend", frontend)
    create_agent_tasks("backend", backend)
    create_agent_tasks("qa", qa)
    create_agent_tasks("test", test)
    
    console.print(f"\n[green]✓ Task distribution complete[/green]")
    console.print("\nNext steps:")
    console.print("1. Review agent task assignments")
    console.print("2. Send task files to respective agents")
    console.print("3. Monitor progress with: [bold]tmux-orc tasks status " + project_name + "[/bold]")


@tasks.command()
@click.argument('project_name')
@click.option('--format', type=click.Choice(['md', 'json', 'html']), default='md', help='Export format')
@click.option('--output', help='Output file path')
def export(project_name: str, format: str, output: Optional[str]) -> None:
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
    data = {
        'project': project_name,
        'exported': datetime.now().isoformat(),
        'tasks': {},
        'agents': {},
        'status': {}
    }
    
    # Read master tasks
    tasks_path = project_dir / "tasks.md"
    if tasks_path.exists():
        data['tasks']['master'] = tasks_path.read_text()
    
    # Read agent tasks
    agents_dir = project_dir / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*-tasks.md"):
            agent_name = agent_file.stem.replace("-tasks", "")
            data['agents'][agent_name] = agent_file.read_text()
    
    # Read status
    summary_path = project_dir / "status" / "summary.md"
    if summary_path.exists():
        data['status']['summary'] = summary_path.read_text()
    
    # Format output
    if format == 'json':
        import json
        output_content = json.dumps(data, indent=2)
        extension = '.json'
    elif format == 'html':
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
    <p>Exported: {data['exported']}</p>
    
    <h2>Master Tasks</h2>
    <pre>{data['tasks'].get('master', 'No tasks found')}</pre>
    
    <h2>Status Summary</h2>
    <pre>{data['status'].get('summary', 'No status found')}</pre>
</body>
</html>"""
        extension = '.html'
    else:  # markdown
        output_content = f"""# Task Export - {project_name}

Exported: {data['exported']}

## Master Task List

{data['tasks'].get('master', '_No tasks found_')}

## Status Summary

{data['status'].get('summary', '_No status found_')}

## Agent Tasks

"""
        for agent, tasks in data['agents'].items():
            output_content += f"### {agent.title()} Agent\n\n{tasks}\n\n"
        
        extension = '.md'
    
    # Write output
    if output:
        output_path = Path(output)
    else:
        output_path = Path(f"{project_name}-tasks-{datetime.now().strftime('%Y%m%d')}{extension}")
    
    output_path.write_text(output_content)
    console.print(f"[green]✓ Exported to: {output_path}[/green]")


@tasks.command()
@click.argument('project_name')
@click.option('--force', is_flag=True, help='Skip confirmation')
def archive(project_name: str, force: bool) -> None:
    """Archive a completed project.
    
    PROJECT_NAME: Project to archive
    
    Moves completed projects to the archive directory with timestamp,
    preserving all task history and status reports.
    
    Examples:
        tmux-orc tasks archive old-project
        tmux-orc tasks archive completed-feature --force
    """
    project_dir = get_projects_dir() / project_name
    
    if not project_dir.exists():
        console.print(f"[red]Project '{project_name}' not found[/red]")
        return
    
    # Check if project is complete
    tasks_path = project_dir / "tasks.md"
    if tasks_path.exists():
        content = tasks_path.read_text()
        if "- [ ]" in content or "- [-]" in content:
            console.print("[yellow]Warning: Project has incomplete tasks![/yellow]")
            if not force:
                confirm = input("Archive anyway? (y/N): ")
                if confirm.lower() != 'y':
                    console.print("[green]Archive cancelled[/green]")
                    return
    
    # Create archive name with timestamp
    archive_name = f"{project_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    archive_path = get_archive_dir() / archive_name
    
    try:
        # Move to archive
        shutil.move(str(project_dir), str(archive_path))
        console.print(f"[green]✓ Archived '{project_name}' to '{archive_name}'[/green]")
        
        # Create summary
        summary = f"""# Archive Summary - {project_name}

Archived: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Original Name: {project_name}
Archive Location: {archive_name}

## Final Status
{content if 'content' in locals() else 'Status unknown'}
"""
        
        (archive_path / "ARCHIVE_SUMMARY.md").write_text(summary)
        
    except Exception as e:
        console.print(f"[red]Failed to archive: {e}[/red]")


@tasks.command()
@click.option('--active', is_flag=True, help='Show only active projects')
@click.option('--archived', is_flag=True, help='Show archived projects')
def list(active: bool, archived: bool) -> None:
    """List all projects and their status.
    
    Shows all projects in the task management system with their
    current status and progress information.
    
    Examples:
        tmux-orc tasks list
        tmux-orc tasks list --active
        tmux-orc tasks list --archived
    """
    show_active = active or not archived
    show_archived = archived or not active
    
    table = Table()
    table.add_column("Project", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Tasks", style="green")
    table.add_column("Progress", style="blue")
    table.add_column("Last Modified", style="magenta")
    
    # Active projects
    if show_active and get_projects_dir().exists():
        for project_dir in sorted(get_projects_dir().iterdir()):
            if project_dir.is_dir():
                # Get task stats
                tasks_path = project_dir / "tasks.md"
                if tasks_path.exists():
                    content = tasks_path.read_text()
                    total = content.count("- [ ]") + content.count("- [-]") + content.count("- [x]")
                    complete = content.count("- [x]")
                    progress = f"{complete}/{total}" if total > 0 else "0/0"
                    pct = (complete/total*100) if total > 0 else 0
                    
                    # Get status
                    if content.count("- [-]") > 0:
                        status = "🔄 In Progress"
                    elif complete == total and total > 0:
                        status = "✅ Complete"
                    elif complete > 0:
                        status = "🟡 Partial"
                    else:
                        status = "⭕ Not Started"
                else:
                    progress = "No tasks"
                    pct = 0
                    status = "📋 Planning"
                
                # Last modified
                mtime = datetime.fromtimestamp(tasks_path.stat().st_mtime if tasks_path.exists() else project_dir.stat().st_mtime)
                
                table.add_row(
                    project_dir.name,
                    status,
                    progress,
                    f"{pct:.0f}%",
                    mtime.strftime("%Y-%m-%d %H:%M")
                )
    
    # Archived projects
    if show_archived and get_archive_dir().exists():
        for archive_dir in sorted(get_archive_dir().iterdir()):
            if archive_dir.is_dir():
                # Extract original name
                parts = archive_dir.name.rsplit('-', 2)
                if len(parts) >= 3:
                    project_name = '-'.join(parts[:-2])
                else:
                    project_name = archive_dir.name
                
                table.add_row(
                    f"[dim]{project_name}[/dim]",
                    "[dim]📦 Archived[/dim]",
                    "[dim]-[/dim]",
                    "[dim]100%[/dim]",
                    "[dim]" + datetime.fromtimestamp(archive_dir.stat().st_mtime).strftime("%Y-%m-%d") + "[/dim]"
                )
    
    if table.row_count == 0:
        console.print("[yellow]No projects found[/yellow]")
    else:
        console.print(f"\n[bold]Task Management Projects[/bold]")
        console.print(table)
        
        if show_active:
            console.print(f"\nActive projects: {sum(1 for _ in get_projects_dir().iterdir() if _.is_dir()) if get_projects_dir().exists() else 0}")
        if show_archived:
            console.print(f"Archived projects: {sum(1 for _ in get_archive_dir().iterdir() if _.is_dir()) if get_archive_dir().exists() else 0}")


@tasks.command()
@click.argument('project_name')
def generate(project_name: str) -> None:
    """Generate task list from PRD using AI analysis.
    
    PROJECT_NAME: Project with PRD to analyze
    
    Reads the project's PRD and generates a comprehensive task list
    following the development standards and patterns.
    
    Examples:
        tmux-orc tasks generate my-project
    """
    project_dir = get_projects_dir() / project_name
    
    if not project_dir.exists():
        console.print(f"[red]Project '{project_name}' not found[/red]")
        return
    
    prd_path = project_dir / "prd.md"
    if not prd_path.exists():
        console.print(f"[red]No PRD found for '{project_name}'[/red]")
        return
    
    console.print(f"[yellow]Task generation from PRD requires AI assistance.[/yellow]")
    console.print("\nTo generate tasks:")
    console.print(f"1. Open the PRD: {prd_path}")
    console.print("2. Use: /workspaces/Tmux-Orchestrator/.claude/commands/generate-tasks.md")
    console.print(f"3. Save generated tasks to: {project_dir}/tasks.md")
    console.print("\nThen distribute with: [bold]tmux-orc tasks distribute " + project_name + "[/bold]")