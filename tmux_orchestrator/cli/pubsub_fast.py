#!/usr/bin/env python3
"""Ultra-fast pubsub CLI interface using daemon backend.

Replaces slow CLI-based pubsub with daemon IPC for sub-100ms performance.
"""

import asyncio
import json
import sys
from typing import List

import click
from rich.console import Console

from tmux_orchestrator.core.messaging_daemon import DaemonClient

console = Console()


@click.group()
def pubsub_fast() -> None:
    """High-performance pubsub messaging via daemon backend.

    Target: <100ms message delivery (vs 5000ms CLI overhead).

    Examples:
        tmux-orc pubsub-fast publish --target pm:0 "Message"
        tmux-orc pubsub-fast read --target qa:0
        tmux-orc pubsub-fast status
    """
    pass


@pubsub_fast.command()
@click.argument("message")
@click.option("--target", required=True, help="Target session:window")
@click.option("--priority", type=click.Choice(["low", "normal", "high", "critical"]), default="normal")
@click.option("--tag", multiple=True, help="Message tags")
def publish(message: str, target: str, priority: str, tag: List[str]) -> None:
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


@pubsub_fast.command()
@click.option("--target", required=True, help="Target session:window")
@click.option("--lines", type=int, default=50, help="Lines to read")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def read(target: str, lines: int, json_output: bool) -> None:
    """Read from target via daemon."""

    async def _read():
        client = DaemonClient()

        start_time = asyncio.get_event_loop().time()
        response = await client.read(target, lines)
        end_time = asyncio.get_event_loop().time()

        read_time_ms = (end_time - start_time) * 1000

        if response["status"] == "success":
            if json_output:
                console.print(json.dumps(response, indent=2))
            else:
                console.print(f"[bold]📖 Reading from {target} ({read_time_ms:.1f}ms)[/bold]")
                console.print(response["content"])
        else:
            console.print(f"[red]✗ Failed: {response.get('message', 'Unknown error')}[/red]")

    try:
        asyncio.run(_read())
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


@pubsub_fast.command()
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


@pubsub_fast.command()
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


if __name__ == "__main__":
    pubsub_fast()
