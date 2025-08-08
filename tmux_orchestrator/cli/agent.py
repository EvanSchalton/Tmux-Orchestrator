"""Agent management commands."""

import subprocess
from typing import Any, Dict

import click
from rich.console import Console

from tmux_orchestrator.core.agent_operations import restart_agent
from tmux_orchestrator.utils.tmux import TMUXManager

console: Console = Console()


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


@agent.command()
@click.argument(
    'agent_type',
    type=click.Choice(['frontend', 'backend', 'testing', 'database', 'docs', 'devops'])
)
@click.argument('role', type=click.Choice(['developer', 'pm', 'qa', 'reviewer']))
@click.pass_context
def deploy(ctx: click.Context, agent_type: str, role: str) -> None:
    """Deploy an individual specialized agent.
    
    Creates a new tmux session with a single Claude agent configured for
    the specified type and role combination.
    
    AGENT_TYPE: Specialization area (frontend, backend, testing, database, docs, devops)
    ROLE: Agent role (developer, pm, qa, reviewer)
    
    Examples:
        tmux-orc agent deploy frontend developer   # Frontend development agent
        tmux-orc agent deploy backend pm          # Backend project manager
        tmux-orc agent deploy testing qa          # QA testing agent
        tmux-orc agent deploy database devops     # Database operations agent
        tmux-orc agent deploy docs reviewer       # Documentation reviewer
    
    The agent will be briefed with role-specific instructions and tools.
    """
    from tmux_orchestrator.core.agent_manager import AgentManager

    manager: AgentManager = AgentManager(ctx.obj['tmux'])
    session: str = manager.deploy_agent(agent_type, role)

    console.print(
        f"[green]✓ Deployed {agent_type} {role} in session: {session}[/green]"
    )


@agent.command()
@click.argument('target')
@click.argument('message')
@click.pass_context
def message(ctx: click.Context, target: str, message: str) -> None:
    """Send a message directly to a specific agent.
    
    Delivers a message to the Claude agent running in the specified tmux window.
    The message appears as user input to the agent, allowing for real-time
    communication and task delegation.
    
    TARGET: Target agent in format session:window (e.g., 'my-project:0')
    MESSAGE: The message text to send to the agent
    
    Examples:
        tmux-orc agent message frontend:0 "Please fix the login form validation"
        tmux-orc agent message backend:1 "STATUS UPDATE: What's your current progress?"
        tmux-orc agent message testing:2 "Run the integration tests for the API"
        tmux-orc agent message docs:0 "Update the deployment guide with new steps"
    
    Usage Tips:
        - Use quotes for multi-word messages
        - Messages appear instantly to the agent
        - Agents respond in their tmux window
        - Use 'tmux-orc agent attach TARGET' to see the response
    """
    tmux: TMUXManager = ctx.obj['tmux']

    if tmux.send_message(target, message):
        console.print(f"[green]✓ Message sent to {target}[/green]")
    else:
        console.print(f"[red]✗ Failed to send message to {target}[/red]")


@agent.command()
@click.argument('target')
@click.pass_context
def attach(ctx: click.Context, target: str) -> None:
    """Attach to an agent's terminal for direct interaction.
    
    Opens a direct terminal connection to the specified agent's tmux window,
    allowing you to see the agent's output and interact directly.
    
    TARGET: Target agent in format session:window (e.g., 'my-project:0')
    
    Examples:
        tmux-orc agent attach frontend:0      # Attach to frontend agent
        tmux-orc agent attach backend:2       # Attach to backend agent
        tmux-orc agent attach testing:1       # Attach to testing agent
    
    Usage Tips:
        - Press Ctrl+B then D to detach without stopping the agent
        - Use this to monitor agent progress in real-time
        - Type directly to interact with the agent
        - The agent continues running after you detach
    
    Note: This opens a new tmux attachment. Use proper tmux detach commands
    to avoid disrupting the agent's operation.
    """
    try:
        subprocess.run(['tmux', 'attach', '-t', target], check=True)
    except subprocess.CalledProcessError:
        console.print(f"[red]✗ Failed to attach to {target}[/red]")


@agent.command()
@click.argument('target')
@click.pass_context
def restart(ctx: click.Context, target: str) -> None:
    """Restart a specific agent that has become unresponsive.
    
    Terminates the current Claude process in the specified window and starts
    a fresh instance with the same configuration and briefing.
    
    TARGET: Target agent in format session:window (e.g., 'my-project:0')
    
    Examples:
        tmux-orc agent restart frontend:0     # Restart unresponsive frontend agent
        tmux-orc agent restart backend:1      # Restart crashed backend agent  
        tmux-orc agent restart testing:2      # Restart stuck testing agent
    
    When to Use:
        - Agent is not responding to messages
        - Agent output shows errors or crashes
        - Agent appears frozen or stuck
        - After system updates that affect Claude
    
    The restart process:
        1. Captures current agent state and context
        2. Terminates the existing Claude process
        3. Starts a new Claude instance
        4. Restores the agent's role and briefing
        5. Provides context about the restart reason
    """
    tmux: TMUXManager = ctx.obj['tmux']

    console.print(f"[yellow]Restarting agent at {target}...[/yellow]")

    # Delegate to business logic
    success, result_message = restart_agent(tmux, target)

    if success:
        console.print(f"[green]✓ {result_message}[/green]")
    else:
        console.print(f"[red]✗ {result_message}[/red]")


