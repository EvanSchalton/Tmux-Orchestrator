"""Spawn command group for creating orchestrators, PMs, and agents."""

from pathlib import Path

import click
from rich.console import Console

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


@click.group()
def spawn() -> None:
    """Spawn orchestrators, project managers, and custom agents.

    This is the primary entry point for creating Claude agents in tmux sessions.
    Use these commands to spawn various types of agents with appropriate contexts
    and configurations. New windows are automatically added to the end of sessions.

    Examples:
        tmux-orc spawn orc                      # Spawn orchestrator (human entry point)
        tmux-orc spawn pm --session proj        # Spawn PM with standard context
        tmux-orc spawn agent api-dev proj --briefing "..."  # Custom agent

    Agent Types:
        - orc: Orchestrator for human interaction (launches new terminal)
        - pm: Project Manager with standardized context
        - agent: Custom agents with flexible briefings
    """
    pass


@spawn.command()
@click.option("--profile", help="Claude Code profile to use (defaults to system default)")
@click.option(
    "--terminal", default="auto", help="Terminal to use: auto, gnome-terminal, konsole, xterm, screen, tmux, etc."
)
@click.option("--no-launch", is_flag=True, help="Create config but don't launch terminal")
@click.option("--no-gui", is_flag=True, help="Run in current terminal (for SSH/bash environments)")
@click.option("--extend", help="Additional project-specific context (deprecated, use --briefing)")
@click.option("--briefing", help="Additional project-specific context")
@click.pass_context
def orc(
    ctx: click.Context,
    profile: str | None,
    terminal: str,
    no_launch: bool,
    no_gui: bool,
    extend: str | None,
    briefing: str | None,
) -> None:
    """Launch Claude Code as an orchestrator in a new terminal.

    <mcp>Create system orchestrator agent (human entry point). Launches new terminal with Claude Code and auto-loads orchestrator context. Context rehydration: Automatically applies orchestrator role context including planning workflows, team coordination patterns, and human interface responsibilities. Use for human-driven project initialization.</mcp>

    This is the primary entry point for humans to start working with tmux-orchestrator.
    It will:
    1. Create a new terminal window
    2. Launch Claude Code with the --dangerously-skip-permissions flag
    3. Automatically load the orchestrator context

    After launching, you'll be ready to create feature requests and use /create-prd
    to generate PRDs that will spawn autonomous agent teams.

    Examples:
        tmux-orc spawn orc                      # Launch with auto-detected terminal
        tmux-orc spawn orc --terminal konsole   # Use specific terminal
        tmux-orc spawn orc --no-gui             # Run in current terminal (SSH)
        tmux-orc spawn orc --profile work       # Use specific Claude profile
        tmux-orc spawn orc --briefing "Working on API refactoring"   # With project context
        tmux-orc spawn orc --extend "Working on API refactoring"     # Deprecated, use --briefing
    """
    # Import the implementation from spawn_orc
    from tmux_orchestrator.cli.spawn_orc import spawn_orc

    # Handle deprecated --extend flag
    context_text = briefing or extend

    # Call the existing implementation
    ctx.invoke(spawn_orc, profile=profile, terminal=terminal, no_launch=no_launch, no_gui=no_gui, extend=context_text)


@spawn.command()
@click.option("--session", required=True, help="Target session name or session:window (legacy)")
@click.option("--extend", help="Additional project-specific context (deprecated, use --briefing)")
@click.option("--briefing", help="Additional project-specific context")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def pm(
    ctx: click.Context, session: str, extend: str | None = None, briefing: str | None = None, json: bool = False
) -> None:
    """Spawn a Project Manager with standardized context.

    <mcp>Create new Project Manager agent with standardized PM context (args: [session]). Context rehydration: Automatically applies PM role context including quality-focused coordination, team management patterns, task distribution workflows, and status reporting. Optional --extend for project-specific context. Creates new window at session end.</mcp>

    This command creates a complete PM agent setup:
    1. Creates a new window at the end of the session
    2. Starts Claude with appropriate permissions
    3. Waits for initialization
    4. Sends the PM context

    The PM will receive the standard PM context from the system contexts,
    which includes quality-focused coordination guidelines and workflow patterns.

    Examples:
        tmux-orc spawn pm --session project
        tmux-orc spawn pm --session main --briefing "Working on API refactoring"
        tmux-orc spawn pm --session main --extend "Working on API refactoring"   # Deprecated
        tmux-orc spawn pm --session project:1  # Legacy format (index ignored)
    """
    # Import context functionality
    from tmux_orchestrator.cli.context import spawn as context_spawn

    # Handle deprecated --extend flag
    context_text = briefing or extend

    # Call the existing implementation
    ctx.invoke(context_spawn, role="pm", session=session, extend=context_text, json=json)


