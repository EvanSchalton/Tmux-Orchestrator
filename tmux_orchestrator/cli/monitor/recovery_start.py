"""Start the agent recovery daemon with enhanced PM detection."""

import click
from rich.console import Console

console = Console()


def recovery_start_daemon(ctx: click.Context, config: str | None) -> None:
    """Start the agent recovery daemon with enhanced PM detection."""
    from tmux_orchestrator.core.recovery import RecoveryDaemon as RecoveryService

    from .models import ConfigPath

    # Validate config path if provided
    if config:
        try:
            validated_config = ConfigPath(path=config)
            config = validated_config.path
        except ValueError as e:
            console.print(f"[red]Invalid config path: {e}[/red]")
            return

    recovery = RecoveryService()

    try:
        # RecoveryDaemon uses async start(), handle differently
        import asyncio

        asyncio.run(recovery.start())
        console.print("[green]✓ Recovery daemon started successfully[/green]")
        console.print("[dim]Use 'tmux-orc monitor recovery-status' to check status[/dim]")
    except Exception as e:
        console.print(f"[red]Error starting recovery daemon: {e}[/red]")
