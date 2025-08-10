"""Agent management commands."""

import re
import subprocess
from typing import Any

import click
from rich.console import Console
from rich.table import Table

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
    "agent_type",
    type=click.Choice(["frontend", "backend", "testing", "database", "docs", "devops"]),
)
@click.argument("role", type=click.Choice(["developer", "pm", "qa", "reviewer"]))
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def deploy(ctx: click.Context, agent_type: str, role: str, json: bool) -> None:
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

    manager: AgentManager = AgentManager(ctx.obj["tmux"])
    session: str = manager.deploy_agent(agent_type, role)

    if json:
        import json as json_module

        result = {
            "success": True,
            "agent_type": agent_type,
            "role": role,
            "session": session,
            "message": f"Deployed {agent_type} {role} in session: {session}",
        }
        console.print(json_module.dumps(result, indent=2))
        return

    console.print(f"[green]✓ Deployed {agent_type} {role} in session: {session}[/green]")


@agent.command()
@click.argument("target")
@click.argument("message")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def message(ctx: click.Context, target: str, message: str, json: bool) -> None:
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
    tmux: TMUXManager = ctx.obj["tmux"]
    success = tmux.send_message(target, message)

    if json:
        import json as json_module

        result = {
            "success": success,
            "target": target,
            "message": message,
            "status": "sent" if success else "failed",
        }
        console.print(json_module.dumps(result, indent=2))
        return

    if success:
        console.print(f"[green]✓ Message sent to {target}[/green]")
    else:
        console.print(f"[red]✗ Failed to send message to {target}[/red]")


@agent.command()
@click.argument("target")
@click.argument("message")
@click.option("--delay", default=0.5, help="Delay between message operations in seconds")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def send(ctx: click.Context, target: str, message: str, delay: float, json: bool) -> None:
    """Send a message to a specific agent with enhanced control.

    Sends a message directly to the Claude agent running in the specified tmux
    target. Supports both session:window and session:window.pane formats for
    precise targeting.

    TARGET: Target agent in format session:window or session:window.pane
    MESSAGE: The message text to send to the agent

    Examples:
        tmux-orc agent send frontend:0 "Please implement the login form"
        tmux-orc agent send backend:1.2 "STATUS: What's your current progress?"
        tmux-orc agent send testing:2 "Run the integration tests" --delay 1.0
        tmux-orc agent send docs:0 "Update deployment guide" --json

    Target Format Details:
        - session:window (e.g., 'my-project:0') - targets the window's active pane
        - session:window.pane (e.g., 'my-project:0.1') - targets specific pane

    Features:
        - Native Python implementation (no shell scripts)
        - Configurable delay between operations
        - Rich error handling and validation
        - Support for both positional and option-based arguments
        - JSON output for automation and scripting

    Usage Tips:
        - Use quotes for multi-word messages
        - Messages appear instantly to the target agent
        - Agents respond in their tmux window/pane
        - Use 'tmux-orc agent attach TARGET' to see the response
        - Adjust --delay for slower systems or complex messages
    """
    import time

    tmux: TMUXManager = ctx.obj["tmux"]

    # Validate target format
    if not re.match(r"^[^:]+:\d+(\.\d+)?$", target):
        error_msg = f"Invalid target format '{target}'. Use session:window or session:window.pane"
        if json:
            import json as json_module

            result = {
                "success": False,
                "target": target,
                "message": message,
                "error": error_msg,
                "status": "invalid_format",
            }
            console.print(json_module.dumps(result, indent=2))
            return
        console.print(f"[red]✗ {error_msg}[/red]")
        return

    # Parse target to validate session exists
    session_name = target.split(":")[0]
    if not tmux.has_session(session_name):
        error_msg = f"Session '{session_name}' does not exist"
        if json:
            import json as json_module

            result = {
                "success": False,
                "target": target,
                "message": message,
                "error": error_msg,
                "status": "session_not_found",
            }
            console.print(json_module.dumps(result, indent=2))
            return
        console.print(f"[red]✗ {error_msg}[/red]")
        return

    # Send message using TMUXManager with custom delay handling
    try:
        # Clear any existing input first
        tmux.send_keys(target, "C-c")
        time.sleep(delay)

        # Clear the input line
        tmux.send_keys(target, "C-u")
        time.sleep(delay)

        # Send the actual message
        tmux.send_keys(target, message)
        time.sleep(max(delay * 6, 3.0))  # Ensure adequate time for message processing

        # Move to end and submit
        tmux.send_keys(target, "End")
        time.sleep(delay * 0.4)
        tmux.send_keys(target, "Enter")
        time.sleep(delay * 2)
        tmux.send_keys(target, "Enter")

        success = True
        status_msg = "sent"

    except Exception as e:
        success = False
        status_msg = f"failed: {str(e)}"

    # Output results
    if json:
        import json as json_module

        result = {
            "success": success,
            "target": target,
            "message": message,
            "delay": delay,
            "status": status_msg,
            "timestamp": time.time(),
        }
        console.print(json_module.dumps(result, indent=2))
        return

    if success:
        console.print(f"[green]✓ Message sent to {target}[/green]")
        console.print(f"[dim]Used {delay}s delay between operations[/dim]")
    else:
        console.print(f"[red]✗ Failed to send message to {target}: {status_msg}[/red]")


