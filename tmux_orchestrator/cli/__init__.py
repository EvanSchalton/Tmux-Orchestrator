"""TMUX Orchestrator CLI - AI-powered tmux session management."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from tmux_orchestrator import __version__
from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

# Initialize console for CLI output
console: Console = Console()


@click.group(name="tmux-orc")
@click.version_option(version=__version__, prog_name="tmux-orc")
@click.option(
    "--config-file",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
    envvar="TMUX_ORC_CONFIG",
)
@click.option("--json", is_flag=True, help="Output in JSON format for scripting")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, config_file: str | None, json: bool, verbose: bool) -> None:
    """TMUX Orchestrator - AI-powered tmux session management.

    The TMUX Orchestrator enables autonomous AI agents to collaborate in tmux sessions,
    providing intelligent session management, automatic recovery, and seamless monitoring.

    Examples:
        tmux-orc team deploy frontend 3          # Deploy 3-agent frontend team
        tmux-orc agent restart session:0         # Restart specific agent
        tmux-orc monitor start --interval 15     # Start monitoring daemon
        tmux-orc setup vscode ./my-project       # Setup VS Code integration

    For detailed command help, use: tmux-orc COMMAND --help
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Initialize configuration
    try:
        ctx.obj["config"] = Config.load(Path(config_file) if config_file else None)
    except Exception as e:
        if verbose:
            console.print(f"[red]Configuration error: {e}[/red]")
        ctx.obj["config"] = Config()  # Use defaults

    # Initialize TMUX manager
    ctx.obj["tmux"] = TMUXManager()
    ctx.obj["console"] = console
    ctx.obj["json_mode"] = json
    ctx.obj["verbose"] = verbose


# Top-level quick commands
@cli.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def list(ctx: click.Context, json: bool) -> None:
    """List all active agents across sessions with comprehensive status.

    Provides a system-wide overview of all Claude agents currently running
    in tmux sessions, including their specializations, health status, and
    recent activity patterns.

    Examples:
        tmux-orc list                    # Show formatted agent overview
        tmux-orc list --json            # JSON output for scripts/monitoring

    Agent Information Displayed:
        • Session name and window location
        • Agent type and specialization
        • Current status (Active, Idle, Busy, Error)
        • Last activity timestamp
        • Response time and health metrics

    Status Indicators:
        🟢 Active:  Agent is responsive and working
        🟡 Idle:    Agent is waiting for tasks
        🔵 Busy:    Agent is processing complex work
        🔴 Error:   Agent encountered issues
        ⚫ Unknown: Status cannot be determined

    Use Cases:
        • System health monitoring
        • Resource utilization assessment
        • Identifying unresponsive agents
        • Planning team deployments
        • Integration with monitoring tools (JSON)

    If no agents are found, provides guidance on deploying teams.
    """
    tmux: TMUXManager = ctx.obj["tmux"]
    use_json: bool = json or ctx.obj.get("json_mode", False)

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
        table.add_row(agent["session"], str(agent["window"]), agent["type"], agent["status"])

    console.print(table)
    console.print("\nUse [bold]tmux-orc agent status[/bold] for detailed information")


