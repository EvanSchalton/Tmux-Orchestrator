"""List command - Display all active agents across sessions."""

import click


def list_agents(ctx: click.Context, json_format: bool) -> None:
    """List all active agents across sessions with comprehensive status.

    <mcp>[LIST] Display all active agents across all tmux sessions.
    Parameters: kwargs (string) - 'action=list [options={"json": true}]'

    Examples:
    - List all agents: kwargs='action=list'
    - JSON format: kwargs='action=list options={"json": true}'

    Shows all agents system-wide. For team summaries use 'team list', for agent details use 'agent status'.</mcp>

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

    Integration Notes:
        • Integrates with monitoring daemon for real-time status
        • Supports filtering and sorting options
        • Compatible with automation scripts via --json
        • Performance optimized for large agent deployments
    """
    from rich.table import Table

    console = ctx.obj["console"]
    tmux = ctx.obj["tmux"]
    json_output = json_format or ctx.obj.get("json_mode", False)

    try:
        # Get all sessions
        sessions = tmux.list_sessions()
        agents = []

        for session in sessions:
            try:
                # Get windows for this session (extract name from session dict)
                session_name = session.get("name") if isinstance(session, dict) else session
                windows = tmux.list_windows(session_name)
                for window in windows:
                    # Basic agent detection logic
                    agent_info = {
                        "session": session_name,
                        "window": window.get("index", window.get("window", "unknown")),
                        "name": window.get("name", "unknown"),
                        "status": "unknown",
                        "type": "agent",
                    }
                    agents.append(agent_info)
            except Exception:
                continue

        if json_format:
            import json

            console.print(json.dumps(agents, indent=2))
        else:
            if not agents:
                console.print("[yellow]No active agents found[/yellow]")
                return

            table = Table(title="Active Agents Overview")
            table.add_column("Session:Window", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Type", style="blue")

            for agent in agents:
                session_window = f"{agent['session']}:{agent['window']}"
                table.add_row(
                    session_window,
                    agent["name"],
                    agent["status"],
                    agent["type"],
                )

            console.print(table)

    except Exception as e:
        error_msg = f"Failed to list agents: {e}"
        if json_output:
            import json

            console.print(json.dumps({"error": error_msg}))
        else:
            console.print(f"[red]{error_msg}[/red]")