@spawn.command()
@click.argument("name")
@click.argument("target")
@click.option("--briefing", required=True, help="Agent briefing/system prompt")
@click.option("--working-dir", help="Working directory for the agent")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def agent(
    ctx: click.Context, name: str, target: str, briefing: str, working_dir: str | None = None, json: bool = False
) -> None:
    """Spawn a custom agent into a specific session.

    <mcp>Create new custom agent with specialized role and briefing (args: [name, target, --briefing]). Context rehydration: Applies custom briefing as system prompt along with base agent context including tmux-orchestrator awareness, communication protocols, and collaborative workflows. Use --working-dir for workspace context. Creates new window at session end. Correct choice for 'deploy agent' requests.</mcp>

    This command creates a new Claude agent with complete customization.
    Allows ANY agent name and custom system prompts for maximum flexibility.
    The new window will be automatically added to the end of the session.

    NAME: Custom agent name (e.g., 'api-specialist', 'ui-architect')
    TARGET: Target session name (e.g., 'myproject') or session:window for legacy compatibility

    Examples:
        # Spawn a custom API specialist (recommended)
        tmux-orc spawn agent api-specialist myproject \\
            --briefing "You are an API design specialist focused on RESTful principles..."

        # Spawn a performance engineer
        tmux-orc spawn agent perf-engineer backend \\
            --working-dir /workspaces/backend \\
            --briefing "You are a performance optimization engineer..."

        # Legacy format (window index will be ignored)
        tmux-orc spawn agent researcher project:4 \\
            --briefing "$(cat .tmux_orchestrator/planning/researcher-briefing.md)"

    The orc typically uses this command to create custom agents
    tailored to specific project needs, as defined in the team composition plan.
    """
    import time

    tmux: TMUXManager = ctx.obj["tmux"] if ctx.obj and "tmux" in ctx.obj else TMUXManager()

    # Parse target - now accepting session name only or session:window (for compatibility)
    if ":" in target:
        # Legacy format with window index - we'll ignore the index
        session_name, _ = target.split(":", 1)
        console.print(
            f"[yellow]Note: Window index in '{target}' will be ignored. New window will be added to end of session.[/yellow]"
        )
    else:
        # New format - just session name
        session_name = target

    # Validate working directory if provided
    if working_dir:
        working_path = Path(working_dir)
        if not working_path.exists():
            error_msg = f"Working directory '{working_dir}' does not exist"
            if json:
                import json as json_module

                result = {"success": False, "name": name, "target": target, "error": error_msg}
                console.print(json_module.dumps(result, indent=2))
                return
            console.print(f"[red]✗ {error_msg}[/red]")
            raise click.Abort()
        if not working_path.is_dir():
            error_msg = f"Working directory '{working_dir}' is not a directory"
            if json:
                import json as json_module

                result = {"success": False, "name": name, "target": target, "error": error_msg}
                console.print(json_module.dumps(result, indent=2))
                return
            console.print(f"[red]✗ {error_msg}[/red]")
            raise click.Abort()

    # Check if session exists
    if not tmux.has_session(session_name):
        # Create new session
        if not tmux.create_session(session_name):
            error_msg = f"Failed to create session '{session_name}'"
            if json:
                import json as json_module

                result = {
                    "success": False,
                    "name": name,
                    "target": target,
                    "error": error_msg,
                }
                console.print(json_module.dumps(result, indent=2))
                return
            console.print(f"[red]✗ {error_msg}[/red]")
            raise click.Abort()

    # Check for duplicate roles in the session
    existing_windows = tmux.list_windows(session_name)

    for window in existing_windows:
        window_name = window.get("name", "").lower()
        name_lower = name.lower()

        # Check for role conflicts (case-insensitive)
        role_conflicts = [
            (name_lower in window_name or window_name in name_lower) and len(name_lower) > 2,
            # Specific role aliases
            (
                name_lower in ["pm", "manager", "project-manager"]
                and any(pm in window_name for pm in ["pm", "manager", "project"])
            ),
            (name_lower in ["dev", "developer", "engineer"] and any(dev in window_name for dev in ["dev", "engineer"])),
            (
                name_lower in ["qa", "tester", "test", "quality", "testing", "qa-engineer", "test-engineer"]
                and any(qa in window_name for qa in ["qa", "tester", "testing", "quality"])
            ),
            (
                name_lower in ["devops", "ops", "deploy"]
                and any(ops in window_name for ops in ["devops", "ops", "deploy"])
            ),
            (name_lower in ["reviewer", "review", "code-review"] and any(rev in window_name for rev in ["review"])),
        ]

        if any(role_conflicts):
            error_msg = (
                f"Role conflict: '{name}' conflicts with existing window '{window['name']}' in session '{session_name}'"
            )
            if json:
                import json as json_module

                result = {
                    "success": False,
                    "name": name,
                    "target": target,
                    "error": error_msg,
                    "conflict_window": f"{session_name}:{window['index']}",
                    "validation_failed": "duplicate_role",
                }
                console.print(json_module.dumps(result, indent=2))
                return
            console.print(f"[red]✗ {error_msg}[/red]")
            console.print(f"[yellow]Existing window: {session_name}:{window['index']} - {window['name']}[/yellow]")
            console.print("[dim]Each role should have only ONE agent per session[/dim]")
            raise click.Abort()

    # Create window with custom name
    window_name = f"Claude-{name}"
    success = tmux.create_window(session_name, window_name, working_dir)

    if not success:
        error_msg = "Failed to create window"
        if json:
            import json as json_module

            result = {
                "success": False,
                "name": name,
                "target": target,
                "error": error_msg,
            }
            console.print(json_module.dumps(result, indent=2))
            return
        console.print(f"[red]✗ {error_msg}[/red]")
        raise click.Abort()

    # Get the actual window index (might differ from requested)
    windows = tmux.list_windows(session_name)
    actual_window_idx = None
    for window in windows:
        if window["name"] == window_name:
            actual_window_idx = window["index"]
            break

    if actual_window_idx is None:
        error_msg = "Window created but not found"
        if json:
            import json as json_module

            result = {
                "success": False,
                "name": name,
                "target": target,
                "error": error_msg,
            }
            console.print(json_module.dumps(result, indent=2))
            return
        console.print(f"[red]✗ {error_msg}[/red]")
        raise click.Abort()

    # Start Claude in the new window
    actual_target = f"{session_name}:{actual_window_idx}"
    tmux.send_text(actual_target, "claude --dangerously-skip-permissions")
    tmux.send_keys(actual_target, "Enter")

    # CRITICAL: Wait for Claude to fully initialize to prevent Ctrl+C interruption
    time.sleep(8)  # Give Claude sufficient time to load completely

    # Prepare enhanced briefing with MCP guidance
    enhanced_briefing = (
        briefing
        + """

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
    )

    # Send enhanced briefing
    tmux.send_message(actual_target, enhanced_briefing)

    # Prepare result
    result_data = {
        "success": True,
        "name": name,
        "target": actual_target,
        "window_name": window_name,
        "briefing_sent": True,
    }

    if json:
        import json as json_module

        console.print(json_module.dumps(result_data, indent=2))
    else:
        console.print(f"[green]✓ Spawned custom agent '{name}' at {actual_target}[/green]")
        console.print(f"  Window name: {window_name}")
        console.print("  Custom briefing: ✓ Sent")
        if working_dir:
            console.print(f"  Working directory: {working_dir}")


if __name__ == "__main__":
    spawn()