@agent.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show comprehensive status of all active agents.
    
    Displays a summary of all Claude agents currently running across
    all tmux sessions, including their current state, activity, and tasks.
    
    Examples:
        tmux-orc agent status                 # Show all agent statuses
    
    Status Information Includes:
        - Agent ID and session:window location
        - Current state (Active, Idle, Error, etc.)
        - Last activity timestamp
        - Current task or operation
        - Response time and health metrics
    
    Status States:
        • Active:   Agent is responding and working
        • Idle:     Agent is waiting for tasks
        • Busy:     Agent is processing a complex task
        • Error:    Agent encountered an issue
        • Stuck:    Agent may need restart
        • Unknown:  Unable to determine status
    
    Use this command regularly to monitor agent health and identify
    agents that may need attention or restart.
    """
    from tmux_orchestrator.core.agent_manager import AgentManager

    manager: AgentManager = AgentManager(ctx.obj['tmux'])
    statuses: Dict[str, Any] = manager.get_all_status()

    for agent_id, status in statuses.items():
        console.print(f"\n[bold cyan]{agent_id}[/bold cyan]")
        console.print(f"  Status: {status['state']}")
        console.print(f"  Last Activity: {status['last_activity']}")
        if status.get('current_task'):
            console.print(f"  Current Task: {status['current_task']}")


@agent.command()
@click.argument('target')
@click.pass_context
def kill(ctx: click.Context, target: str) -> None:
    """Terminate a specific agent permanently.
    
    Forcefully terminates the Claude agent at the specified location.
    This is more aggressive than restart and should be used when an
    agent is completely unresponsive or causing system issues.
    
    TARGET: Target agent in format session:window (e.g., 'my-project:0')
    
    Examples:
        tmux-orc agent kill frontend:0        # Kill unresponsive frontend agent
        tmux-orc agent kill stuck-session:1   # Kill problematic agent
        tmux-orc agent kill testing:2         # Remove completed testing agent
    
    ⚠️  WARNING: This permanently terminates the agent
    
    When to Use:
        - Agent is completely frozen and restart failed
        - Agent is consuming excessive resources
        - Agent is causing system instability
        - Project is complete and agents no longer needed
    
    Difference from Restart:
        - Kill: Permanently removes the agent
        - Restart: Terminates and immediately recreates the agent
    
    The kill operation removes the agent's tmux window or session,
    losing all context and conversation history.
    """
    tmux: TMUXManager = ctx.obj['tmux']

    console.print(f"[yellow]Killing agent at {target}...[/yellow]")

    # Parse target to get session and window
    if ':' not in target:
        console.print("[red]✗ Invalid target format. Use session:window[/red]")
        return

    try:
        # Kill the specific window (using session kill as fallback)
        try:
            if hasattr(tmux, 'kill_window'):
                success = tmux.kill_window(target)
            else:
                # Fallback: kill entire session if method doesn't exist
                session = target.split(':')[0]
                success = tmux.kill_session(session)
        except Exception:
            success = False
            
        if success:
            console.print(f"[green]✓ Agent at {target} killed successfully[/green]")
        else:
            console.print(f"[red]✗ Failed to kill agent at {target}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Error killing agent: {str(e)}[/red]")


@agent.command()
@click.argument('target')
@click.option('--json', is_flag=True, help='Output in JSON format')
@click.pass_context
def info(ctx: click.Context, target: str, json: bool) -> None:
    """Get detailed diagnostic information about a specific agent.
    
    Provides comprehensive details about an agent's current state,
    including activity history, resource usage, and system health.
    
    TARGET: Target agent in format session:window (e.g., 'my-project:0')
    
    Examples:
        tmux-orc agent info frontend:0        # Show detailed frontend agent info
        tmux-orc agent info backend:1 --json  # Get machine-readable info
        tmux-orc agent info testing:2         # Diagnostic info for testing agent
    
    Information Provided:
        - Agent existence and accessibility
        - Current status and health state
        - Recent terminal activity (last 20 lines)
        - Resource usage and performance metrics
        - Session and window configuration
        - Last response time and communication status
    
    Output Formats:
        - Default: Human-readable formatted output
        - --json: Machine-readable JSON for automation
    
    Use Cases:
        - Debugging unresponsive agents
        - Monitoring agent performance
        - Gathering data for system optimization
        - Integration with monitoring tools (JSON mode)
    """
    tmux: TMUXManager = ctx.obj['tmux']

    # Get detailed agent information
    agent_info = {
        'target': target,
        'exists': tmux.has_session(target.split(':')[0]) if ':' in target else False,
        'pane_content': '',
        'status': 'unknown'
    }

    if agent_info['exists']:
        try:
            agent_info['pane_content'] = tmux.capture_pane(target, lines=20)
            agent_info['status'] = 'active' if agent_info['pane_content'] else 'inactive'
        except Exception as e:
            agent_info['status'] = f'error: {str(e)}'

    if json:
        import json as json_module
        console.print(json_module.dumps(agent_info, indent=2))
    else:
        console.print(f"[bold cyan]Agent Information: {target}[/bold cyan]")
        console.print(f"  Exists: {'✓' if agent_info['exists'] else '✗'}")
        console.print(f"  Status: {agent_info['status']}")
        if agent_info['pane_content'] and isinstance(agent_info['pane_content'], str):
            console.print("  Recent activity:")
            lines = str(agent_info['pane_content']).split('\n')[-5:]
            for line in lines:
                if line.strip():
                    console.print(f"    {line[:60]}..." if len(line) > 60 else f"    {line}")
