"""Formatting utilities for CLI output."""

import json
from typing import Any

from rich.table import Table


def format_json(data: Any, indent: int = 2) -> str:
    """Format data as JSON string."""
    return json.dumps(data, indent=indent, default=str)


def format_table(headers: list[str], rows: list[list[Any]], title: str = "") -> Table:
    """Create a formatted table for display."""
    table = Table(title=title, show_header=True)

    for header in headers:
        table.add_column(header)

    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    return table


def format_error(message: str, details: str = "") -> str:
    """Format an error message with optional details."""
    output = f"[bold red]Error:[/bold red] {message}"
    if details:
        output += f"\n[dim]{details}[/dim]"
    return output
