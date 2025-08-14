"""Spawn command group for creating orchestrators, PMs, and agents."""

import re
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
    and configurations.

    Examples:
        tmux-orc spawn orc                    # Spawn orchestrator (human entry point)
        tmux-orc spawn pm --session proj:1    # Spawn PM with standard context
        tmux-orc spawn agent api-dev proj:2 --briefing "..."  # Custom agent

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
@click.pass_context
def orc(ctx: click.Context, profile: str | None, terminal: str, no_launch: bool, no_gui: bool) -> None:
    """Launch Claude Code as an orchestrator in a new terminal.

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
    """
    # Import the implementation from spawn_orc
    from tmux_orchestrator.cli.spawn_orc import spawn_orc

    # Call the existing implementation
    ctx.invoke(spawn_orc, profile=profile, terminal=terminal, no_launch=no_launch, no_gui=no_gui)


@spawn.command()
@click.option("--session", required=True, help="Target session:window")
@click.option("--extend", help="Additional project-specific context")
@click.pass_context
def pm(ctx: click.Context, session: str, extend: str | None = None) -> None:
    """Spawn a Project Manager with standardized context.

    This command creates a complete PM agent setup:
    1. Creates the window if needed
    2. Starts Claude with appropriate permissions
    3. Waits for initialization
    4. Sends the PM context

    The PM will receive the standard PM context from the system contexts,
    which includes quality-focused coordination guidelines and workflow patterns.

    Examples:
        tmux-orc spawn pm --session project:1
        tmux-orc spawn pm --session main:0 --extend "Working on API refactoring"
    """
    # Import context functionality
    from tmux_orchestrator.cli.context import spawn as context_spawn

    # Call the existing implementation
    ctx.invoke(context_spawn, name="pm", session=session, extend=extend)


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
    """Spawn a custom agent into a specific session and window.

    This command creates a new Claude agent with complete customization.
    Allows ANY agent name and custom system prompts for maximum flexibility.

    NAME: Custom agent name (e.g., 'api-specialist', 'ui-architect')
    TARGET: Target location in format session:window (e.g., 'myproject:3')

    Examples:
        # Spawn a custom API specialist
        tmux-orc spawn agent api-specialist myproject:2 \\
            --briefing "You are an API design specialist focused on RESTful principles..."

        # Spawn a performance engineer
        tmux-orc spawn agent perf-engineer backend:3 \\
            --working-dir /workspaces/backend \\
            --briefing "You are a performance optimization engineer..."

        # Spawn from a briefing file
        tmux-orc spawn agent researcher project:4 \\
            --briefing "$(cat .tmux_orchestrator/planning/researcher-briefing.md)"

    The orchestrator typically uses this command to create custom agents
    tailored to specific project needs, as defined in the team composition plan.
    """
    # Import agent spawn functionality
    from tmux_orchestrator.cli.agent import spawn as agent_spawn

    # Validate target format
    if not re.match(r"^[^:]+:\d+$", target):
        error_msg = f"Invalid target format '{target}'. Use session:window (e.g., 'myproject:3')"
        if json:
            import json as json_module

            result = {"success": False, "name": name, "target": target, "error": error_msg}
            console.print(json_module.dumps(result, indent=2))
            return
        console.print(f"[red]✗ {error_msg}[/red]")
        raise click.Abort()

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

    # Ensure context has tmux manager
    if ctx.obj is None:
        ctx.obj = {}
    if "tmux" not in ctx.obj:
        ctx.obj["tmux"] = TMUXManager()

    try:
        # Call the existing implementation using Click's invoke
        ctx.invoke(
            agent_spawn,
            name=name,
            target=target,
            briefing=briefing,
            working_dir=working_dir or str(Path.cwd()),
            json=json,
        )
    except Exception as e:
        if json:
            import json as json_module

            result = {"success": False, "name": name, "target": target, "error": str(e)}
            console.print(json_module.dumps(result, indent=2))
        else:
            console.print(f"[red]✗ Failed to spawn agent: {str(e)}[/red]")
        raise click.Abort()


if __name__ == "__main__":
    spawn()
