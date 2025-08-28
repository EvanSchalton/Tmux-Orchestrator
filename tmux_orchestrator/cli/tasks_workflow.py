"""Task workflow and distribution commands."""

from datetime import datetime

import click
from rich.console import Console

from tmux_orchestrator.cli.tasks_core import get_projects_dir

console = Console()


@click.command()
@click.argument("project_name")
@click.option("--frontend", default=0, help="Number of frontend tasks (0=auto)")
@click.option("--backend", default=0, help="Number of backend tasks (0=auto)")
@click.option("--qa", default=0, help="Number of QA tasks (0=auto)")
@click.option("--test", default=0, help="Number of test automation tasks (0=auto)")
@click.option("--auto", is_flag=True, default=True, help="Auto-detect agents from session")
@click.pass_context
def distribute(
    ctx: click.Context, project_name: str, frontend: int, backend: int, qa: int, test: int, auto: bool
) -> None:
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
        console.print("[red]No master task list found[/red]")
        return

    # Read master tasks
    tasks_content = tasks_path.read_text()

    # Parse tasks more intelligently by section and priority
    all_tasks = []
    task_categories: dict[str, list[str]] = {
        "frontend": [],
        "backend": [],
        "api": [],
        "database": [],
        "testing": [],
        "documentation": [],
        "devops": [],
        "general": [],
    }

    lines = tasks_content.split("\n")
    for line in lines:
        # Parse tasks
        if line.strip().startswith("- [ ]"):
            task = line.strip()
            # Categorize based on content
            task_lower = task.lower()

            if any(word in task_lower for word in ["ui", "component", "frontend", "react", "vue", "css", "design"]):
                task_categories["frontend"].append(task)
            elif any(word in task_lower for word in ["api", "endpoint", "rest", "graphql"]):
                task_categories["api"].append(task)
            elif any(word in task_lower for word in ["database", "schema", "migration", "query"]):
                task_categories["database"].append(task)
            elif any(word in task_lower for word in ["test", "testing", "qa", "spec"]):
                task_categories["testing"].append(task)
            elif any(word in task_lower for word in ["backend", "server", "service", "logic"]):
                task_categories["backend"].append(task)
            elif any(word in task_lower for word in ["deploy", "docker", "ci/cd", "infrastructure"]):
                task_categories["devops"].append(task)
            elif any(word in task_lower for word in ["document", "readme", "docs"]):
                task_categories["documentation"].append(task)
            else:
                task_categories["general"].append(task)

            all_tasks.append(task)

    if not all_tasks:
        console.print("[yellow]No pending tasks found to distribute[/yellow]")
        return

    console.print(f"[blue]Distributing {len(all_tasks)} tasks across teams...[/blue]")

    # Show task breakdown
    console.print("\n[bold]Task Categories:[/bold]")
    for category, tasks in task_categories.items():
        if tasks:
            console.print(f"  {category.title()}: {len(tasks)} tasks")

    # Auto-detect agents if enabled
    if auto and (frontend == 0 or backend == 0 or qa == 0 or test == 0):
        from tmux_orchestrator.utils.tmux import TMUXManager

        tmux = ctx.obj.get("tmux", TMUXManager())

        if tmux.has_session(project_name):
            windows = tmux.list_windows(project_name)

            # Count agent types
            agent_counts = {"frontend": 0, "backend": 0, "qa": 0, "test": 0}

            for window in windows[1:]:  # Skip PM at window 0
                window_name = window["name"].lower()
                if "frontend" in window_name:
                    agent_counts["frontend"] += 1
                elif "backend" in window_name:
                    agent_counts["backend"] += 1
                elif "qa" in window_name:
                    agent_counts["qa"] += 1
                elif "test" in window_name:
                    agent_counts["test"] += 1

            # Use detected counts if not manually specified
            if frontend == 0:
                frontend = agent_counts["frontend"] * 3  # 3 tasks per frontend agent
            if backend == 0:
                backend = agent_counts["backend"] * 3  # 3 tasks per backend agent
            if qa == 0:
                qa = agent_counts["qa"] * 2  # 2 tasks per QA agent
            if test == 0:
                test = agent_counts["test"] * 2  # 2 tasks per test agent

            console.print(f"\n[green]✓ Auto-detected {sum(agent_counts.values())} agents in session[/green]")

    # Create agent task files
    agents_dir = project_dir / "agents"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Helper to create agent task file
    def create_agent_tasks(agent_type: str, task_count: int) -> None:
        agent_file = agents_dir / f"{agent_type}-tasks.md"

        # Select tasks for this agent based on categories
        agent_tasks: list[str] = []

        # Map agent types to task categories
        if agent_type == "frontend":
            agent_tasks.extend(task_categories["frontend"])
            agent_tasks.extend(task_categories["general"][: max(0, task_count - len(agent_tasks))])
        elif agent_type == "backend":
            agent_tasks.extend(task_categories["backend"])
            agent_tasks.extend(task_categories["api"])
            agent_tasks.extend(task_categories["database"])
            agent_tasks.extend(task_categories["general"][: max(0, task_count - len(agent_tasks))])
        elif agent_type == "qa":
            agent_tasks.extend(task_categories["testing"])
            agent_tasks.extend(task_categories["general"][: max(0, task_count - len(agent_tasks))])
        elif agent_type == "test":
            agent_tasks.extend(task_categories["testing"][: task_count // 2])
            agent_tasks.extend(task_categories["documentation"][: task_count // 2])
            agent_tasks.extend(task_categories["general"][: max(0, task_count - len(agent_tasks))])

        # Limit to requested count
        agent_tasks = agent_tasks[:task_count] if task_count > 0 else agent_tasks

        # Create the file
        if agent_tasks:
            content = f"""# {agent_type.title()} Tasks - {project_name}

Generated: {timestamp}
Total Tasks: {len(agent_tasks)}

## Instructions
- Work through these tasks in order
- Mark completed tasks with [x]
- Update status in daily standup
- Communicate blockers to PM

## Tasks

{chr(10).join(agent_tasks)}

## Status Summary
- [ ] Review tasks and ask questions
- [ ] Begin implementation
- [ ] Regular progress updates
- [ ] Testing and validation
- [ ] Mark complete when done
"""
            agent_file.write_text(content)
            console.print(f"[green]✓ Created {agent_type} tasks: {len(agent_tasks)} tasks[/green]")

    # Generate agent task files
    if frontend > 0:
        create_agent_tasks("frontend", frontend)
    if backend > 0:
        create_agent_tasks("backend", backend)
    if qa > 0:
        create_agent_tasks("qa", qa)
    if test > 0:
        create_agent_tasks("test", test)

    console.print("\n[bold green]✓ Task distribution complete![/bold green]")
    console.print("Next steps:")
    console.print("1. Review agent task files in agents/ directory")
    console.print("2. Notify agents that tasks are ready")
    console.print("3. Monitor progress with: [bold]tmux-orc tasks status " + project_name + "[/bold]")


@click.command()
@click.argument("project_name")
def generate(project_name: str) -> None:
    """Generate master task list from PRD."""
    project_dir = get_projects_dir() / project_name

    if not project_dir.exists():
        console.print(f"[red]Project '{project_name}' not found[/red]")
        return

    prd_path = project_dir / "prd.md"
    if not prd_path.exists():
        console.print("[red]No PRD found. Create project first.[/red]")
        return

    # Read PRD content
    prd_path.read_text()

    # Simple task generation based on common patterns
    tasks = [
        "- [ ] Review and refine PRD",
        "- [ ] Set up project structure",
        "- [ ] Create database schema",
        "- [ ] Implement core API endpoints",
        "- [ ] Create frontend components",
        "- [ ] Write unit tests",
        "- [ ] Integration testing",
        "- [ ] Documentation",
        "- [ ] Deployment setup",
    ]

    # Generate tasks file
    tasks_path = project_dir / "tasks.md"
    content = f"""# Tasks - {project_name}

Generated from: prd.md
Date: {datetime.now().strftime("%Y-%m-%d")}

## Task Summary
- Total: {len(tasks)}
- Completed: 0
- In Progress: 0
- Pending: {len(tasks)}

## Relevant Files
_To be updated as implementation progresses_

## Tasks

{chr(10).join(tasks)}

## Notes
- Tasks generated from PRD analysis
- Customize based on specific requirements
- Use `tmux-orc tasks distribute` to assign to agents
"""

    tasks_path.write_text(content)
    console.print(f"[green]✓ Generated {len(tasks)} tasks for {project_name}[/green]")
    console.print(f"Tasks file: {tasks_path}")
    console.print("\nNext step: [bold]tmux-orc tasks distribute " + project_name + "[/bold]")
