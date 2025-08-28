"""Interactive monitoring dashboard with real-time updates."""

import click
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel

console = Console()


def show_dashboard(ctx: click.Context, session: str | None, refresh: int, json: bool) -> None:
    """Interactive monitoring dashboard with real-time updates."""
    tmux = ctx.obj["tmux"]

    def create_dashboard():
        """Create the dashboard layout."""
        # Get system data
        sessions = tmux.list_sessions()
        agents = tmux.list_agents()

        # Filter by session if specified
        if session:
            sessions = [s for s in sessions if s["name"] == session]
            agents = [a for a in agents if a["session"] == session]

        if json:
            dashboard_data = {
                "timestamp": "2024-01-01T10:00:00Z",  # Would use real timestamp
                "sessions": sessions,
                "agents": agents,
                "summary": {
                    "total_sessions": len(sessions),
                    "total_agents": len(agents),
                    "active_agents": len([a for a in agents if a.get("status") == "active"]),
                },
            }
            import json as json_module

            return json_module.dumps(dashboard_data, indent=2)

        # Create dashboard components
        title = "[bold]🔍 TMUX Orchestrator Dashboard" + (f" - {session}" if session else "") + "[/bold]"

        # System summary
        summary_text = (
            f"Sessions: {len(sessions)} | "
            f"Agents: {len(agents)} | "
            f"Active: {len([a for a in agents if a.get('status') == 'active'])}"
        )

        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(Panel(title), size=3),
            Layout(Panel(summary_text, title="System Summary"), size=3),
            Layout(name="main"),
        )

        return layout

    if json:
        console.print(create_dashboard())
        return

    if refresh > 0:
        # Live updating dashboard
        try:
            with Live(create_dashboard(), refresh_per_second=1 / refresh, console=console) as live:
                import time

                while True:
                    time.sleep(refresh)
                    live.update(create_dashboard())
        except KeyboardInterrupt:
            console.print("\n[dim]Dashboard closed[/dim]")
    else:
        # Static dashboard
        console.print(create_dashboard())
