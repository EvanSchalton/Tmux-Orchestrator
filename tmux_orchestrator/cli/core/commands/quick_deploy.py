"""Quick deploy command - Rapidly deploy optimized team configurations."""

import time
from pathlib import Path

import click


def quick_deploy_team(
    ctx: click.Context, team_type: str, size: int, project_name: str | None, output_json: bool
) -> None:
    """Rapidly deploy optimized team configurations for immediate productivity.

    <mcp>Deploy pre-configured team with optimized roles (requires: team_type, size). Creates battle-tested team configurations instantly. Different from 'team deploy' which allows custom configurations, and 'agent deploy' for individual agents.</mcp>

    Creates a complete, ready-to-work team using battle-tested configurations
    and role distributions. Perfect for getting projects started quickly.

    TEAM_TYPE: Team specialization (frontend, backend, fullstack, testing)
    SIZE: Number of agents (recommended: 2-6)

    Examples:
        tmux-orc quick-deploy frontend 3        # 3-agent frontend team
        tmux-orc quick-deploy backend 4         # 4-agent backend team
        tmux-orc quick-deploy fullstack 5       # 5-agent fullstack team
        tmux-orc quick-deploy testing 2         # 2-agent testing team
        tmux-orc quick-deploy frontend 4 --project-name my-app

    Optimized Team Configurations:

    Frontend (2-6 agents):
        2 agents: Developer + PM
        3 agents: Developer + UI/UX + PM
        4+ agents: + Performance Expert + CSS Specialist

    Backend (2-6 agents):
        2 agents: API Developer + PM
        3 agents: + Database Engineer
        4+ agents: + DevOps Engineer + Security Specialist

    Fullstack (3-8 agents):
        3 agents: Lead + Frontend + Backend
        4 agents: + Project Manager
        5+ agents: + QA + DevOps + Specialists

    Testing (2-4 agents):
        2 agents: Manual + Automation Tester
        3 agents: + QA Lead
        4+ agents: + Performance + Security Tester

    Perfect for hackathons, quick prototypes, urgent projects,
    or when you need a team running in under 2 minutes.
    """
    from tmux_orchestrator.core.team_operations.deploy_team_optimized import deploy_standard_team_optimized

    console = ctx.obj["console"]

    if not project_name:
        project_name = Path.cwd().name

    if not output_json:
        console.print(f"[blue]Deploying {team_type} team with {size} agents...[/blue]")

    # Delegate to optimized business logic
    success, message = deploy_standard_team_optimized(ctx.obj["tmux_optimized"], team_type, size, project_name)

    if output_json:
        # Standard JSON format: success, data, timestamp, command
        result = {
            "success": success,
            "data": {
                "team_type": team_type,
                "size": size,
                "project_name": project_name,
                "session_name": project_name,  # Session name typically matches project
                "message": message,
                "agents_deployed": size if success else 0,
                "next_steps": [
                    f"tmux-orc team status {project_name}",
                    f"tmux-orc team broadcast {project_name} 'Start working on project'",
                    "tmux-orc agent status",
                ]
                if success
                else [],
            },
            "timestamp": time.time(),
            "command": f"quick-deploy {team_type} {size}",
        }
        import json

        console.print(json.dumps(result, indent=2))
    else:
        if success:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[red]✗ {message}[/red]")
