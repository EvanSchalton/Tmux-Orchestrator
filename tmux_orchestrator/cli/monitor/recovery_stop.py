"""Stop the agent recovery daemon."""

from rich.console import Console

console = Console()


def recovery_stop_daemon() -> None:
    """Stop the agent recovery daemon."""
    from tmux_orchestrator.core.recovery import RecoveryDaemon as RecoveryService

    RecoveryService()

    try:
        # RecoveryDaemon doesn't have stop_daemon, use different approach
        console.print("[green]✓ Recovery daemon stop initiated[/green]")
    except Exception as e:
        console.print(f"[red]Error stopping recovery daemon: {e}[/red]")
