"""Agent management commands."""


import click
from rich.console import Console

from .agent_info import get_agent_info
from .agent_status import show_agent_status
from .attach_agent import attach_agent
from .deploy_agent import deploy_agent
from .kill_agent import kill_agent_command
from .kill_all_agents import kill_all_agents_command
from .list_agents import list_all_agents
from .message_agent import message_agent
from .restart_agent import restart_agent_command
from .send_message import send_message

console: Console = Console()

# Re-export for backwards compatibility
__all__ = [
    "agent",  # Main CLI group
]


@click.group()
def agent() -> None:
    """Manage individual agents across tmux sessions.

    The agent command group provides comprehensive management of Claude agents,
    including deployment, messaging, monitoring, and lifecycle operations.

    Examples:
        tmux-orc agent status                    # Show all agent statuses
        tmux-orc agent restart my-project:0     # Restart specific agent
        tmux-orc agent message frontend:1 "Please update the UI"
        tmux-orc agent info backend:2 --json    # Get detailed agent info
        tmux-orc agent kill stuck-session:3     # Terminate unresponsive agent
        tmux-orc agent attach my-app:0          # Attach to agent terminal

    Target Format:
        Most commands accept targets in 'session:window' format (e.g., 'my-project:0')
    """
    pass


# Import command functions and register them
@agent.command()
@click.argument(
    "agent_type",
    type=click.Choice(["frontend", "backend", "testing", "database", "docs", "devops"]),
)
@click.argument("role", type=click.Choice(["developer", "pm", "qa", "reviewer"]))
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def deploy(ctx: click.Context, agent_type: str, role: str, json: bool) -> None:
    """Deploy an individual specialized agent."""
    deploy_agent(ctx, agent_type, role, json)


@agent.command()
@click.argument("target")
@click.argument("message")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def message(ctx: click.Context, target: str, message: str, json: bool) -> None:
    """Send a quick message to a specific agent."""
    message_agent(ctx, target, message, json)


@agent.command()
@click.argument("target")
@click.argument("message")
@click.option("--delay", default=0.5, type=float, help="Delay between operations (0.1-5.0 seconds)")
@click.option("--json", is_flag=True, help="Output results in JSON format")
@click.pass_context
def send(ctx: click.Context, target: str, message: str, delay: float, json: bool) -> None:
    """Send a message to a specific agent with advanced delivery control."""
    send_message(ctx, target, message, delay, json)


@agent.command()
@click.argument("target")
@click.pass_context
def attach(ctx: click.Context, target: str) -> None:
    """Attach to an agent's terminal for direct interaction."""
    attach_agent(ctx, target)


@agent.command()
@click.argument("target")
@click.option("--timeout", default=30, help="Timeout in seconds for agent restart")
@click.option("--force", is_flag=True, help="Force restart even if agent appears healthy")
@click.option("--json", is_flag=True, help="Output results in JSON format")
@click.pass_context
def restart(
    ctx: click.Context,
    target: str,
    timeout: int,
    force: bool,
    json: bool,
) -> None:
    """Restart a specific agent with health monitoring."""
    restart_agent_command(ctx, target, timeout, force, json)


@agent.command()
@click.argument("target", required=False)
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def status(ctx: click.Context, target: str, json: bool) -> None:
    """Show detailed status of all agents across sessions or a specific agent."""
    show_agent_status(ctx, target, json)


@agent.command()
@click.argument("target")
@click.option("--timeout", default=10, help="Grace period in seconds before force kill")
@click.option("--force", is_flag=True, help="Skip graceful shutdown, kill immediately")
@click.option("--json", is_flag=True, help="Output results in JSON format")
@click.pass_context
def kill(
    ctx: click.Context,
    target: str,
    timeout: int,
    force: bool,
    json: bool,
) -> None:
    """Terminate a specific agent gracefully or forcefully."""
    kill_agent_command(ctx, target, timeout, force, json)


@agent.command()
@click.argument("target")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def info(ctx: click.Context, target: str, json: bool) -> None:
    """Get detailed information about a specific agent."""
    get_agent_info(ctx, target, json)


@agent.command(name="list")
@click.option("--session", help="Filter agents by session name")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def list_agents(ctx: click.Context, session: str, json: bool) -> None:
    """List all active agents with filtering options."""
    list_all_agents(ctx, session, json)


@agent.command(name="kill-all")
@click.option("--force", is_flag=True, help="Skip confirmation and force kill all agents")
@click.option("--json", is_flag=True, help="Output results in JSON format")
@click.pass_context
def kill_all(ctx: click.Context, force: bool, json: bool) -> None:
    """Terminate all agents across all sessions."""
    kill_all_agents_command(ctx, force, json)
