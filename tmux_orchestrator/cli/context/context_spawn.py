"""Context spawn commands."""

import json as json_module
import logging
import time
from typing import Optional

import click
from rich.console import Console

from tmux_orchestrator.utils.tmux import TMUXManager

from .context_utils import get_available_contexts, load_context

console = Console()
logger = logging.getLogger(__name__)


@click.command("spawn")
@click.argument("role")
@click.option("--session", required=True, help="Target session name or session:window (legacy)")
@click.option("--extend", help="Additional project-specific context")
@click.option("--briefing", help="Additional project-specific briefing (alias for --extend)")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def spawn_context(
    ctx: click.Context,
    role: str,
    session: str,
    extend: Optional[str] = None,
    briefing: Optional[str] = None,
    json: bool = False,
) -> None:
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

    try:
        load_context(role)
    except click.ClickException as e:
        if json:
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

    # Get TMUX manager from context (for testing) or create new one
    tmux: TMUXManager = ctx.obj["tmux"] if ctx.obj and "tmux" in ctx.obj else TMUXManager()
    logger.info(f"Starting spawn for role '{role}' in session '{session}'")

    # Parse session - now accepting session name only or session:window (for compatibility)
    if ":" in session:
        # Legacy format with window index - we'll ignore the index
        session_name, window_part = session.split(":", 1)
        logger.info(f"Parsed legacy format - session: '{session_name}', ignoring window: '{window_part}'")
        if not json:
            console.print(
                f"[yellow]Note: Window index in '{session}' will be ignored. New window will be added to end of session.[/yellow]"
            )
    else:
        # New format - just session name
        session_name = session
        logger.info(f"Using session name: '{session_name}'")

    # Check if session exists, create if needed
    logger.info(f"Checking if session '{session_name}' exists")
    sessions = tmux.list_sessions()
    logger.debug(f"Current sessions: {[s['name'] for s in sessions]}")
    session_created = False
    if not any(s["name"] == session_name for s in sessions):
        logger.info(f"Session '{session_name}' does not exist, creating...")
        if not json:
            console.print(f"[yellow]Creating new session: {session_name}[/yellow]")

        create_result = tmux.create_session(session_name)
        logger.info(f"Session creation result: {create_result}")

        if not create_result:
            logger.error(f"Failed to create session '{session_name}'")
            if json:
                result = {
                    "success": False,
                    "error": f"Failed to create session '{session_name}'",
                    "error_type": "SessionCreationError",
                }
                console.print(json_module.dumps(result, indent=2))
                return
            console.print(f"[red]Error: Failed to create session '{session_name}'[/red]")
            return
        session_created = True
        logger.info(f"Session '{session_name}' created successfully")
    else:
        logger.info(f"Session '{session_name}' already exists")

    # Pause the monitor daemon to prevent interference during PM setup
    # This prevents the daemon from auto-spawning recovery PMs while we're creating one
    if role == "pm":
        logger.info("Attempting to pause monitor daemon for PM spawn")
        try:
            import subprocess

            # Pause for 30 seconds to give us time to set up the PM properly
            cmd = ["tmux-orc", "monitor", "pause", "30"]
            logger.info(f"Executing pause command: {' '.join(cmd)}")
            pause_result = subprocess.run(cmd, capture_output=True, timeout=2, text=True)

            logger.info(f"Pause command return code: {pause_result.returncode}")
            if pause_result.stdout:
                logger.info(f"Pause command stdout: {pause_result.stdout.strip()}")
            if pause_result.stderr:
                logger.error(f"Pause command stderr: {pause_result.stderr.strip()}")

            if pause_result.returncode == 0:
                logger.info("Monitor daemon pause command succeeded")
                if not json:
                    console.print("[dim]Monitor daemon paused for 30 seconds to prevent interference[/dim]")
            else:
                logger.error(f"Monitor daemon pause command failed with return code {pause_result.returncode}")
                if not json:
                    console.print("[yellow]Warning: Could not pause monitor daemon[/yellow]")

        except Exception as e:
            logger.error(f"Exception during monitor daemon pause: {e}")
            if not json:
                console.print("[yellow]Warning: Monitor daemon pause failed[/yellow]")

        # Verify daemon status after pause attempt
        try:
            status_result = subprocess.run(["tmux-orc", "monitor", "status"], capture_output=True, timeout=2, text=True)
            if status_result.returncode == 0 and status_result.stdout:
                logger.info(f"Monitor status after pause attempt: {status_result.stdout.strip()}")
            else:
                logger.info("Could not check monitor status after pause")
        except Exception as e:
            logger.warning(f"Could not verify monitor status after pause: {e}")

    # Create window with appropriate name (always append to end)
    window_name = f"Claude-{role}"
    logger.info(f"Creating window '{window_name}' in session '{session_name}'")
    try:
        # Create new window at the end of the session using TMUXManager
        create_window_result = tmux.create_window(session_name, window_name)
        logger.info(f"Window creation result: {create_window_result}")

        if not create_window_result:
            logger.error(f"create_window returned False for '{window_name}' in session '{session_name}'")
            if json:
                result = {
                    "success": False,
                    "error": f"Failed to create window '{window_name}' in session '{session_name}'",
                    "error_type": "WindowCreationError",
                }
                console.print(json_module.dumps(result, indent=2))
                return
            console.print(f"[red]Error: Failed to create window '{window_name}' in session '{session_name}'[/red]")
            return

        # Get the actual window index that was created
        logger.info(f"Looking for created window '{window_name}' in session '{session_name}'")
        windows = tmux.list_windows(session_name)
        logger.info(f"Windows in session '{session_name}': {windows}")

        actual_window_idx = None
        for window in windows:
            logger.debug(f"Checking window: {window}")
            if window["name"] == window_name:
                actual_window_idx = window["index"]
                logger.info(f"Found window '{window_name}' at index {actual_window_idx}")
                break

        if actual_window_idx is None:
            logger.error(f"Window '{window_name}' was created but not found in list!")
            logger.error(f"Expected window name: '{window_name}'")
            logger.error(f"Available windows: {[w['name'] for w in windows]}")
            if json:
                result = {"success": False, "error": "Window created but not found", "error_type": "WindowNotFound"}
                console.print(json_module.dumps(result, indent=2))
                return
            console.print("[red]Error: Window created but not found[/red]")
            return

        actual_target = f"{session_name}:{actual_window_idx}"
        logger.info(f"Window created successfully - target: {actual_target}")

        # Comprehensive process monitoring to find window killer
        def get_process_snapshot():
            """Get snapshot of all processes for comparison."""
            try:
                import subprocess

                ps_result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
                processes = []
                for line in ps_result.stdout.split("\n")[1:]:  # Skip header
                    if line.strip():
                        parts = line.split(None, 10)  # Split into max 11 parts
                        if len(parts) >= 11:
                            processes.append({"pid": parts[1], "command": parts[10], "full_line": line.strip()})
                return processes
            except Exception as e:
                logger.error(f"Failed to get process snapshot: {e}")
                return []

        logger.info("📊 PROCESS MONITOR: Taking initial process snapshot")
        initial_processes = get_process_snapshot()
        initial_tmux_orc = [p for p in initial_processes if "tmux-orc" in p["command"]]
        logger.info(f"📊 Initial tmux-orc processes: {len(initial_tmux_orc)}")
        for proc in initial_tmux_orc:
            logger.info(f"📊   {proc['pid']}: {proc['command']}")

        # Store process snapshot for comparison during Claude startup
        process_snapshots = {"initial": initial_processes}

        if not json:
            console.print(f"[green]Created window: {actual_target} ({window_name})[/green]")
    except Exception as e:
        logger.error(f"Exception during window creation: {e}", exc_info=True)
        if json:
            result = {"success": False, "error": f"Error creating window: {e}", "error_type": "WindowCreationError"}
            console.print(json_module.dumps(result, indent=2))
            return
        console.print(f"[red]Error creating window: {e}[/red]")
        return

    # Start Claude in the window
    if not json:
        console.print(f"[blue]Starting Claude in {actual_target}...[/blue]")

    logger.info(f"Starting Claude in {actual_target}")
    claude_cmd_result = tmux.send_keys(actual_target, "claude --dangerously-skip-permissions", literal=True)
    logger.info(f"Claude command send result: {claude_cmd_result}")

    enter_result = tmux.send_keys(actual_target, "Enter")
    logger.info(f"Enter key send result: {enter_result}")

    # Take snapshot after Claude command sent
    logger.info("📊 PROCESS MONITOR: Taking snapshot after Claude command sent")
    after_claude_processes = get_process_snapshot()
    process_snapshots["after_claude_cmd"] = after_claude_processes

    # Check for new processes after Claude command
    def compare_processes(before, after, label):
        """Compare process lists and log new processes."""
        before_pids = {p["pid"] for p in before}
        after_pids = {p["pid"] for p in after}
        new_pids = after_pids - before_pids
        gone_pids = before_pids - after_pids

        if new_pids:
            logger.warning(f"📊 NEW PROCESSES ({label}): {len(new_pids)} new processes detected")
            for pid in new_pids:
                proc = next((p for p in after if p["pid"] == pid), None)
                if proc:
                    logger.warning(f"📊   NEW: {proc['pid']}: {proc['command']}")

        if gone_pids:
            logger.info(f"📊 ENDED PROCESSES ({label}): {len(gone_pids)} processes ended")

    compare_processes(initial_processes, after_claude_processes, "after Claude cmd")

    # Wait for Claude to initialize with periodic window checks
    if not json:
        console.print("[dim]Waiting for Claude to initialize...[/dim]")

    logger.info("Starting 8-second Claude initialization wait with periodic window checks")
    last_processes = after_claude_processes
    for i in range(8):
        time.sleep(1)

        # Take process snapshot every few seconds and when window disappears
        if i in [2, 4, 6] or i == 7:  # Take snapshots at critical moments
            current_processes = get_process_snapshot()
            process_snapshots[f"second_{i+1}"] = current_processes
            compare_processes(last_processes, current_processes, f"second {i+1}")
            last_processes = current_processes

        # Check if window still exists
        current_windows = tmux.list_windows(session_name)
        window_exists = any(w["name"] == window_name for w in current_windows)
        logger.info(f"Second {i+1}/8: Window '{window_name}' exists: {window_exists}")

        # If window exists, capture what's in it to see what's happening
        if window_exists:
            try:
                window_content = tmux.capture_pane(actual_target, lines=10)
                logger.info(f"Second {i+1}/8: Window content: {repr(window_content[-200:])}")  # Last 200 chars
            except Exception as e:
                logger.warning(f"Could not capture window content at second {i+1}: {e}")

        if not window_exists:
            # Window just disappeared - take immediate process snapshot
            logger.error(f"🚨 WINDOW DISAPPEARED at second {i+1}! Taking emergency process snapshot")
            disappeared_processes = get_process_snapshot()
            process_snapshots[f"disappeared_second_{i+1}"] = disappeared_processes
            compare_processes(last_processes, disappeared_processes, f"WINDOW DISAPPEARED second {i+1}")

            # Look specifically for any tmux-related processes
            current_tmux_processes = [p for p in disappeared_processes if "tmux" in p["command"].lower()]
            logger.error(f"📊 TMUX PROCESSES when window disappeared: {len(current_tmux_processes)}")
            for proc in current_tmux_processes:
                logger.error(f"📊   TMUX: {proc['pid']}: {proc['command']}")
            logger.error(f"Window '{window_name}' disappeared during Claude initialization at second {i+1}!")
            logger.error(f"Remaining windows: {[w['name'] for w in current_windows]}")

            # Check for processes that might have killed it
            logger.info("Checking for potential window killers...")
            import subprocess

            try:
                ps_result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
                if "tmux-orc" in ps_result.stdout:
                    logger.info("Found tmux-orc processes:")
                    for line in ps_result.stdout.split("\n"):
                        if "tmux-orc" in line and "grep" not in line:
                            logger.info(f"  {line.strip()}")
            except Exception:
                pass

            if json:
                result = {
                    "success": False,
                    "error": f"Window disappeared during Claude initialization at second {i+1}",
                    "error_type": "WindowDisappearedDuringInit",
                }
                console.print(json_module.dumps(result, indent=2))
                return
            console.print("[red]✗ Window disappeared during Claude initialization![/red]")
            return

    logger.info("Claude initialization wait completed, window still exists")

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

    # Add extension/briefing if provided (briefing takes precedence for compatibility)
    additional_context = briefing if briefing else extend
    if additional_context:
        message += f"\n\n## Additional Instructions\n\n{additional_context}"

    if not json:
        console.print(f"[blue]Sending {role} instruction...[/blue]")

    logger.info(f"Sending context message to {actual_target} (length: {len(message)} chars)")
    logger.debug(f"Message content: {message[:200]}...")  # First 200 chars
    success = tmux.send_message(actual_target, message)
    logger.info(f"Message send result: {success}")

    if json:
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
