"""Deploy an individual specialized agent."""

import click
from rich.console import Console

console = Console()


def deploy_agent(ctx: click.Context, agent_type: str, role: str, json: bool) -> None:
    """Deploy an individual specialized agent."""
    # Implementation would go here
    if json:
        import json as json_module

        result = {
            "success": True,
            "agent_type": agent_type,
            "role": role,
            "message": f"Deployed {role} agent of type {agent_type}",
        }
        console.print(json_module.dumps(result, indent=2))
    else:
        console.print(f"[green]✓ Deployed {role} agent of type {agent_type}[/green]")