@agent.command()
@click.argument("target")
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
        subprocess.run(["tmux", "attach", "-t", target], check=True)
    except subprocess.CalledProcessError:
        console.print(f"[red]✗ Failed to attach to {target}[/red]")


@agent.command()
@click.argument("target")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def restart(ctx: click.Context, target: str, json: bool) -> None:
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
    tmux: TMUXManager = ctx.obj["tmux"]

    console.print(f"[yellow]Restarting agent at {target}...[/yellow]")

    # Delegate to business logic
    success, result_message = restart_agent(tmux, target)

    if json:
        import json as json_module

        result = {
            "success": success,
            "target": target,
            "message": result_message,
            "action": "restart",
        }
        console.print(json_module.dumps(result, indent=2))
        return

    if success:
        console.print(f"[green]✓ {result_message}[/green]")
    else:
        console.print(f"[red]✗ {result_message}[/red]")


@agent.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def status(ctx: click.Context, json: bool) -> None:
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

    manager: AgentManager = AgentManager(ctx.obj["tmux"])
    statuses: dict[str, Any] = manager.get_all_status()

    if json:
        import json as json_module

        console.print(json_module.dumps(statuses, indent=2))
        return

    for agent_id, status in statuses.items():
        console.print(f"\n[bold cyan]{agent_id}[/bold cyan]")
        console.print(f"  Status: {status['state']}")
        console.print(f"  Last Activity: {status['last_activity']}")
        if status.get("current_task"):
            console.print(f"  Current Task: {status['current_task']}")


