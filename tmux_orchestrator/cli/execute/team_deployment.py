"""Team deployment and management for PRD execution."""

import subprocess
from typing import Any

from rich.console import Console

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


def deploy_agent_team(
    tmux: TMUXManager,
    project_name: str,
    team_type: str,
    team_size: int,
    briefings: dict[str, str],
    output_json: bool = False,
) -> tuple[bool, dict[str, Any]]:
    """Deploy the agent team for PRD execution.

    Args:
        tmux: TMUX manager instance
        project_name: Name of the project
        team_type: Type of team to deploy
        team_size: Number of agents to deploy
        briefings: Role-specific briefings
        output_json: Whether to output JSON

    Returns:
        Tuple of (success, deployment_data)
    """
    deployment_data: dict[str, Any] = {
        "session": project_name,
        "team_type": team_type,
        "team_size": team_size,
        "agents_deployed": [],
        "errors": [],
    }

    if not output_json:
        console.print(f"\n[blue]Deploying {team_type} team with {team_size} agents...[/blue]")

    # Check if session already exists
    if tmux.has_session(project_name):
        if not output_json:
            console.print(f"[yellow]⚠ Session '{project_name}' already exists[/yellow]")
        deployment_data["errors"].append(f"Session {project_name} already exists")
        return False, deployment_data

    # Create the session
    if not tmux.create_session(project_name, "orchestrator"):
        deployment_data["errors"].append("Failed to create session")
        return False, deployment_data

    # Deploy PM first (window 0)
    pm_deployed = deploy_pm_agent(project_name, briefings.get("pm", ""), output_json)
    if pm_deployed:
        deployment_data["agents_deployed"].append({"role": "pm", "window": 0, "status": "active"})

    # Deploy other agents based on team type and size
    agents_to_deploy = get_team_composition(team_type, team_size)

    for i, agent_role in enumerate(agents_to_deploy, start=1):
        briefing = briefings.get(agent_role, briefings.get("developer", ""))
        if deploy_team_agent(project_name, i, agent_role, briefing, output_json):
            deployment_data["agents_deployed"].append({"role": agent_role, "window": i, "status": "active"})
        else:
            deployment_data["errors"].append(f"Failed to deploy {agent_role}")

    success = len(deployment_data["agents_deployed"]) >= 2  # At least PM + 1 agent

    if not output_json and success:
        console.print(f"[green]✓ Team deployed: {len(deployment_data['agents_deployed'])} agents[/green]")

    return success, deployment_data


def deploy_pm_agent(project_name: str, briefing: str, output_json: bool = False) -> bool:
    """Deploy the Project Manager agent.

    Args:
        project_name: Name of the project
        briefing: PM briefing content
        output_json: Whether to output JSON

    Returns:
        True if deployment successful
    """
    try:
        # Use tmux-orc spawn command
        cmd = ["tmux-orc", "spawn", "pm", "--session", f"{project_name}:0", "--briefing", briefing]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            if not output_json:
                console.print("  [green]✓[/green] PM deployed at window 0")
            return True
        else:
            if not output_json:
                console.print(f"  [red]✗[/red] PM deployment failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        if not output_json:
            console.print("  [red]✗[/red] PM deployment timed out")
        return False
    except Exception as e:
        if not output_json:
            console.print(f"  [red]✗[/red] PM deployment error: {e}")
        return False


def deploy_team_agent(project_name: str, window: int, role: str, briefing: str, output_json: bool = False) -> bool:
    """Deploy a team member agent.

    Args:
        project_name: Name of the project
        window: Window number for the agent
        role: Role of the agent
        briefing: Agent briefing content
        output_json: Whether to output JSON

    Returns:
        True if deployment successful
    """
    try:
        # Use tmux-orc spawn command
        cmd = ["tmux-orc", "spawn", "agent", role, "--session", f"{project_name}:{window}", "--briefing", briefing]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            if not output_json:
                console.print(f"  [green]✓[/green] {role.capitalize()} deployed at window {window}")
            return True
        else:
            if not output_json:
                console.print(f"  [red]✗[/red] {role.capitalize()} deployment failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        if not output_json:
            console.print(f"  [red]✗[/red] {role.capitalize()} deployment timed out")
        return False
    except Exception as e:
        if not output_json:
            console.print(f"  [red]✗[/red] {role.capitalize()} deployment error: {e}")
        return False


def get_team_composition(team_type: str, team_size: int) -> list[str]:
    """Get team composition based on type and size.

    Args:
        team_type: Type of team
        team_size: Number of team members

    Returns:
        List of agent roles to deploy
    """
    # Base compositions
    compositions = {
        "frontend": ["developer", "developer", "qa", "developer", "devops"],
        "backend": ["developer", "developer", "qa", "devops", "developer"],
        "fullstack": ["developer", "developer", "qa", "developer", "devops"],
        "testing": ["qa", "developer", "qa", "developer", "devops"],
        "custom": ["developer", "qa", "developer", "devops", "developer"],
    }

    base_comp = compositions.get(team_type, compositions["fullstack"])

    # Adjust to requested size
    if team_size <= len(base_comp):
        return base_comp[: team_size - 1]  # -1 for PM
    else:
        # Add more developers if larger team requested
        extra = team_size - len(base_comp) - 1
        return base_comp + ["developer"] * extra
