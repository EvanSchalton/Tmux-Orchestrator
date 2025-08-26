"""
Core MCP Tools Module

Contains basic tool implementations that will be used by the specific modules.
This provides a foundation for all the specialized tool modules.
"""

import logging
from typing import Any, Dict, Optional

from .shared_logic import (
    CommandExecutor,
    ExecutionError,
    ValidationError,
    format_error_response,
    format_success_response,
    validate_session_format,
)

logger = logging.getLogger(__name__)


async def spawn_agent(session: str, role: str, briefing: str, window: Optional[int] = None) -> Dict[str, Any]:
    """
    Spawn a new agent with specified role and briefing.

    Args:
        session: Session name
        role: Agent role (developer, qa-engineer, etc.)
        briefing: Agent briefing text
        window: Optional window number (auto-assigned if None)

    Returns:
        Result dictionary with success status and agent info
    """
    try:
        # Validate inputs
        if not session or not role or not briefing:
            return format_error_response(
                "Session, role, and briefing are required",
                f"spawn agent {session} {role}",
                ["Ensure all parameters are provided", "Check session name format"],
            )

        # Build command
        cmd = ["tmux-orc", "spawn", "agent", role]

        # Add target if window specified
        if window is not None:
            validate_session_format(f"{session}:{window}")
            cmd.extend(["--session", f"{session}:{window}"])
        else:
            cmd.extend(["--session", session])

        # Add briefing
        cmd.extend(["--briefing", briefing])

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            return format_success_response(result["data"], result["command"], f"Agent {role} spawned successfully")
        else:
            return format_error_response(
                result.get("stderr", "Spawn failed"),
                result["command"],
                ["Check session exists", "Verify role is valid", "Ensure briefing is not empty"],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"spawn agent {session} {role}")
    except ExecutionError as e:
        return format_error_response(str(e), f"spawn agent {session} {role}")
    except Exception as e:
        logger.error(f"Unexpected error in spawn_agent: {e}")
        return format_error_response(f"Unexpected error: {e}", f"spawn agent {session} {role}")


async def spawn_pm(session: str, briefing: Optional[str] = None, window: Optional[int] = None) -> Dict[str, Any]:
    """
    Spawn a Project Manager agent.

    Args:
        session: Session name
        briefing: Optional PM briefing (uses default if None)
        window: Optional window number

    Returns:
        Result dictionary with success status and PM info
    """
    try:
        # Use default briefing if none provided
        pm_briefing = briefing or "Project Manager with standard PM context"

        # Build command
        cmd = ["tmux-orc", "spawn", "pm"]

        # Add target
        if window is not None:
            validate_session_format(f"{session}:{window}")
            cmd.extend(["--session", f"{session}:{window}"])
        else:
            cmd.extend(["--session", session])

        # Add briefing
        cmd.extend(["--briefing", pm_briefing])

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            return format_success_response(result["data"], result["command"], "Project Manager spawned successfully")
        else:
            return format_error_response(result.get("stderr", "PM spawn failed"), result["command"])

    except ValidationError as e:
        return format_error_response(str(e), f"spawn pm {session}")
    except ExecutionError as e:
        return format_error_response(str(e), f"spawn pm {session}")
    except Exception as e:
        logger.error(f"Unexpected error in spawn_pm: {e}")
        return format_error_response(f"Unexpected error: {e}", f"spawn pm {session}")


async def kill_agent(target: str, force: bool = False) -> Dict[str, Any]:
    """
    Kill an agent or session.

    Args:
        target: Target in 'session:window' format, or just 'session' for entire session
        force: Force kill without confirmation

    Returns:
        Result dictionary with success status
    """
    try:
        # Build command
        cmd = ["tmux-orc", "agent", "kill", target]

        if force:
            cmd.append("--force")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            kill_type = "window" if ":" in target else "session"
            return format_success_response(
                result["data"], result["command"], f"Successfully killed {kill_type} {target}"
            )
        else:
            return format_error_response(
                result.get("stderr", "Kill failed"), result["command"], ["Check target exists", "Use --force if needed"]
            )

    except Exception as e:
        logger.error(f"Unexpected error in kill_agent: {e}")
        return format_error_response(f"Unexpected error: {e}", f"kill {target}")


