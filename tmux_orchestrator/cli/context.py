"""Context commands for standardized agent briefings."""

from pathlib import Path

import click
import pkg_resources  # noqa: E402
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()

try:
    # Try to use package data first
    CONTEXTS_DIR = Path(pkg_resources.resource_filename("tmux_orchestrator", "data/contexts"))
except Exception:
    # Fallback for development
    CONTEXTS_DIR = Path(__file__).parent.parent / "data" / "contexts"


def get_available_contexts() -> dict[str, Path]:
    """Get list of available context files."""
    if not CONTEXTS_DIR.exists():
        return {}

    contexts = {}
    for file in CONTEXTS_DIR.glob("*.md"):
        role = file.stem
        contexts[role] = file

    return contexts


def load_context(role: str) -> str:
    """Load context from file."""
    contexts = get_available_contexts()
    if role not in contexts:
        raise click.ClickException(f"Context '{role}' not found. Available: {', '.join(contexts.keys())}")

    return contexts[role].read_text()


@click.group()
def context() -> None:
    """Provide standardized context briefings for common agent roles.

    These contexts serve as starting points that can be extended with
    project-specific details when spawning agents.

    Examples:
        tmux-orc context orc             # Show orchestrator briefing
        tmux-orc context pm              # Show PM briefing
        tmux-orc context list            # List all available contexts
    """
    pass


@context.command()
@click.argument("role")
@click.option("--raw", is_flag=True, help="Output raw markdown without formatting")
@click.option("--json", is_flag=True, help="Output in JSON format")
def show(role: str, raw: bool, json: bool) -> None:
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
            import json as json_module

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
        import json as json_module

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


@context.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
def list(json: bool) -> None:
    """List all available context templates.

    <mcp>List available role contexts (no args). Shows all standardized context templates available for agent roles including orchestrator, pm, and specialty roles. Use to discover context options.</mcp>
    """
    contexts = get_available_contexts()

    if not contexts:
        if json:
            import json as json_module

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
        import json as json_module

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


