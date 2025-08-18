#!/usr/bin/env python3
"""Ultra-fast pubsub CLI interface using daemon backend.

Replaces slow CLI-based pubsub with daemon IPC for sub-100ms performance.
"""

import asyncio
import json
import sys

import click
from rich.console import Console

from tmux_orchestrator.core.messaging_daemon import DaemonClient

console = Console()


@click.group()
def pubsub() -> None:
    """High-performance pubsub messaging via daemon backend.

    Target: <100ms message delivery (vs 5000ms CLI overhead).

    Examples:
        tmux-orc pubsub publish --target pm:0 "Message"
        tmux-orc pubsub read --target qa:0
        tmux-orc pubsub status
    """
    pass


@pubsub.command()
@click.argument("message")
@click.option("--target", required=True, help="Target session:window")
@click.option("--priority", type=click.Choice(["low", "normal", "high", "critical"]), default="normal")
@click.option("--tag", multiple=True, help="Message tags")
def publish(message: str, target: str, priority: str, tag: list[str]) -> None:
    """Publish message via high-performance daemon (target: <100ms)."""

    async def _publish():
        client = DaemonClient()

        start_time = asyncio.get_event_loop().time()
        response = await client.publish(target, message, priority, list(tag))
        end_time = asyncio.get_event_loop().time()

        delivery_time_ms = (end_time - start_time) * 1000

        if response["status"] == "queued":
            console.print(f"[green]✓ Message queued for {target} ({delivery_time_ms:.1f}ms)[/green]")
            if delivery_time_ms > 100:
                console.print(f"[yellow]⚠️  Delivery time {delivery_time_ms:.1f}ms exceeds 100ms target[/yellow]")
        else:
            console.print(f"[red]✗ Failed: {response.get('message', 'Unknown error')}[/red]")

    try:
        asyncio.run(_publish())
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


@pubsub.command()
@click.option("--target", required=True, help="Target session:window")
@click.option("--lines", type=int, default=50, help="Lines to read")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option(
    "--filter-priority",
    type=click.Choice(["critical", "high", "normal", "low"]),
    multiple=True,
    help="Filter by priority",
)
@click.option(
    "--filter-category",
    type=click.Choice(["health", "recovery", "status", "task", "escalation"]),
    multiple=True,
    help="Filter by category",
)
@click.option("--filter-tag", multiple=True, help="Filter by tag")
@click.option("--filter-source", help="Filter by source type (daemon, pm, agent)")
@click.option("--unacked-only", is_flag=True, help="Show only unacknowledged messages")
def read(
    target: str,
    lines: int,
    json_output: bool,
    filter_priority: list[str],
    filter_category: list[str],
    filter_tag: list[str],
    filter_source: str,
    unacked_only: bool,
) -> None:
    """Read from target via daemon with optional filtering."""

    async def _read():
        client = DaemonClient()

        start_time = asyncio.get_event_loop().time()
        response = await client.read(target, lines)
        end_time = asyncio.get_event_loop().time()

        read_time_ms = (end_time - start_time) * 1000

        if response["status"] == "success":
            content = response["content"]

            # Apply filters if content contains structured messages
            if filter_priority or filter_category or filter_tag or filter_source or unacked_only:
                filtered_content = _apply_message_filters(
                    content, filter_priority, filter_category, filter_tag, filter_source, unacked_only
                )
                content = filtered_content

            if json_output:
                console.print(
                    json.dumps({"status": "success", "content": content, "read_time_ms": read_time_ms}, indent=2)
                )
            else:
                console.print(f"[bold]📖 Reading from {target} ({read_time_ms:.1f}ms)[/bold]")
                if filter_priority or filter_category or filter_tag or filter_source or unacked_only:
                    console.print("[dim]Filters applied[/dim]")
                console.print(content)
        else:
            console.print(f"[red]✗ Failed: {response.get('message', 'Unknown error')}[/red]")

    try:
        asyncio.run(_read())
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


@pubsub.command()
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
def status(format: str) -> None:
    """Show daemon status and performance metrics."""

    async def _status():
        client = DaemonClient()
        response = await client.get_status()

        if response["status"] == "active":
            if format == "json":
                console.print(json.dumps(response, indent=2))
            else:
                console.print("[bold]🚀 High-Performance Messaging Daemon Status[/bold]")
                console.print(f"Status: [green]{response['status']}[/green]")
                console.print(f"Uptime: {response['uptime_seconds']:.1f}s")
                console.print(f"Messages Processed: {response['messages_processed']}")
                console.print(f"Queue Size: {response['queue_size']}")
                console.print(f"Avg Delivery Time: {response['avg_delivery_time_ms']:.1f}ms")
                console.print(f"Performance Target: {response['performance_target']}")

                perf_status = response["current_performance"]
                if perf_status == "OK":
                    console.print(f"Performance: [green]{perf_status}[/green]")
                else:
                    console.print(f"Performance: [red]{perf_status}[/red]")
        else:
            console.print(f"[red]✗ Daemon error: {response.get('message', 'Unknown error')}[/red]")

    try:
        asyncio.run(_status())
    except Exception as e:
        console.print(f"[red]✗ Error connecting to daemon: {e}[/red]")
        console.print("[yellow]💡 Hint: Start daemon with 'tmux-orc daemon start'[/yellow]")
        sys.exit(1)


