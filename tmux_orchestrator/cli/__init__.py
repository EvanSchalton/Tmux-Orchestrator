"""TMUX Orchestrator CLI - AI-powered tmux session management."""

from pathlib import Path
from typing import Dict, Optional

import click
from rich.console import Console
from rich.table import Table

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

# Initialize console for CLI output
console: Console = Console()


@click.group(name="tmux-orc")
@click.version_option(version="2.0.0", prog_name="tmux-orc")
@click.option(
    "--config-file",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
    envvar="TMUX_ORC_CONFIG"
)
@click.option(
    "--json",
    is_flag=True,
    help="Output in JSON format for scripting"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.pass_context
def cli(ctx: click.Context, config_file: Optional[str], json: bool, verbose: bool) -> None:
    """TMUX Orchestrator - AI-powered tmux session management.

    The TMUX Orchestrator enables autonomous AI agents to collaborate in tmux sessions,
    providing intelligent session management, automatic recovery, and seamless monitoring.

    Examples:
        tmux-orc team deploy frontend 3          # Deploy 3-agent frontend team
        tmux-orc agent restart session:0         # Restart specific agent
        tmux-orc monitor start --interval 15     # Start monitoring daemon
        tmux-orc setup-vscode ./my-project       # Setup VS Code integration

    For detailed command help, use: tmux-orc COMMAND --help
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Initialize configuration
    try:
        ctx.obj['config'] = Config.load(config_file) if config_file else Config.load()
    except Exception as e:
        if verbose:
            console.print(f"[red]Configuration error: {e}[/red]")
        ctx.obj['config'] = Config()  # Use defaults

    # Initialize TMUX manager
    ctx.obj['tmux'] = TMUXManager()
    ctx.obj['console'] = console
    ctx.obj['json_mode'] = json
    ctx.obj['verbose'] = verbose


# Top-level quick commands
@cli.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def list(ctx: click.Context, json: bool) -> None:
    """List all active agents across sessions.

    Displays a comprehensive overview of all Claude agents currently running
    in tmux sessions, including their status and session information.

    Examples:
        tmux-orc list                    # Show agent table
        tmux-orc list --json            # JSON output for scripts
    """
    tmux: TMUXManager = ctx.obj['tmux']
    use_json: bool = json or ctx.obj.get('json_mode', False)

    agents = tmux.list_agents()

    if use_json:
        import json as json_module
        console.print(json_module.dumps(agents, indent=2))
        return

    if not agents:
        console.print("[yellow]No active agents found.[/yellow]")
        console.print("\nTo deploy agents, use: [bold]tmux-orc team deploy[/bold]")
        return

    table = Table(title=f"Active Agents ({len(agents)} total)")
    table.add_column("Session", style="cyan", width=12)
    table.add_column("Window", style="magenta", width=8)
    table.add_column("Type", style="green", width=15)
    table.add_column("Status", style="yellow", width=12)

    for agent in agents:
        table.add_row(
            agent['session'],
            str(agent['window']),
            agent['type'],
            agent['status']
        )

    console.print(table)
    console.print("\nUse [bold]tmux-orc agent status[/bold] for detailed information")


@cli.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def status(ctx: click.Context, json: bool) -> None:
    """Show comprehensive system status dashboard.

    Displays detailed information about all tmux sessions, agents, and
    the overall health of the orchestrator system.

    Examples:
        tmux-orc status                  # Show status dashboard
        tmux-orc status --json          # JSON output for monitoring
    """
    tmux: TMUXManager = ctx.obj['tmux']
    use_json: bool = json or ctx.obj.get('json_mode', False)

    # Gather system information
    sessions = tmux.list_sessions()
    agents = tmux.list_agents()

    if use_json:
        import json as json_module
        status_data = {
            "sessions": sessions,
            "agents": agents,
            "summary": {
                "total_sessions": len(sessions),
                "total_agents": len(agents),
                "active_agents": len([a for a in agents if a['status'] == 'Active'])
            }
        }
        console.print(json_module.dumps(status_data, indent=2))
        return

    # Display rich status dashboard
    console.print("\n[bold blue]TMUX Orchestrator System Status[/bold blue]")
    console.print("=" * 50)

    # Sessions summary
    if sessions:
        console.print(f"\n[bold]Sessions ({len(sessions)} active):[/bold]")
        for session in sessions[:5]:  # Show top 5
            attached = "✓" if session.get('attached') == '1' else "○"
            console.print(f"  {attached} {session['name']}")
        if len(sessions) > 5:
            console.print(f"  ... and {len(sessions) - 5} more sessions")
    else:
        console.print("\n[yellow]No active sessions found[/yellow]")

    # Agents summary
    if agents:
        console.print(f"\n[bold]Agents ({len(agents)} active):[/bold]")
        status_counts: Dict[str, int] = {}
        for agent in agents:
            status_counts[agent['status']] = status_counts.get(agent['status'], 0) + 1

        for status, count in status_counts.items():
            color = "green" if status == "Active" else "yellow" if status == "Idle" else "red"
            console.print(f"  [{color}]{status}: {count}[/{color}]")
    else:
        console.print("\n[yellow]No active agents found[/yellow]")

    console.print("\nUse [bold]tmux-orc team status <session>[/bold] for detailed team info")


@cli.command("quick-deploy")
@click.argument("team_type", type=click.Choice(['frontend', 'backend', 'fullstack', 'testing']))
@click.argument("size", type=int, default=3)
@click.option("--project-name", help="Project name (defaults to current directory)")
@click.pass_context
def quick_deploy(ctx: click.Context, team_type: str, size: int, project_name: Optional[str]) -> None:
    """Quickly deploy a standard team configuration.

    Deploys a predefined team with the specified type and size.
    This is a convenience command for common team configurations.

    Examples:
        tmux-orc quick-deploy frontend 3        # 3-agent frontend team
        tmux-orc quick-deploy fullstack 5       # 5-agent fullstack team
        tmux-orc quick-deploy testing 2         # 2-agent testing team
    """
    from tmux_orchestrator.core.team_operations.deploy_team import deploy_standard_team

    if not project_name:
        project_name = Path.cwd().name

    console.print(f"[blue]Deploying {team_type} team with {size} agents...[/blue]")

    # Delegate to business logic
    success, message = deploy_standard_team(
        ctx.obj['tmux'],
        team_type,
        size,
        project_name
    )

    if success:
        console.print(f"[green]✓ {message}[/green]")
    else:
        console.print(f"[red]✗ {message}[/red]")


def _setup_command_groups() -> None:
    """Set up command groups - called at module load time."""
    try:
        # Import command groups (with error handling for missing modules)
        from tmux_orchestrator.cli import agent, monitor, pm

        # Add core command groups
        cli.add_command(agent.agent)
        cli.add_command(monitor.monitor)
        cli.add_command(pm.pm)

        # Add team commands (may not exist yet)
        try:
            from tmux_orchestrator.cli import team
            cli.add_command(team.team)
        except ImportError:
            pass  # team.py module will be created in Task 2.3

        # Add orchestrator commands (may not exist yet)
        try:
            from tmux_orchestrator.cli import orchestrator
            cli.add_command(orchestrator.orchestrator)
        except ImportError:
            pass  # orchestrator.py module will be created in Task 2.4

        # Add setup commands (may not exist yet)
        try:
            from tmux_orchestrator.cli import setup
            cli.add_command(setup.setup)
        except ImportError:
            pass  # setup.py module will be created in Task 2.5

    except ImportError as e:
        # Handle missing modules gracefully during development
        console.print(f"[yellow]Warning: Some CLI modules not available: {e}[/yellow]")


# Set up command groups when module is imported
_setup_command_groups()


if __name__ == '__main__':
    cli()