async def send_message(target: str, message: str, urgent: bool = False) -> Dict[str, Any]:
    """
    Send message to an agent.

    Args:
        target: Target in 'session:window' format
        message: Message text
        urgent: Mark as urgent message

    Returns:
        Result dictionary with success status
    """
    try:
        # Validate target format
        validate_session_format(target)

        if not message.strip():
            return format_error_response("Message cannot be empty", f"send message to {target}")

        # Build command
        cmd = ["tmux-orc", "agent", "message", target, message]

        if urgent:
            cmd.append("--urgent")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            return format_success_response(result["data"], result["command"], f"Message sent to {target}")
        else:
            return format_error_response(
                result.get("stderr", "Message send failed"),
                result["command"],
                ["Check target exists", "Verify agent is responsive"],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"send message to {target}")
    except ExecutionError as e:
        return format_error_response(str(e), f"send message to {target}")
    except Exception as e:
        logger.error(f"Unexpected error in send_message: {e}")
        return format_error_response(f"Unexpected error: {e}", f"send message to {target}")


async def list_agents() -> Dict[str, Any]:
    """
    List all active agents.

    Returns:
        Result dictionary with agent list
    """
    try:
        # Build command
        cmd = ["tmux-orc", "agent", "list"]

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            return format_success_response(result["data"], result["command"], "Agent list retrieved successfully")
        else:
            return format_error_response(result.get("stderr", "Failed to list agents"), result["command"])

    except ExecutionError as e:
        return format_error_response(str(e), "list agents")
    except Exception as e:
        logger.error(f"Unexpected error in list_agents: {e}")
        return format_error_response(f"Unexpected error: {e}", "list agents")


async def get_status(target: Optional[str] = None) -> Dict[str, Any]:
    """
    Get status of agent or system.

    Args:
        target: Optional target to get status for (if None, gets system status)

    Returns:
        Result dictionary with status information
    """
    try:
        # Build command
        if target:
            validate_session_format(target)
            cmd = ["tmux-orc", "agent", "status", target]
        else:
            cmd = ["tmux-orc", "status"]

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            status_type = f"for {target}" if target else "system"
            return format_success_response(
                result["data"], result["command"], f"Status {status_type} retrieved successfully"
            )
        else:
            return format_error_response(result.get("stderr", "Failed to get status"), result["command"])

    except ValidationError as e:
        return format_error_response(str(e), f"get status {target or 'system'}")
    except ExecutionError as e:
        return format_error_response(str(e), f"get status {target or 'system'}")
    except Exception as e:
        logger.error(f"Unexpected error in get_status: {e}")
        return format_error_response(f"Unexpected error: {e}", f"get status {target or 'system'}")


async def monitor_dashboard() -> Dict[str, Any]:
    """
    Get monitoring dashboard information.

    Returns:
        Result dictionary with dashboard data
    """
    try:
        # Build command
        cmd = ["tmux-orc", "monitor", "dashboard"]

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            return format_success_response(result["data"], result["command"], "Dashboard data retrieved successfully")
        else:
            return format_error_response(result.get("stderr", "Failed to get dashboard"), result["command"])

    except ExecutionError as e:
        return format_error_response(str(e), "monitor dashboard")
    except Exception as e:
        logger.error(f"Unexpected error in monitor_dashboard: {e}")
        return format_error_response(f"Unexpected error: {e}", "monitor dashboard")


async def show_context(context_name: str) -> Dict[str, Any]:
    """
    Show context information.

    Args:
        context_name: Name of context to show (orc, pm, mcp, tmux-comms)

    Returns:
        Result dictionary with context data
    """
    try:
        # Validate context name
        valid_contexts = {"orc", "pm", "mcp", "tmux-comms"}
        if context_name not in valid_contexts:
            return format_error_response(
                f"Invalid context '{context_name}'. Valid contexts: {', '.join(valid_contexts)}",
                f"show context {context_name}",
                [f"Use one of: {', '.join(valid_contexts)}"],
            )

        # Build command
        cmd = ["tmux-orc", "context", "show", context_name]

        # Execute command (context show returns markdown, not JSON)
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=False)

        if result["success"]:
            return format_success_response(
                {"context": context_name, "content": result["stdout"]},
                result["command"],
                f"Context {context_name} retrieved successfully",
            )
        else:
            return format_error_response(result.get("stderr", "Failed to show context"), result["command"])

    except ExecutionError as e:
        return format_error_response(str(e), f"show context {context_name}")
    except Exception as e:
        logger.error(f"Unexpected error in show_context: {e}")
        return format_error_response(f"Unexpected error: {e}", f"show context {context_name}")
