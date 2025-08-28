"""Stop the monitoring daemon gracefully."""

import os
import signal
from pathlib import Path

import click
from rich.console import Console

console = Console()

# Use project directory for storage
PROJECT_DIR = str(Path.cwd() / ".tmux_orchestrator")
PID_FILE = f"{PROJECT_DIR}/idle-monitor.pid"


def stop_daemon(ctx: click.Context, json: bool) -> None:
    """Stop the monitoring daemon and disable automated health checks.

    <mcp>Stop the monitoring daemon completely. Gracefully shuts down background monitoring service, disabling automated health checks, failure detection, and recovery operations. Use for maintenance or debugging.</mcp>

    Gracefully shuts down the monitoring daemon, stopping all automated
    health checks and recovery operations.

    Examples:
        tmux-orc monitor stop                  # Stop monitoring daemon

    Impact of Stopping:
        • No automatic agent health monitoring
        • No automated failure detection
        • No idle agent identification
        • Manual intervention required for issues
        • Loss of performance metrics collection

    ⚠️  Warning: Stopping monitoring disables automated recovery

    Use this when:
        • Performing system maintenance
        • Debugging monitoring issues
        • Temporarily reducing system load
        • Switching to manual management mode

    Remember to restart monitoring after maintenance to ensure
    continued system reliability.
    """
    from tmux_orchestrator.core.monitor import IdleMonitor
    from tmux_orchestrator.utils.tmux import TMUXManager

    tmux = TMUXManager()
    IdleMonitor(tmux)

    if json:
        # JSON output mode
        import json as json_module

        result = {"command": "monitor stop", "success": False, "message": ""}

        # Skip supervised stop - monitor.supervisor doesn't exist
        # Go directly to legacy stop

        # Try legacy stop
        if not os.path.exists(PID_FILE):
            result["success"] = False
            result["message"] = "Monitor is not running"
            console.print(json_module.dumps(result, indent=2))
            return

        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())

            # Create graceful stop file
            graceful_stop_file = Path(PROJECT_DIR) / "idle-monitor.graceful"
            graceful_stop_file.touch()

            # Send SIGTERM
            os.kill(pid, signal.SIGTERM)
            result["success"] = True
            result["message"] = f"Monitor stop signal sent to PID {pid}"
            result["pid"] = pid

            # Clean up PID file
            try:
                os.unlink(PID_FILE)
            except Exception:
                pass

        except ProcessLookupError:
            result["success"] = False
            result["message"] = "Monitor process not found, cleaning up PID file"
            try:
                os.unlink(PID_FILE)
            except Exception:
                pass
        except ValueError:
            result["success"] = False
            result["message"] = "Invalid PID file format"
        except Exception as e:
            result["success"] = False
            result["message"] = f"Failed to stop monitor: {e}"
            result["error"] = str(e)

        console.print(json_module.dumps(result, indent=2))
        return

    # Skip supervised stop - monitor.supervisor doesn't exist
    # Go directly to legacy stop

    # Fallback to legacy stop
    if not os.path.exists(PID_FILE):
        console.print("[yellow]Monitor is not running[/yellow]")
        return

    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())

        # Create graceful stop file to signal this is an authorized stop
        graceful_stop_file = Path(PROJECT_DIR) / "idle-monitor.graceful"
        graceful_stop_file.touch()

        # Send SIGTERM to daemon
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]✓ Monitor stop signal sent to PID {pid}[/green]")

        # Clean up PID file immediately (daemon might be slow)
        try:
            os.unlink(PID_FILE)
        except Exception:
            pass

    except ProcessLookupError:
        console.print("[yellow]Monitor process not found, cleaning up PID file[/yellow]")
        try:
            os.unlink(PID_FILE)
        except Exception:
            pass
    except ValueError:
        console.print("[red]Invalid PID file format[/red]")
    except Exception as e:
        console.print(f"[red]✗ Failed to stop monitor: {e}[/red]")