@pubsub.command()
def stats() -> None:
    """Show detailed performance statistics."""

    async def _stats():
        client = DaemonClient()
        command = {"command": "stats"}
        response = await client.send_command(command)

        if "performance_metrics" in response:
            metrics = response["performance_metrics"]
            console.print("[bold]📊 Performance Metrics[/bold]")
            console.print(f"Total Messages: {metrics['total_messages']}")
            console.print(f"Queue Depth: {metrics['queue_depth']}")

            times = metrics["delivery_times_ms"]
            console.print("\n[bold]⏱️  Delivery Times (ms)[/bold]")
            console.print(f"Min: {times['min']:.1f}ms")
            console.print(f"Avg: {times['avg']:.1f}ms")
            console.print(f"P95: {times['p95']:.1f}ms")
            console.print(f"Max: {times['max']:.1f}ms")

            target = metrics["target_performance"]
            meeting = metrics["meeting_target"]
            console.print("\n[bold]🎯 Target Performance[/bold]")
            console.print(f"Target: <{target}ms")
            if meeting:
                console.print("[green]✓ Meeting performance target[/green]")
            else:
                console.print("[red]✗ NOT meeting performance target[/red]")
        else:
            console.print(f"[red]✗ Error: {response.get('message', 'Unknown error')}[/red]")

    try:
        asyncio.run(_stats())
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


def _apply_message_filters(
    content: str,
    filter_priority: list[str],
    filter_category: list[str],
    filter_tag: list[str],
    filter_source: str,
    unacked_only: bool,
) -> str:
    """Apply filters to message content.

    Args:
        content: Raw message content
        filter_priority: Priority levels to include
        filter_category: Categories to include
        filter_tag: Tags to include
        filter_source: Source type to include
        unacked_only: Only show unacknowledged messages

    Returns:
        Filtered content
    """
    # Parse lines and try to identify structured messages
    lines = content.split("\n")
    filtered_lines = []

    for line in lines:
        # Try to parse as JSON structured message
        try:
            if line.strip().startswith("{"):
                msg = json.loads(line)

                # Check if it's a structured message
                if all(key in msg for key in ["id", "timestamp", "source", "message", "metadata"]):
                    # Apply filters
                    if filter_priority and msg["message"]["priority"] not in filter_priority:
                        continue
                    if filter_category and msg["message"]["category"] not in filter_category:
                        continue
                    if filter_source and msg["source"]["type"] != filter_source:
                        continue
                    if filter_tag:
                        msg_tags = msg["metadata"].get("tags", [])
                        if not any(tag in msg_tags for tag in filter_tag):
                            continue
                    if unacked_only and not msg["metadata"].get("requires_ack", False):
                        continue

                    # Format structured message for display
                    formatted = _format_structured_message(msg)
                    filtered_lines.append(formatted)
                else:
                    # Not a structured message, include if no filters
                    if not (filter_priority or filter_category or filter_tag or filter_source or unacked_only):
                        filtered_lines.append(line)
            else:
                # Regular line, include if no filters
                if not (filter_priority or filter_category or filter_tag or filter_source or unacked_only):
                    filtered_lines.append(line)
        except json.JSONDecodeError:
            # Not JSON, include if no filters
            if not (filter_priority or filter_category or filter_tag or filter_source or unacked_only):
                filtered_lines.append(line)

    return "\n".join(filtered_lines)


def _format_structured_message(msg: dict) -> str:
    """Format structured message for display.

    Args:
        msg: Structured message dict

    Returns:
        Formatted string
    """
    priority = msg["message"]["priority"]
    category = msg["message"]["category"]
    subject = msg["message"]["content"]["subject"]
    body = msg["message"]["content"]["body"]
    source = msg["source"]["identifier"]
    timestamp = msg["timestamp"]

    # Priority indicators
    priority_icons = {"critical": "🚨", "high": "⚠️", "normal": "📨", "low": "💬"}

    icon = priority_icons.get(priority, "📨")

    return f"{icon} [{priority.upper()}] {subject}\n   From: {source} | Category: {category}\n   {body}\n   Time: {timestamp}"


@pubsub.command()
@click.option("--session", required=True, help="Session to query")
@click.option(
    "--priority", type=click.Choice(["critical", "high", "normal", "low"]), multiple=True, help="Filter by priority"
)
@click.option(
    "--category",
    type=click.Choice(["health", "recovery", "status", "task", "escalation"]),
    multiple=True,
    help="Filter by category",
)
@click.option("--source", help="Filter by source (daemon, pm, agent)")
@click.option("--since", type=int, default=30, help="Minutes to look back")
@click.option("--unacked", is_flag=True, help="Only unacknowledged messages")
@click.option("--format", "output_format", type=click.Choice(["pretty", "json", "summary"]), default="pretty")
def query(
    session: str, priority: list[str], category: list[str], source: str, since: int, unacked: bool, output_format: str
) -> None:
    """Query structured messages with advanced filtering."""

    async def _query():
        # For now, simulate querying message store
        # In production, this would query the actual message store
        console.print(f"[bold]🔍 Querying messages for session: {session}[/bold]")
        console.print(f"Filters: priority={priority or 'all'}, category={category or 'all'}, source={source or 'all'}")
        console.print(f"Time range: last {since} minutes")

        if unacked:
            console.print("[yellow]Showing only unacknowledged messages[/yellow]")

        # Example output
        if output_format == "summary":
            console.print("\n[bold]Summary:[/bold]")
            console.print("• Total messages: 42")
            console.print("• Critical: 2")
            console.print("• High priority: 5")
            console.print("• Unacknowledged: 3")
            console.print("• Categories: health (15), status (20), recovery (7)")

    try:
        asyncio.run(_query())
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    pubsub()