@cli.command()
@click.option("--format", type=click.Choice(["tree", "json", "markdown"]), default="tree", help="Output format")
@click.option("--include-hidden", is_flag=True, help="Include hidden commands")
@click.pass_context
def reflect(ctx: click.Context, format: str, include_hidden: bool) -> None:
    """Generate complete CLI command structure via introspection.

    Examples:
        tmux-orc reflect                     # Tree view of all commands
        tmux-orc reflect --format json      # JSON structure for tools
        tmux-orc reflect --format markdown  # Markdown documentation
    """
    import json
    import sys

    # Direct output to stdout
    try:
        # Get root CLI group
        root_group = ctx.find_root().command

        # Simple command listing
        if format == "tree":
            sys.stdout.write("tmux-orc CLI Commands:\n")
            sys.stdout.write("=" * 30 + "\n\n")

            for name, command in root_group.commands.items():
                if not include_hidden and getattr(command, "hidden", False):
                    continue

                cmd_type = "📁" if isinstance(command, click.Group) else "⚡"
                help_text = (
                    getattr(command, "short_help", "") or (command.help.split("\n")[0] if command.help else "")
                ).strip()

                sys.stdout.write(f"{cmd_type} {name}")
                if help_text:
                    sys.stdout.write(f" - {help_text}")
                sys.stdout.write("\n")

                # Show subcommands if it's a group
                if isinstance(command, click.Group):
                    for subname, subcmd in command.commands.items():
                        sub_help = (
                            getattr(subcmd, "short_help", "") or (subcmd.help.split("\n")[0] if subcmd.help else "")
                        ).strip()
                        sys.stdout.write(f"  └── {subname}")
                        if sub_help:
                            sys.stdout.write(f" - {sub_help}")
                        sys.stdout.write("\n")

            sys.stdout.write("\n💡 Use 'tmux-orc [COMMAND] --help' for detailed information\n")
            sys.stdout.write("📁 = Command group, ⚡ = Individual command\n")

        elif format == "json":
            # Simple JSON structure
            commands = {}
            for name, command in root_group.commands.items():
                if not include_hidden and getattr(command, "hidden", False):
                    continue
                commands[name] = {
                    "type": "group" if isinstance(command, click.Group) else "command",
                    "help": command.help or "",
                    "short_help": getattr(command, "short_help", "") or "",
                }
            sys.stdout.write(json.dumps(commands, indent=2) + "\n")

        elif format == "markdown":
            sys.stdout.write("# tmux-orc CLI Reference\n\n")
            for name, command in root_group.commands.items():
                if not include_hidden and getattr(command, "hidden", False):
                    continue
                cmd_type = "Group" if isinstance(command, click.Group) else "Command"
                sys.stdout.write(f"## {name} ({cmd_type})\n\n")
                if command.help:
                    sys.stdout.write(f"{command.help}\n\n")

    except Exception as e:
        sys.stdout.write(f"Error generating CLI reflection: {e}\n")


@cli.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def status(ctx: click.Context, json: bool) -> None:
    """Display comprehensive system status dashboard and health overview.

    Provides a high-level view of the entire TMUX Orchestrator ecosystem,
    including all sessions, agents, system health metrics, and operational status.

    Examples:
        tmux-orc status                  # Show interactive status dashboard
        tmux-orc status --json          # JSON output for monitoring systems

    Dashboard Information:
        • Total sessions and attachment status
        • Agent counts by type and status
        • System resource utilization
        • Recent activity patterns
        • Health alerts and warnings
        • Performance metrics

    System Health Indicators:
        🟢 Healthy:   All systems operational
        🟡 Warning:   Minor issues detected
        🔴 Critical:  Major problems requiring attention
        ⚫ Offline:   System not responding

    Monitoring Categories:
        • Session Management: Active sessions and stability
        • Agent Health: Response times and error rates
        • Resource Usage: Memory, CPU, and network utilization
        • Communication: Message delivery and latency
        • Quality Metrics: Task completion and success rates

    Use for regular system health checks, performance monitoring,
    and integration with external monitoring and alerting systems.
    """
    tmux: TMUXManager = ctx.obj["tmux"]
    use_json: bool = json or ctx.obj.get("json_mode", False)

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
                "active_agents": len([a for a in agents if a["status"] == "Active"]),
            },
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
            attached = "✓" if session.get("attached") == "1" else "○"
            console.print(f"  {attached} {session['name']}")
        if len(sessions) > 5:
            console.print(f"  ... and {len(sessions) - 5} more sessions")
    else:
        console.print("\n[yellow]No active sessions found[/yellow]")

    # Agents summary
    if agents:
        console.print(f"\n[bold]Agents ({len(agents)} active):[/bold]")
        status_counts: dict[str, int] = {}
        for agent in agents:
            status_counts[agent["status"]] = status_counts.get(agent["status"], 0) + 1

        for status, count in status_counts.items():
            color = "green" if status == "Active" else "yellow" if status == "Idle" else "red"
            console.print(f"  [{color}]{status}: {count}[/{color}]")
    else:
        console.print("\n[yellow]No active agents found[/yellow]")

    console.print("\nUse [bold]tmux-orc team status <session>[/bold] for detailed team info")


