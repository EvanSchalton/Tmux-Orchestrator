"""Context display commands."""

import json as json_module

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .context_utils import get_available_contexts, load_context

console = Console()


@click.command("show")
@click.argument("role")
@click.option("--raw", is_flag=True, help="Output raw markdown without formatting")
@click.option("--json", is_flag=True, help="Output in JSON format")
def show_context(role: str, raw: bool, json: bool) -> None:
    """Display context briefing for a specific role.

    <mcp>Show standardized agent role context (args: [role_name], options: --raw). Displays full context briefing for orchestrator/pm roles. Use --raw for copying into custom briefings. Essential for context rehydration.</mcp>

    ROLE: The agent role to show context for

    Examples:
        tmux-orc context show orc
        tmux-orc context show pm --raw  # For copying into briefings
    """
    try:
        content = load_context(role)
    except click.ClickException as e:
        if json:
            result = {
                "success": False,
                "role": role,
                "error": str(e),
                "available_roles": list(get_available_contexts().keys()),
                "timestamp": __import__("time").time(),
            }
            console.print(json_module.dumps(result, indent=2))
        else:
            console.print(f"[red]Error: {e}[/red]")
            console.print("\nUse 'tmux-orc context list' to see available contexts")
        return

    if json:
        result = {
            "success": True,
            "role": role,
            "content": content,
            "content_length": len(content),
            "timestamp": __import__("time").time(),
        }
        console.print(json_module.dumps(result, indent=2))
    elif raw:
        console.print(content)
    else:
        md = Markdown(content)
        console.print(Panel(md, title=f"{role.title()} Context", border_style="blue"))


@click.command("list")
@click.option("--json", is_flag=True, help="Output in JSON format")
def list_contexts(json: bool) -> None:
    """List all available context templates.

    <mcp>List available role contexts (no args). Shows all standardized context templates available for agent roles including orchestrator, pm, and specialty roles. Use to discover context options.</mcp>
    """
    contexts = get_available_contexts()

    if not contexts:
        if json:
            result = {
                "success": False,
                "contexts": [],
                "message": "No context files found in tmux_orchestrator/data/contexts/",
                "timestamp": __import__("time").time(),
            }
            console.print(json_module.dumps(result, indent=2))
        else:
            console.print("[yellow]No context files found in tmux_orchestrator/data/contexts/[/yellow]")
        return

    contexts_data = []
    for role, path in contexts.items():
        # Read first meaningful line as description
        content = path.read_text()
        lines = content.strip().split("\n")
        description = next((line.strip() for line in lines if line.strip() and not line.startswith("#")), "")

        contexts_data.append({"role": role, "description": description, "file_path": str(path)})

    if json:
        result = {
            "success": True,
            "contexts": contexts_data,
            "total_contexts": len(contexts_data),
            "timestamp": __import__("time").time(),
        }
        console.print(json_module.dumps(result, indent=2))
    else:
        console.print("\n[bold]Available System Role Contexts:[/bold]\n")

        for context_info in contexts_data:
            console.print(f"  [cyan]{context_info['role']:15}[/cyan] {context_info['description']}")

        console.print("\n[dim]Use 'tmux-orc context show <role>' to view full context[/dim]")
        console.print("\n[bold]Note:[/bold] Other agent types (developer, qa, etc.) should have")
        console.print("custom briefings defined in your team plan documents.")
