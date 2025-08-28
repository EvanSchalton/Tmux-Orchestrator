"""Execute command module - PRD execution via agent teams.

This module has been refactored following development-patterns.md:
- Business logic separated into focused modules
- Each module handles single responsibility
- Clean import organization at top level
- Full backwards compatibility maintained
"""

import json
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from tmux_orchestrator.utils.tmux import TMUXManager

from .prd_analyzer import analyze_prd_for_team_composition
from .project_setup import setup_project_structure, validate_prd_file
from .task_monitor import (
    check_project_status,
    display_project_summary,
    monitor_task_distribution,
    wait_for_task_generation,
)
from .team_briefing import generate_team_briefings_from_prd
from .team_deployment import deploy_agent_team

console = Console()


@click.command()
@click.argument("prd_file", type=click.Path(exists=True))
@click.option("--project-name", "-p", help="Project name (default: derived from PRD filename)")
@click.option("--team-size", "-s", default=5, help="Number of agents in team")
@click.option(
    "--team-type",
    "-t",
    type=click.Choice(["frontend", "backend", "fullstack", "testing", "custom"]),
    default="custom",
    help="Team composition type",
)
@click.option("--no-monitor", is_flag=True, help="Skip monitoring after deployment")
@click.option("--skip-planning", is_flag=True, help="Skip planning phase")
@click.option("--auto", "-a", is_flag=True, help="Auto-determine team from PRD analysis")
@click.option("--wait-for-tasks", is_flag=True, help="Wait for PM to generate tasks")
@click.option("--json", "output_json", is_flag=True, help="Output execution data as JSON")
@click.pass_context
def execute(
    ctx: click.Context,
    prd_file: str,
    project_name: str | None,
    team_size: int,
    team_type: str,
    no_monitor: bool,
    skip_planning: bool,
    auto: bool,
    wait_for_tasks: bool,
    output_json: bool,
) -> None:
    """Execute a PRD by deploying an agent team for manual orchestration.

    PRD_FILE: Path to the Product Requirements Document

    This command sets up a manual orchestration workflow where Claude (you)
    acts as the orchestrator to oversee an autonomous AI agent team.

    WORKFLOW:
    1. Creates project structure and copies PRD
    2. Analyzes PRD to suggest optimal team composition
    3. Deploys the agent team with role-specific briefings
    4. PM agent autonomously reads PRD and creates tasks
    5. PM distributes tasks to team members
    6. Team works independently with PM coordination
    7. You monitor and guide at a high level

    Examples:
        tmux-orc execute ./prd.md
        tmux-orc execute ./prd.md --auto
        tmux-orc execute ./prd.md --project-name myapp
        tmux-orc execute ./prd.md --team-type backend --team-size 4
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Determine project name
    prd_path = Path(prd_file).resolve()
    if not project_name:
        # Extract from filename: prd-user-auth.md -> user-auth
        name = prd_path.stem
        if name.startswith("prd-"):
            project_name = name[4:]
        else:
            project_name = name

    # Track execution data for JSON output
    execution_data: dict[str, Any] = {
        "project_name": project_name,
        "prd_file": str(prd_path),
        "team_type": team_type,
        "team_size": team_size,
        "monitoring": not no_monitor,
        "auto_mode": auto,
        "wait_for_tasks": wait_for_tasks,
        "steps_completed": [],
        "errors": [],
    }

    # Step 1: Validate PRD file
    valid, error_msg = validate_prd_file(prd_path)
    if not valid:
        execution_data["errors"].append(error_msg)
        if output_json:
            console.print(json.dumps(execution_data, indent=2))
        else:
            console.print(f"[red]✗ {error_msg}[/red]")
        return

    # Step 2: Analyze PRD if auto mode
    if auto or team_type == "custom":
        if not output_json:
            console.print("[blue]Analyzing PRD to determine optimal team composition...[/blue]")
        analyzed_type, analyzed_size, tech_scores = analyze_prd_for_team_composition(prd_path)

        if auto:
            team_type = analyzed_type
            team_size = analyzed_size
            if not output_json:
                console.print("[green]✓ PRD Analysis Complete[/green]")
                console.print(f"  Suggested team: {team_type} with {team_size} agents")

    execution_data["team_type"] = team_type
    execution_data["team_size"] = team_size

    # Step 3: Set up project structure
    success, project_dir = setup_project_structure(project_name, prd_path, output_json)
    if not success:
        execution_data["errors"].append("Failed to set up project structure")
        if output_json:
            console.print(json.dumps(execution_data, indent=2))
        return

    execution_data["steps_completed"].append("project_setup")

    # Step 4: Generate team briefings
    briefings = generate_team_briefings_from_prd(prd_path, project_name, team_type)

    # Step 5: Deploy the team
    if not skip_planning:
        if not output_json:
            console.print(
                Panel.fit(
                    f"[bold]Ready to Deploy {team_type.title()} Team[/bold]\n\n"
                    f"Project: {project_name}\n"
                    f"Team Size: {team_size} agents\n"
                    f"PRD: {prd_path.name}",
                    title="Deployment Summary",
                )
            )

            if not auto and not Confirm.ask("Deploy this team configuration?"):
                console.print("[yellow]Deployment cancelled[/yellow]")
                return

    # Deploy the team
    deploy_success, deployment_data = deploy_agent_team(
        tmux, project_name, team_type, team_size, briefings, output_json
    )

    if not deploy_success:
        execution_data["errors"].append("Team deployment failed")
        if output_json:
            console.print(json.dumps(execution_data, indent=2))
        else:
            console.print("[red]✗ Team deployment failed[/red]")
        return

    execution_data["steps_completed"].append("team_deployment")
    execution_data["deployment_data"] = deployment_data

    # Step 6: Wait for task generation if requested
    if wait_for_tasks:
        if wait_for_task_generation(project_name):
            execution_data["steps_completed"].append("task_generation")
            monitor_task_distribution(project_name)
            execution_data["steps_completed"].append("task_distribution")

    # Step 7: Display final status
    if not output_json:
        console.print("\n" + "=" * 50)
        console.print("[bold green]✓ PRD Execution Started Successfully[/bold green]")
        console.print("=" * 50)

        # Show project status
        status = check_project_status(project_name)
        display_project_summary(project_name, status)

        console.print("\n[cyan]Next Steps:[/cyan]")
        console.print(f"  • Monitor PM: tmux-orc read --session {project_name}:0")
        console.print(f"  • Check tasks: tmux-orc tasks status {project_name}")
        console.print(f"  • View team: tmux-orc team status {project_name}")
        console.print(f"  • Message PM: tmux-orc send {project_name}:0 'status?'")

    if output_json:
        execution_data["success"] = True
        console.print(json.dumps(execution_data, indent=2))


# Export the command for backwards compatibility
__all__ = ["execute"]
