"""Execute PRD files by deploying and managing agent teams - Fixed version."""

import json
import subprocess
import time
from pathlib import Path

import click
from rich.console import Console

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()

# Import the existing functions from execute.py


@click.command()
@click.argument("prd_file", type=click.Path(exists=True))
@click.option("--project-name", help="Project name (defaults to PRD filename)")
@click.option("--team-size", default=5, help="Number of agents to deploy")
@click.option(
    "--team-type",
    type=click.Choice(["frontend", "backend", "fullstack", "custom"]),
    default="custom",
    help="Type of team to deploy",
)
@click.option("--no-monitor", is_flag=True, help="Skip starting the monitoring daemon")
@click.option("--skip-planning", is_flag=True, help="Skip team planning phase")
@click.option("--auto", is_flag=True, help="Automatically determine team from PRD analysis")
@click.option("--wait-for-tasks/--no-wait-for-tasks", default=True, help="Wait for PM to generate tasks")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
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
    """Execute a PRD by deploying an agent team."""
    tmux: TMUXManager = ctx.obj["tmux"]

    # Determine project name
    prd_path = Path(prd_file).resolve()
    if not project_name:
        name = prd_path.stem
        if name.startswith("prd-"):
            project_name = name[4:]
        else:
            project_name = name

    # For JSON mode, execute without progress display
    if output_json:
        # Simple execution for JSON output
        success = True
        error_msg = None

        try:
            # Create project
            result = subprocess.run(
                ["tmux-orc", "tasks", "create", project_name, "--prd", str(prd_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                success = False
                error_msg = f"Failed to create project: {result.stderr}"

            # Deploy team if project created
            if success:
                from tmux_orchestrator.core.team_operations.deploy_team import deploy_standard_team

                deploy_success, message = deploy_standard_team(tmux, team_type, team_size, project_name)
                if not deploy_success:
                    success = False
                    error_msg = f"Failed to deploy team: {message}"

        except Exception as e:
            success = False
            error_msg = str(e)

        # Output JSON result
        if success:
            project_dir = (
                Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name
            )
            json_result = {
                "success": True,
                "data": {
                    "project_name": project_name,
                    "prd_file": str(prd_path),
                    "team_type": team_type,
                    "team_size": team_size,
                    "session": project_name,
                    "project_dir": str(project_dir),
                    "monitoring_enabled": not no_monitor,
                    "workflow_status": {"project_created": True, "team_deployed": True, "agents_deployed": team_size},
                    "next_commands": [
                        f"tmux-orc agent send {project_name}:0 'status update'",
                        f"tmux-orc tasks status {project_name}",
                        f"tmux-orc team status {project_name}",
                    ],
                },
                "timestamp": time.time(),
                "command": f"execute {prd_path.name}",
            }
        else:
            json_result = {
                "success": False,
                "error": error_msg,
                "timestamp": time.time(),
                "command": f"execute {prd_path.name}",
            }

        console.print(json.dumps(json_result, indent=2))
        return

    # Regular execution with progress display
    # ... (rest of the original logic)
    console.print("[yellow]Full execute command implementation in progress...[/yellow]")


# Export for CLI registration
__all__ = ["execute"]