@context.command()
@click.argument("role")
@click.option("--session", required=True, help="Target session name or session:window (legacy)")
@click.option("--extend", help="Additional project-specific context")
@click.option("--json", is_flag=True, help="Output in JSON format")
def spawn(role: str, session: str, extend: str | None = None, json: bool = False) -> None:
    """Spawn an agent with standardized context (orc/pm only).

    <mcp>Create agent with standard role context (args: [role, session], options: --extend). Creates complete agent with standardized orchestrator/pm context plus optional project-specific extensions. For other roles use spawn.agent with custom briefings.</mcp>

    This command creates a complete agent setup:
    1. Creates a new window at the end of the session
    2. Starts Claude with appropriate permissions
    3. Waits for initialization
    4. Sends the role context

    For other agent types, use custom briefings from your team plan.

    Examples:
        tmux-orc context spawn pm --session project
        tmux-orc context spawn orc --session main --extend "Working on API project"
        tmux-orc context spawn pm --session project:1  # Legacy format (index ignored)
    """
    import subprocess
    import time

    from tmux_orchestrator.utils.tmux import TMUXManager

    try:
        load_context(role)
    except click.ClickException as e:
        if json:
            import json as json_module

            result = {
                "success": False,
                "error": str(e),
                "error_type": "ContextNotFound",
                "available_roles": list(get_available_contexts().keys()),
            }
            console.print(json_module.dumps(result, indent=2))
            return
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Note:[/yellow] Only system roles (orc, pm) have standard contexts.")
        console.print("Other agents should be spawned with custom briefings from your team plan.")
        return

    tmux = TMUXManager()

    # Parse session - now accepting session name only or session:window (for compatibility)
    if ":" in session:
        # Legacy format with window index - we'll ignore the index
        session_name, _ = session.split(":", 1)
        if not json:
            console.print(
                f"[yellow]Note: Window index in '{session}' will be ignored. New window will be added to end of session.[/yellow]"
            )
    else:
        # New format - just session name
        session_name = session

    # Check if session exists, create if needed
    sessions = tmux.list_sessions()
    session_created = False
    if not any(s["name"] == session_name for s in sessions):
        if not json:
            console.print(f"[yellow]Creating new session: {session_name}[/yellow]")
        subprocess.run(["tmux", "new-session", "-d", "-s", session_name], check=True)
        session_created = True

    # Create window with appropriate name (always append to end)
    window_name = f"Claude-{role}"
    try:
        # Create new window at the end of the session
        subprocess.run(["tmux", "new-window", "-t", session_name, "-n", window_name], check=True)

        # Get the actual window index that was created
        windows = tmux.list_windows(session_name)
        actual_window_idx = None
        for window in windows:
            if window["name"] == window_name:
                actual_window_idx = window["index"]
                break

        if actual_window_idx is None:
            if json:
                import json as json_module

                result = {"success": False, "error": "Window created but not found", "error_type": "WindowNotFound"}
                console.print(json_module.dumps(result, indent=2))
                return
            console.print("[red]Error: Window created but not found[/red]")
            return

        actual_target = f"{session_name}:{actual_window_idx}"
        if not json:
            console.print(f"[green]Created window: {actual_target} ({window_name})[/green]")
    except subprocess.CalledProcessError as e:
        if json:
            import json as json_module

            result = {"success": False, "error": f"Error creating window: {e}", "error_type": "WindowCreationError"}
            console.print(json_module.dumps(result, indent=2))
            return
        console.print(f"[red]Error creating window: {e}[/red]")
        return

    # Start Claude in the window
    if not json:
        console.print(f"[blue]Starting Claude in {actual_target}...[/blue]")
    tmux.send_keys(actual_target, "claude --dangerously-skip-permissions", literal=True)
    tmux.send_keys(actual_target, "Enter")

    # Wait for Claude to initialize
    if not json:
        console.print("[dim]Waiting for Claude to initialize...[/dim]")
    time.sleep(8)

    # Send instruction message instead of full context
    if role == "pm":
        message = (
            "You're the PM for our team, please run 'tmux-orc context show pm' for more information about your role\n\n"
            "## Context Rehydration\n"
            "If you experience compaction or memory issues, you can rehydrate your context at any time by running:\n"
            "```bash\n"
            "tmux-orc context show pm\n"
            "```\n"
            "This will reload your complete PM role context and restore your capabilities."
        )
    elif role == "orc":
        message = (
            "You're the orchestrator for our team, please run 'tmux-orc context show orc' for more information about your role\n\n"
            "## Context Rehydration\n"
            "If you experience compaction or memory issues, you can rehydrate your context at any time by running:\n"
            "```bash\n"
            "tmux-orc context show orc\n"
            "```\n"
            "This will reload your complete orchestrator role context and restore your capabilities."
        )
    else:
        message = (
            f"You're the {role} for our team, please run 'tmux-orc context show {role}' for more information about your role\n\n"
            "## Context Rehydration\n"
            f"If you experience compaction or memory issues, you can rehydrate your context at any time by running:\n"
            "```bash\n"
            f"tmux-orc context show {role}\n"
            "```\n"
            "This will reload your complete role context and restore your capabilities."
        )

    # Add MCP guidance
    message += """

## MCP Tool Access

The tmux-orchestrator provides 92 auto-generated MCP tools through Claude Code's MCP integration.

**For complete MCP guidance, run:**
```bash
tmux-orc context show mcp
```

This will show you:
- How to use MCP tools effectively
- Complete reference for all 92 tools
- Friendly tutorial for getting started
- Integration with Claude Code

Quick overview of tool categories:
- **agent** - Agent lifecycle management (deploy, kill, list, status, restart, etc.)
- **monitor** - Daemon monitoring and health checks (start, stop, dashboard, recovery, etc.)
- **team** - Team coordination (deploy, status, broadcast, recover, etc.)
- **spawn** - Create new agents (agent, pm, orchestrator)
- **context** - Access role contexts and documentation

To check if MCP tools are available, look for the tools icon in Claude Code's interface. If not available, you can still use all features via the standard CLI commands."""

    # Add extension if provided
    if extend:
        message += f"\n\n## Additional Instructions\n\n{extend}"

    if not json:
        console.print(f"[blue]Sending {role} instruction...[/blue]")
    success = tmux.send_message(actual_target, message)

    if json:
        import json as json_module
        import time

        result = {
            "success": success,
            "role": role,
            "target": actual_target,
            "window_name": window_name,
            "session_created": session_created,
            "claude_started": True,
            "context_sent": success,
            "extend": extend,
            "timestamp": time.time(),
        }
        console.print(json_module.dumps(result, indent=2))
    else:
        if success:
            console.print(f"[green]✓ Successfully spawned {role} agent at {actual_target}[/green]")
            console.print(f"  Window name: {window_name}")
            console.print("  Claude started: Yes")
            console.print("  Context sent: Yes")
        else:
            console.print(f"[red]✗ Failed to send context to {role} agent[/red]")
            console.print("[yellow]Claude may have started but context sending failed[/yellow]")


@context.command()
@click.argument("output_file", type=click.Path())
@click.option("--role", required=True, help="System role (orchestrator/pm) to export")
@click.option("--project", help="Project name for customization")
@click.option("--json", is_flag=True, help="Output in JSON format")
def export(output_file: str, role: str, project: str | None = None, json: bool = False) -> None:
    """Export a system role context to a file for customization.

    <mcp>Export role context to file for customization (args: [output_file, --role], options: --project). Exports standardized context template to file for project-specific customization. Use to create custom agent briefings based on standard roles.</mcp>

    Only orchestrator and PM have standard contexts. All other agents
    (developers, writers, engineers, artists, etc.) should have custom
    briefings defined in your team plan.

    Examples:
        tmux-orc context export my-pm-briefing.md --role pm
        tmux-orc context export orchestrator-api.md --role orchestrator --project "API Service"
    """
    import time

    start_time = time.time()

    try:
        content = load_context(role)
    except click.ClickException as e:
        if json:
            import json as json_module

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
        import json as json_module

        console.print(json_module.dumps(result_data, indent=2))
    else:
        if success:
            console.print(f"[green]✓ Exported {role} context to {output_file}[/green]")
        else:
            console.print(f"[red]✗ Failed to export context: {error_message}[/red]")