@agent.command()
@click.argument("target")
@click.option("--session", is_flag=True, help="Kill entire session (requires confirmation)")
@click.pass_context
def kill(ctx: click.Context, target: str, session: bool) -> None:
    """Terminate a specific agent or entire session.

    By default, kills only the specified agent window. Use --session flag
    to kill an entire session with all its agents.

    TARGET:
        - Without --session: session:window format (e.g., 'my-project:0')
        - With --session: session name only (e.g., 'my-project')

    Examples:
        tmux-orc agent kill frontend:0        # Kill only frontend agent window
        tmux-orc agent kill backend:2         # Kill only backend agent window
        tmux-orc agent kill my-project --session  # Kill entire session (with confirmation)

    ⚠️  WARNING:
        - Window kill: Terminates only the specified agent
        - Session kill: Terminates ALL agents in the session

    When to Use Window Kill:
        - Agent is frozen or unresponsive
        - Agent completed its task
        - Need to replace specific agent

    When to Use Session Kill:
        - Project is complete
        - Need to clean up all agents at once
        - Session is corrupted

    The kill operation loses all context and conversation history.
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    if session:
        # Session kill mode
        console.print("\n[bold red]⚠️  WARNING: Session Kill Mode[/bold red]")
        console.print(f"This will terminate ALL agents in session '{target}'")
        console.print("All agent contexts and conversations will be lost.\n")

        if not click.confirm("Are you sure you want to kill the entire session?", default=False):
            console.print("[yellow]Session kill cancelled.[/yellow]")
            return

        console.print(f"[yellow]Killing entire session '{target}'...[/yellow]")
        success = tmux.kill_session(target)

        if success:
            console.print(f"[green]✓ Session '{target}' killed successfully[/green]")
        else:
            console.print(f"[red]✗ Failed to kill session '{target}'[/red]")
    else:
        # Window kill mode (default)
        if ":" not in target:
            console.print("[red]✗ Invalid target format. Use session:window for window kill[/red]")
            console.print("[dim]Tip: Use --session flag to kill entire session[/dim]")
            return

        console.print(f"[yellow]Killing agent at {target}...[/yellow]")

        try:
            # Kill the specific window ONLY
            success = tmux.kill_window(target)

            if success:
                console.print(f"[green]✓ Agent at {target} killed successfully[/green]")
            else:
                console.print(f"[red]✗ Failed to kill agent at {target}[/red]")
        except Exception as e:
            console.print(f"[red]✗ Error killing agent: {str(e)}[/red]")


@agent.command()
@click.argument("target")
@click.option("--json", is_flag=True, help="Output in JSON format")
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
    tmux: TMUXManager = ctx.obj["tmux"]

    # Get detailed agent information
    agent_info = {
        "target": target,
        "exists": tmux.has_session(target.split(":")[0]) if ":" in target else False,
        "pane_content": "",
        "status": "unknown",
    }

    if agent_info["exists"]:
        try:
            agent_info["pane_content"] = tmux.capture_pane(target, lines=20)
            agent_info["status"] = "active" if agent_info["pane_content"] else "inactive"
        except Exception as e:
            agent_info["status"] = f"error: {str(e)}"

    if json:
        import json as json_module

        console.print(json_module.dumps(agent_info, indent=2))
    else:
        console.print(f"[bold cyan]Agent Information: {target}[/bold cyan]")
        console.print(f"  Exists: {'✓' if agent_info['exists'] else '✗'}")
        console.print(f"  Status: {agent_info['status']}")
        if agent_info["pane_content"] and isinstance(agent_info["pane_content"], str):
            console.print("  Recent activity:")
            lines = str(agent_info["pane_content"]).split("\n")[-5:]
            for line in lines:
                if line.strip():
                    console.print(f"    {line[:60]}..." if len(line) > 60 else f"    {line}")


@agent.command(name="list")
@click.option("--session", help="Filter by session name")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def list_agents(ctx: click.Context, session: str, json: bool) -> None:
    """List all agents across sessions with their status.

    Shows all active Claude agents in the system with their:
    - Session and window location
    - Agent type and role
    - Current status (active/idle)
    - Last activity time

    Options:
        --session: Filter agents by session name
        --json: Output in machine-readable JSON format

    Examples:
        tmux-orc agent list                     # List all agents
        tmux-orc agent list --session my-project  # List agents in specific session
        tmux-orc agent list --json              # Get JSON output for automation

    Status Indicators:
        Active: Agent is currently working or responding
        Idle: Agent is waiting for tasks or instructions
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Get all agents
    agents = tmux.list_agents()

    # Filter by session if specified
    if session:
        agents = [a for a in agents if a["session"] == session]

    if json:
        import json as json_module

        console.print(json_module.dumps(agents, indent=2))
        return

    if not agents:
        if session:
            console.print(f"[yellow]No agents found in session '{session}'[/yellow]")
        else:
            console.print("[yellow]No agents found in any session[/yellow]")
        return

    # Create table
    table = Table(title="Active Agents")
    table.add_column("Session", style="cyan")
    table.add_column("Window", style="blue")
    table.add_column("Type", style="green")
    table.add_column("Role", style="yellow")
    table.add_column("Status", style="magenta")
    table.add_column("Target", style="dim")

    # Add rows
    for agent in agents:
        target = f"{agent['session']}:{agent['window']}"

        # Try to determine role from window name
        window_name = ""
        try:
            windows = tmux.list_windows(agent["session"])
            for w in windows:
                if str(w["index"]) == str(agent["window"]):
                    window_name = w["name"]
                    break
        except Exception:
            pass

        role = "Agent"
        if "pm" in window_name.lower() or agent["window"] == "0":
            role = "Project Manager"
        elif "qa" in window_name.lower():
            role = "QA Engineer"
        elif "test" in window_name.lower():
            role = "Test Engineer"
        elif "dev" in window_name.lower():
            role = "Developer"

        # Color status
        status_colored = agent["status"]
        if agent["status"] == "Idle":
            status_colored = f"[yellow]{agent['status']}[/yellow]"
        elif agent["status"] == "Active":
            status_colored = f"[green]{agent['status']}[/green]"

        table.add_row(agent["session"], str(agent["window"]), agent["type"], role, status_colored, target)

    console.print(table)

    # Summary
    total = len(agents)
    idle = len([a for a in agents if a["status"] == "Idle"])
    active = total - idle

    console.print(f"\n[bold]Summary:[/bold] {total} agents ({active} active, {idle} idle)")

    if session:
        console.print(f"[dim]Filtered by session: {session}[/dim]")