@cli.command("quick-deploy")
@click.argument("team_type", type=click.Choice(["frontend", "backend", "fullstack", "testing"]))
@click.argument("size", type=int, default=3)
@click.option("--project-name", help="Project name (defaults to current directory)")
@click.pass_context
def quick_deploy(ctx: click.Context, team_type: str, size: int, project_name: str | None) -> None:
    """Rapidly deploy optimized team configurations for immediate productivity.

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

    Quick Deploy Benefits:
        • Instant team setup with optimized roles
        • Pre-configured communication protocols
        • Battle-tested role distributions
        • Immediate project context and briefings
        • No configuration complexity

    Perfect for hackathons, quick prototypes, urgent projects,
    or when you need a team running in under 2 minutes.
    """
    from tmux_orchestrator.core.team_operations.deploy_team import deploy_standard_team

    if not project_name:
        project_name = Path.cwd().name

    console.print(f"[blue]Deploying {team_type} team with {size} agents...[/blue]")

    # Delegate to business logic
    success, message = deploy_standard_team(ctx.obj["tmux"], team_type, size, project_name)

    if success:
        console.print(f"[green]✓ {message}[/green]")
    else:
        console.print(f"[red]✗ {message}[/red]")


def _setup_command_groups() -> None:
    """Set up command groups - called at module load time."""
    try:
        # Import command groups (with error handling for missing modules)
        from tmux_orchestrator.cli import agent, context, monitor, pm

        # Add core command groups
        cli.add_command(agent.agent)
        cli.add_command(monitor.monitor)
        cli.add_command(pm.pm)
        cli.add_command(context.context)

        # Add team commands
        try:
            from tmux_orchestrator.cli import team

            cli.add_command(team.team)
        except ImportError:
            # Try new team compose module
            try:
                from tmux_orchestrator.cli import team_compose

                cli.add_command(team_compose.team)
            except ImportError:
                pass  # team modules not available

        # Add orchestrator commands (may not exist yet)
        try:
            from tmux_orchestrator.cli import orchestrator

            cli.add_command(orchestrator.orchestrator)
        except ImportError:
            pass  # orchestrator.py module will be created in Task 2.4

        # Add setup commands
        try:
            from tmux_orchestrator.cli import setup_claude

            cli.add_command(setup_claude.setup)
        except ImportError:
            pass  # setup_claude.py module for environment setup

        # Add spawn command group
        try:
            from tmux_orchestrator.cli import spawn

            cli.add_command(spawn.spawn)
        except ImportError:
            pass  # spawn.py module for spawning agents

        # Add spawn-orc command for orchestrator launch
        try:
            from tmux_orchestrator.cli import spawn_orc

            cli.add_command(spawn_orc.spawn_orc)
        except ImportError:
            pass  # spawn_orc.py module for orchestrator launch

        # Note: VS Code setup moved to setup_claude.py as 'tmux-orc setup vscode'

        # Add recovery commands
        try:
            from tmux_orchestrator.cli import recovery

            cli.add_command(recovery.recovery)
        except ImportError:
            pass  # recovery.py module for automatic agent recovery

        # Add session commands
        try:
            from tmux_orchestrator.cli import session

            cli.add_command(session.session)
        except ImportError:
            pass  # session.py module for session management

        # Add pubsub commands
        try:
            from tmux_orchestrator.cli import pubsub

            cli.add_command(pubsub.pubsub)
        except ImportError:
            pass  # pubsub.py module for agent communication

        # Add tasks commands
        try:
            from tmux_orchestrator.cli import tasks

            cli.add_command(tasks.tasks)
        except ImportError:
            pass  # tasks.py module for task list management

        # Add execute command
        try:
            from tmux_orchestrator.cli import execute

            cli.add_command(execute.execute)
        except ImportError:
            pass  # execute.py module for PRD execution

        # Add error management commands
        try:
            from tmux_orchestrator.cli import errors

            cli.add_command(errors.errors)
        except ImportError:
            pass  # errors.py module for error management

        # Add MCP server commands
        try:
            from tmux_orchestrator.cli import server

            cli.add_command(server.server)
        except ImportError:
            pass  # server.py module for MCP server management

    except ImportError as e:
        # Handle missing modules gracefully during development
        console.print(f"[yellow]Warning: Some CLI modules not available: {e}[/yellow]")


# Set up command groups when module is imported
_setup_command_groups()


if __name__ == "__main__":
    cli()
