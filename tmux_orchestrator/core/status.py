"""Status dashboard for monitoring agents."""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table


class StatusDashboard:
    """Interactive status dashboard for monitoring agents."""

    def __init__(self, tmux_manager):
        self.tmux = tmux_manager
        self.console = Console()

    def display(self, session_filter: Optional[str] = None):
        """Display the status dashboard."""
        # Create main layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )

        # Header
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header_text = f"TMUX Orchestrator Status Dashboard - {current_time}"
        if session_filter:
            header_text += f" (Session: {session_filter})"

        layout["header"].update(Panel(header_text, style="bold blue"))

        # Main content - split into sessions and agents
        layout["main"].split_row(
            Layout(name="sessions", ratio=1),
            Layout(name="agents", ratio=2)
        )

        # Get sessions
        try:
            sessions = self.tmux.list_sessions()
        except Exception:
            sessions = []

        if session_filter:
            sessions = [s for s in sessions if s.get('name') == session_filter]

        # Sessions panel
        sessions_table = Table(title="Sessions")
        sessions_table.add_column("Name", style="cyan")
        sessions_table.add_column("Windows", style="magenta")
        sessions_table.add_column("Status", style="green")

        for session in sessions:
            try:
                windows = self.tmux.list_windows(session['name'])
                status = "Attached" if session.get('attached') == '1' else "Detached"
                sessions_table.add_row(session['name'], str(len(windows)), status)
            except Exception:
                sessions_table.add_row(session['name'], "?", "Unknown")

        layout["sessions"].update(Panel(sessions_table, title="Sessions"))

        # Agents panel - use a simpler approach since list_agents may not exist
        agents_table = Table(title="Development Team Status")
        agents_table.add_column("Window", style="cyan")
        agents_table.add_column("Role", style="magenta")
        agents_table.add_column("Status", style="green")

        # Check specific development session
        dev_session = "tmux-orc-dev"
        try:
            windows = self.tmux.list_windows(dev_session)
            role_map = {
                1: "Orchestrator",
                2: "MCP-Developer",
                3: "CLI-Developer",
                4: "Agent-Recovery-Dev",
                5: "Project-Manager"
            }

            for window in windows:
                window_id = window.get('window_index', '?')
                window_name = window.get('window_name', 'Unknown')
                role = role_map.get(int(window_id), window_name)

                # Simple status check - if window exists, assume agent is running
                status = "🟢 Active" if window_id else "🔴 Inactive"

                agents_table.add_row(f"{dev_session}:{window_id}", role, status)

        except Exception as e:
            agents_table.add_row("No development", "team found", f"Error: {str(e)[:30]}")

        layout["agents"].update(Panel(agents_table, title="Agents"))

        # Footer with commands
        footer_text = "Commands: Use 'tmux attach-session -t session:window' to connect to agents"
        layout["footer"].update(Panel(footer_text, style="dim"))

        self.console.print(layout)
