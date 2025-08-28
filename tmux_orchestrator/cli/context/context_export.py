"""Context export commands."""

import json as json_module
import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from .context_utils import get_available_contexts, load_context

console = Console()


@click.command("export")
@click.argument("output_file", type=click.Path())
@click.option("--role", required=True, help="System role (orchestrator/pm) to export")
@click.option("--project", help="Project name for customization")
@click.option("--json", is_flag=True, help="Output in JSON format")
def export_context(output_file: str, role: str, project: Optional[str] = None, json: bool = False) -> None:
    """Export a system role context to a file for customization.

    <mcp>Export role context to file for customization (args: [output_file, --role], options: --project). Exports standardized context template to file for project-specific customization. Use to create custom agent briefings based on standard roles.</mcp>

    Only orchestrator and PM have standard contexts. All other agents
    (developers, writers, engineers, artists, etc.) should have custom
    briefings defined in your team plan.

    Examples:
        tmux-orc context export my-pm-briefing.md --role pm
        tmux-orc context export orchestrator-api.md --role orchestrator --project "API Service"
    """

    start_time = time.time()

    try:
        content = load_context(role)
    except click.ClickException as e:
        if json:
            result = {
                "success": False,
                "role": role,
                "output_file": output_file,
                "error": str(e),
                "available_roles": list(get_available_contexts().keys()),
                "timestamp": time.time(),
            }
            console.print(json_module.dumps(result, indent=2))
        else:
            console.print(f"[red]Error: {e}[/red]")
        return

    original_content_length = len(content)

    if project:
        content += f"\n\n## Project: {project}\n\n[Add project-specific details here]\n"

    try:
        Path(output_file).write_text(content)
        success = True
        error_message = None
    except Exception as e:
        success = False
        error_message = str(e)

    execution_time = (time.time() - start_time) * 1000

    result_data = {
        "success": success,
        "role": role,
        "output_file": output_file,
        "project": project,
        "content_length": len(content),
        "original_content_length": original_content_length,
        "execution_time_ms": execution_time,
        "timestamp": time.time(),
    }

    if not success:
        result_data["error"] = error_message

    if json:
        console.print(json_module.dumps(result_data, indent=2))
    else:
        if success:
            console.print(f"[green]✓ Exported {role} context to {output_file}[/green]")
        else:
            console.print(f"[red]✗ Failed to export context: {error_message}[/red]")