@agent.command()
@click.argument("name")
@click.argument("target")
@click.option("--briefing", help="Custom system prompt/briefing for the agent")
@click.option("--working-dir", help="Working directory for the agent")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def spawn(ctx: click.Context, name: str, target: str, briefing: str, working_dir: str, json: bool) -> None:
    """Spawn a custom agent into a specific session and window.

    This command creates a new Claude agent with complete customization.
    Unlike deploy, this allows ANY agent name and custom system prompts.

    NAME: Custom agent name (e.g., 'api-specialist', 'ui-architect')
    TARGET: Target location in format session:window (e.g., 'myproject:3')

    Options:
        --briefing: Full system prompt/briefing for the agent
        --working-dir: Working directory for the agent
        --json: Output result in JSON format

    Examples:
        # Spawn a custom API specialist
        tmux-orc agent spawn api-specialist myproject:2 \\
            --briefing "You are an API design specialist focused on RESTful principles..."

        # Spawn a performance engineer
        tmux-orc agent spawn perf-engineer backend:3 \\
            --working-dir /workspaces/backend \\
            --briefing "You are a performance optimization engineer..."

        # Spawn with minimal configuration
        tmux-orc agent spawn researcher project:4

    The orchestrator typically uses this command to create custom agents
    tailored to specific project needs, as defined in the team composition plan.
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Validate target format
    if not re.match(r"^[^:]+:\d+$", target):
        error_msg = f"Invalid target format '{target}'. Use session:window"
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
        return

    session_name, window_idx = target.split(":")

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
            return

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
        return

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
        return

    # Start Claude in the new window
    actual_target = f"{session_name}:{actual_window_idx}"
    tmux.send_keys(actual_target, "claude --dangerously-skip-permissions")
    tmux.send_keys(actual_target, "Enter")

    # CRITICAL: Wait for Claude to fully initialize to prevent Ctrl+C interruption
    import time

    time.sleep(8)  # Give Claude sufficient time to load completely

    # Send briefing if provided
    if briefing:
        tmux.send_message(actual_target, briefing)
        briefing_sent = True
    else:
        briefing_sent = False

    # Prepare result
    result_data = {
        "success": True,
        "name": name,
        "target": actual_target,
        "window_name": window_name,
        "briefing_sent": briefing_sent,
    }

    if json:
        import json as json_module

        console.print(json_module.dumps(result_data, indent=2))
    else:
        console.print(f"[green]✓ Spawned custom agent '{name}' at {actual_target}[/green]")
        console.print(f"  Window name: {window_name}")
        if briefing_sent:
            console.print("  Custom briefing: ✓ Sent")
        else:
            console.print("  Custom briefing: None provided")
        if working_dir:
            console.print(f"  Working directory: {working_dir}")
