"""Console utilities for CLI output."""


from rich.console import Console
from rich.panel import Panel

# Shared console instances
console = Console()
error_console = Console(stderr=True)


def create_panel(content: str, title: str = "", style: str = "cyan") -> Panel:
    """Create a styled panel for display."""
    return Panel(content, title=title, style=style)
