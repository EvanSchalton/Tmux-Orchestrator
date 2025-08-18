"""Error management and reporting commands."""

from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tmux_orchestrator.core.error_handler import (
    ErrorSeverity,
    clear_error_messages,
    get_error_handler,
)

console = Console()


@click.group()
def errors() -> None:
    """Error management and reporting utilities.

    Provides commands for viewing error logs, analyzing error patterns,
    and managing error history for the TMUX Orchestrator system.

    Examples:
        tmux-orc errors summary       # Show error summary
        tmux-orc errors recent        # Show recent errors
        tmux-orc errors clear         # Clear old error logs
        tmux-orc errors stats         # Show error statistics
    """
    pass


@errors.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
def summary(json: bool) -> None:
    """Display comprehensive error summary and statistics.

    Shows an overview of all errors tracked by the system, including
    categorization, severity distribution, and recovery success rates.

    Examples:
        tmux-orc errors summary       # Show error summary
        tmux-orc errors summary --json  # JSON output for automation
    """
    handler = get_error_handler()
    summary_data = handler.get_error_summary()

    if not summary_data["total"]:
        console.print("[green]No errors recorded[/green]")
        return

    if json:
        import json as json_module

        console.print(json_module.dumps(summary_data, indent=2))
        return

    # Create summary table
    table = Table(title="Error Summary", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Errors", str(summary_data["total"]))
    table.add_row("Recovery Success Rate", f"{summary_data['recovery_success_rate']:.1f}%")

    console.print(table)

    # Show errors by category
    if summary_data["by_category"]:
        cat_table = Table(title="Errors by Category", show_header=True)
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Count", style="yellow")

        for category, count in sorted(summary_data["by_category"].items()):
            cat_table.add_row(category.title(), str(count))

        console.print("\n")
        console.print(cat_table)

    # Show errors by severity
    if summary_data["by_severity"]:
        sev_table = Table(title="Errors by Severity", show_header=True)
        sev_table.add_column("Severity", style="cyan")
        sev_table.add_column("Count", style="yellow")

        severity_colors = {"low": "green", "medium": "yellow", "high": "red", "critical": "red bold"}

        for severity, count in summary_data["by_severity"].items():
            color = severity_colors.get(severity, "white")
            sev_table.add_row(f"[{color}]{severity.upper()}[/{color}]", str(count))

        console.print("\n")
        console.print(sev_table)


@errors.command()
@click.option("--count", "-n", default=10, help="Number of errors to show")
@click.option("--severity", type=click.Choice(["low", "medium", "high", "critical"]), help="Filter by severity")
@click.option("--category", help="Filter by error category")
def recent(count: int, severity: Optional[str], category: Optional[str]) -> None:
    """Display recent errors with details.

    Shows the most recent errors recorded by the system, with options
    to filter by severity and category.

    Examples:
        tmux-orc errors recent               # Show last 10 errors
        tmux-orc errors recent -n 20         # Show last 20 errors
        tmux-orc errors recent --severity critical  # Critical errors only
        tmux-orc errors recent --category tmux     # TMUX errors only
    """
    handler = get_error_handler()

    # Get all errors
    all_errors = handler.error_history

    if not all_errors:
        console.print("[green]No errors recorded[/green]")
        return

    # Apply filters
    filtered_errors = all_errors

    if severity:
        filtered_errors = [e for e in filtered_errors if e.severity == ErrorSeverity(severity)]

    if category:
        filtered_errors = [e for e in filtered_errors if e.category.value == category.lower()]

    # Sort by timestamp (most recent first) and limit
    filtered_errors.sort(key=lambda e: e.timestamp, reverse=True)
    filtered_errors = filtered_errors[:count]

    if not filtered_errors:
        console.print("[yellow]No errors match the specified filters[/yellow]")
        return

    # Display errors
    for i, error in enumerate(filtered_errors, 1):
        severity_colors = {
            ErrorSeverity.LOW: "green",
            ErrorSeverity.MEDIUM: "yellow",
            ErrorSeverity.HIGH: "red",
            ErrorSeverity.CRITICAL: "red bold",
        }

        color = severity_colors.get(error.severity, "white")

        panel_content = (
            f"[yellow]Type:[/yellow] {error.error_type}\n"
            f"[yellow]Message:[/yellow] {error.message}\n"
            f"[yellow]Category:[/yellow] {error.category.value}\n"
            f"[yellow]Operation:[/yellow] {error.context.operation}\n"
            f"[yellow]Time:[/yellow] {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        if error.context.agent_id:
            panel_content += f"\n[yellow]Agent:[/yellow] {error.context.agent_id}"

        if error.recovery_attempted:
            status = "✓ Successful" if error.recovery_successful else "✗ Failed"
            panel_content += f"\n[yellow]Recovery:[/yellow] {status}"

        panel = Panel(
            panel_content,
            title=f"[{color}]Error #{i} - {error.severity.value.upper()}[/{color}]",
            border_style=color,
        )

        console.print(panel)

        if i < len(filtered_errors):
            console.print()  # Add spacing between errors


@errors.command()
@click.option("--age-days", default=7, help="Clear errors older than N days")
@click.option("--dry-run", is_flag=True, help="Show what would be cleared without clearing")
def clear(age_days: int, dry_run: bool) -> None:
    """Clear old error logs to save disk space.

    Removes error log files older than the specified number of days.
    Use --dry-run to preview what would be deleted.

    Examples:
        tmux-orc errors clear              # Clear errors older than 7 days
        tmux-orc errors clear --age-days 30  # Clear errors older than 30 days
        tmux-orc errors clear --dry-run    # Preview what would be cleared
    """
    if dry_run:
        console.print(f"[yellow]DRY RUN: Would clear error logs older than {age_days} days[/yellow]")
        # Could enhance to show actual files that would be deleted
        return

    cleared = clear_error_messages(age_days)

    if cleared > 0:
        console.print(f"[green]✓ Cleared {cleared} error log file(s)[/green]")
    else:
        console.print(f"[yellow]No error logs older than {age_days} days found[/yellow]")


@errors.command()
def stats() -> None:
    """Display detailed error statistics and trends.

    Shows comprehensive error analysis including patterns, trends,
    and recommendations for system improvement.

    Examples:
        tmux-orc errors stats    # Show error statistics
    """
    handler = get_error_handler()
    summary = handler.get_error_summary()

    if not summary["total"]:
        console.print("[green]No errors recorded - system running smoothly![/green]")
        return

    # Overall health assessment
    error_rate = summary["total"]  # Could calculate per time period
    recovery_rate = summary["recovery_success_rate"]

    health_status = "🟢 Good"
    if error_rate > 100:
        health_status = "🔴 Poor"
    elif error_rate > 50:
        health_status = "🟡 Fair"

    health_panel = Panel(
        f"[bold]System Health:[/bold] {health_status}\n"
        f"[bold]Total Errors:[/bold] {summary['total']}\n"
        f"[bold]Recovery Success:[/bold] {recovery_rate:.1f}%",
        title="Error Statistics Overview",
        border_style="blue",
    )

    console.print(health_panel)

    # Top error categories
    if summary["by_category"]:
        console.print("\n[bold]Top Error Categories:[/bold]")
        sorted_categories = sorted(summary["by_category"].items(), key=lambda x: x[1], reverse=True)[:5]

        for category, count in sorted_categories:
            percentage = (count / summary["total"]) * 100
            bar_length = int(percentage / 2)
            bar = "█" * bar_length
            console.print(f"  {category.title():<15} {bar} {count} ({percentage:.1f}%)")

    # Recommendations
    console.print("\n[bold]Recommendations:[/bold]")

    if summary["by_category"].get("tmux", 0) > 10:
        console.print("  • High TMUX errors - check session stability")

    if summary["by_category"].get("network", 0) > 20:
        console.print("  • Network issues detected - verify connectivity")

    if recovery_rate < 50:
        console.print("  • Low recovery success - review recovery procedures")

    if summary["by_severity"].get("critical", 0) > 5:
        console.print("  • [red]Critical errors detected - immediate attention needed[/red]")
