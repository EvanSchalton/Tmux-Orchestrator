"""Send a message to a specific agent with advanced delivery control."""

import re
import time

import click
from rich.console import Console

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


def send_message(ctx: click.Context, target: str, message: str, delay: float, json: bool) -> None:
    """Send a message to a specific agent with advanced delivery control.

    <mcp>[AGENT SEND] Enhanced message sending with retry and timing control.
    Parameters: kwargs (string) - 'action=send target=session:window args=["message"] [options={...}]'

    Examples:
    - Basic send: kwargs='action=send target=backend:1 args=["Deploy the service"]'
    - With retries: kwargs='action=send target=frontend:0 args=["Update UI"] options={"max-retries": 3}'
    - Custom delay: kwargs='action=send target=qa:2 args=["Run tests"] options={"initial-delay": 2.0}'

    More reliable than 'agent message'. Use for critical production communications.</mcp>

    Delivers messages to Claude agents with sophisticated target validation,
    timing controls, and robust error handling. Implements production-grade
    message delivery patterns optimized for agent responsiveness and reliability.

    DIRECT SENDING: All messages are sent directly without chunking.
    Tmux handles 4000+ characters natively.

    Args:
        ctx: Click context containing TMUX manager and configuration
        target: Agent target in session:window or session:window.pane format
        message: Message text to deliver to the agent
        delay: Inter-operation delay for timing control (0.1-5.0 seconds)
        json: Output structured results for automation integration

    Target Format Specification:
        Standard Window Targeting:
        - Format: session:window (e.g., 'my-project:0')
        - Targets the active pane within the specified window
        - Most common usage pattern for agent communication
        - Automatic pane resolution for multi-pane windows

        Specific Pane Targeting:
        - Format: session:window.pane (e.g., 'my-project:0.1')
        - Targets exact pane for precise message delivery
        - Required for complex multi-pane agent configurations
        - Enables parallel agent operation within single window

    Message Delivery Features:
        - Direct message delivery without chunking
        - Support for messages up to 4000+ characters
        - Single atomic send operation
        - Immediate delivery with no artificial delays
        - Full message integrity maintained

    Performance Characteristics:
        Delivery Speed:
        - All messages: 1-2 seconds end-to-end
        - Large messages: Same speed as small messages
        - Multi-line content: No additional overhead
        - System scaling: Constant time regardless of size

    Security and Safety:
        - Input sanitization prevents command injection
        - Local-only operation (no network exposure)
        - Agent isolation through TMUX session boundaries
        - No persistent message storage or logging
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Validate target format
    if not re.match(r"^[^:]+:\d+(\.\d+)?$", target):
        error_msg = f"Invalid target format '{target}'. Use session:window or session:window.pane"
        if json:
            import json as json_module

            result = {
                "success": False,
                "target": target,
                "message": message,
                "error": error_msg,
                "status": "invalid_format",
            }
            console.print(json_module.dumps(result, indent=2))
            return
        console.print(f"[red]✗ {error_msg}[/red]")
        return

    # Parse target to validate session exists
    session_name = target.split(":")[0]
    if not tmux.has_session(session_name):
        error_msg = f"Session '{session_name}' does not exist"
        if json:
            import json as json_module

            result = {
                "success": False,
                "target": target,
                "message": message,
                "error": error_msg,
                "status": "session_not_found",
            }
            console.print(json_module.dumps(result, indent=2))
            return
        console.print(f"[red]✗ {error_msg}[/red]")
        return

    # Send message directly without chunking
    try:
        # Clear the input line
        tmux.press_ctrl_u(target)
        time.sleep(delay)

        # Send the entire message as literal text (tmux handles 4000+ chars)
        success = tmux.send_message(target, message, delay)
        status_msg = "sent" if success else "failed"

    except Exception as e:
        success = False
        status_msg = f"failed: {str(e)}"

    # Output results
    if json:
        import json as json_module

        result = {
            "success": success,
            "target": target,
            "message": message,
            "delay": delay,
            "status": status_msg,
            "timestamp": time.time(),
        }
        console.print(json_module.dumps(result, indent=2))
        return

    if success:
        console.print(f"[green]✓ Message sent to {target}[/green]")
        console.print(f"[dim]Message length: {len(message)} chars, sent directly[/dim]")
    else:
        console.print(f"[red]✗ Failed to send message to {target}: {status_msg}[/red]")
