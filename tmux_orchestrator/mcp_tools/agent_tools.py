"""
Agent Management Tools

Implements native MCP tools for agent lifecycle management with exact parameter
signatures from API Designer's specifications.
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


async def agent_list(
    format: str = "table", filter_session: Optional[str] = None, include_idle: bool = True
) -> Dict[str, Any]:
    """
    List all active agents across sessions.

    Implements API Designer's agent_list specification with comprehensive filtering.

    Args:
        format: Output format preference ("table", "json", "summary")
        filter_session: Filter agents by session name
        include_idle: Include idle agents in results

    Returns:
        Structured response with agent list and metadata
    """
    try:
        # Validate format parameter
        valid_formats = {"table", "json", "summary"}
        if format not in valid_formats:
            return format_error_response(
                f"Invalid format '{format}'. Valid formats: {', '.join(valid_formats)}",
                "agent list",
                ["Use 'table', 'json', or 'summary' format"],
            )

        # Validate session filter if provided
        if filter_session:
            # Basic session name validation (no colon, alphanumeric + hyphens/underscores)
            import re

            if not re.match(r"^[a-zA-Z0-9_-]+$", filter_session):
                return format_error_response(
                    f"Invalid session name '{filter_session}'. Use alphanumeric characters, hyphens, and underscores only",
                    f"agent list --filter-session {filter_session}",
                )

        # Build command
        cmd = ["tmux-orc", "agent", "list"]

        # Add format if not default
        if format != "table":
            cmd.extend(["--format", format])

        # Add session filter
        if filter_session:
            cmd.extend(["--filter-session", filter_session])

        # Add include-idle flag (default is true, so only add if false)
        if not include_idle:
            cmd.append("--exclude-idle")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=(format == "json"))

        if result["success"]:
            # Enhance response with metadata
            data = result["data"]

            # Add call metadata
            response_data = {
                "agents": data.get("agents", []) if isinstance(data, dict) else [],
                "format": format,
                "filter_applied": filter_session,
                "include_idle": include_idle,
                "total_count": len(data.get("agents", [])) if isinstance(data, dict) else 0,
            }

            # Add summary statistics if available
            if isinstance(data, dict) and "summary" in data:
                response_data["summary"] = data["summary"]

            return format_success_response(
                response_data, result["command"], f"Retrieved {response_data['total_count']} agents"
            )
        else:
            return format_error_response(
                result.get("stderr", "Failed to list agents"),
                result["command"],
                ["Check if tmux-orc service is running", "Verify session access permissions"],
            )

    except ExecutionError as e:
        return format_error_response(str(e), "agent list")
    except Exception as e:
        logger.error(f"Unexpected error in agent_list: {e}")
        return format_error_response(f"Unexpected error: {e}", "agent list")


async def agent_status(target: str, include_metrics: bool = False) -> Dict[str, Any]:
    """
    Get detailed status of a specific agent.

    Implements API Designer's agent_status specification with metrics support.

    Args:
        target: Agent target in 'session:window' format
        include_metrics: Include performance metrics

    Returns:
        Structured response with agent status and optional metrics
    """
    try:
        # Validate target format using shared logic
        validate_session_format(target)

        # Build command
        cmd = ["tmux-orc", "agent", "status", target]

        # Add metrics flag if requested
        if include_metrics:
            cmd.append("--metrics")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Enhance response with call metadata
            response_data = {
                "target": target,
                "include_metrics": include_metrics,
                "status": data if isinstance(data, dict) else {"raw_status": data},
                "timestamp": None,  # Could add timestamp if CLI provides it
            }

            return format_success_response(response_data, result["command"], f"Status retrieved for {target}")
        else:
            return format_error_response(
                result.get("stderr", f"Failed to get status for {target}"),
                result["command"],
                [
                    f"Check that target '{target}' exists",
                    "Verify agent is responsive",
                    "Use 'tmux-orc agent list' to see available targets",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"agent status {target}")
    except ExecutionError as e:
        return format_error_response(str(e), f"agent status {target}")
    except Exception as e:
        logger.error(f"Unexpected error in agent_status: {e}")
        return format_error_response(f"Unexpected error: {e}", f"agent status {target}")


async def agent_send_message(
    target: str, message: str, priority: str = "normal", expect_response: bool = False
) -> Dict[str, Any]:
    """
    Send message to a specific agent.

    Implements API Designer's agent_send_message specification with priority levels.

    Args:
        target: Agent target in 'session:window' format
        message: Message content to send to the agent
        priority: Message priority level ("low", "normal", "high", "urgent")
        expect_response: Whether to wait for agent response

    Returns:
        Structured response with message delivery status
    """
    try:
        # Validate target format
        validate_session_format(target)

        # Validate message content
        if not message or not message.strip():
            return format_error_response(
                "Message cannot be empty", f"agent send-message {target}", ["Provide a non-empty message"]
            )

        # Validate priority
        valid_priorities = {"low", "normal", "high", "urgent"}
        if priority not in valid_priorities:
            return format_error_response(
                f"Invalid priority '{priority}'. Valid priorities: {', '.join(valid_priorities)}",
                f"agent send-message {target}",
                [f"Use one of: {', '.join(valid_priorities)}"],
            )

        # Build command
        cmd = ["tmux-orc", "agent", "message", target, message]

        # Add priority if not normal
        if priority != "normal":
            cmd.extend(["--priority", priority])

        # Add response expectation flag
        if expect_response:
            cmd.append("--expect-response")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "target": target,
                "message": message,
                "priority": priority,
                "expect_response": expect_response,
                "delivery_status": data if isinstance(data, dict) else {"delivered": True},
                "message_id": data.get("message_id") if isinstance(data, dict) else None,
            }

            return format_success_response(
                response_data, result["command"], f"Message sent to {target} with {priority} priority"
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to send message to {target}"),
                result["command"],
                [
                    f"Check that target '{target}' exists and is responsive",
                    "Verify agent is not in compaction or error state",
                    "Use 'tmux-orc agent status {target}' to check agent health",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"agent send-message {target}")
    except ExecutionError as e:
        return format_error_response(str(e), f"agent send-message {target}")
    except Exception as e:
        logger.error(f"Unexpected error in agent_send_message: {e}")
        return format_error_response(f"Unexpected error: {e}", f"agent send-message {target}")


async def agent_restart(target: str, preserve_context: bool = True, force: bool = False) -> Dict[str, Any]:
    """
    Restart a specific agent.

    Implements API Designer's agent_restart specification with context preservation.

    Args:
        target: Agent target in 'session:window' format
        preserve_context: Preserve agent context during restart
        force: Force restart even if agent is busy

    Returns:
        Structured response with restart status
    """
    try:
        # Validate target format
        validate_session_format(target)

        # Build command
        cmd = ["tmux-orc", "agent", "restart", target]

        # Add context preservation flag (default is true, so add --no-preserve if false)
        if not preserve_context:
            cmd.append("--no-preserve-context")

        # Add force flag if requested
        if force:
            cmd.append("--force")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "target": target,
                "preserve_context": preserve_context,
                "force": force,
                "restart_status": data if isinstance(data, dict) else {"restarted": True},
                "restart_time": data.get("restart_time") if isinstance(data, dict) else None,
            }

            return format_success_response(response_data, result["command"], f"Agent {target} restarted successfully")
        else:
            return format_error_response(
                result.get("stderr", f"Failed to restart agent {target}"),
                result["command"],
                [
                    f"Check that target '{target}' exists",
                    "Use --force flag if agent is unresponsive",
                    "Verify sufficient system resources for restart",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"agent restart {target}")
    except ExecutionError as e:
        return format_error_response(str(e), f"agent restart {target}")
    except Exception as e:
        logger.error(f"Unexpected error in agent_restart: {e}")
        return format_error_response(f"Unexpected error: {e}", f"agent restart {target}")


async def agent_kill(target: str, graceful: bool = True, timeout: int = 30) -> Dict[str, Any]:
    """
    Terminate a specific agent.

    Implements API Designer's agent_kill specification with graceful timeouts.

    Args:
        target: Agent target in 'session:window' format
        graceful: Attempt graceful shutdown first
        timeout: Timeout in seconds for graceful shutdown (1-60)

    Returns:
        Structured response with kill status
    """
    try:
        # Validate target format
        validate_session_format(target)

        # Validate timeout
        if not (1 <= timeout <= 60):
            return format_error_response(
                f"Invalid timeout {timeout}. Must be between 1 and 60 seconds",
                f"agent kill {target}",
                ["Use timeout between 1-60 seconds"],
            )

        # Build command
        cmd = ["tmux-orc", "agent", "kill", target]

        # Add graceful flag (default is true, so add --force if false)
        if not graceful:
            cmd.append("--force")

        # Add timeout if not default
        if timeout != 30:
            cmd.extend(["--timeout", str(timeout)])

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "target": target,
                "graceful": graceful,
                "timeout": timeout,
                "kill_status": data if isinstance(data, dict) else {"killed": True},
                "kill_method": "graceful" if graceful else "force",
            }

            return format_success_response(
                response_data,
                result["command"],
                f"Agent {target} terminated {'gracefully' if graceful else 'forcefully'}",
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to kill agent {target}"),
                result["command"],
                [
                    f"Check that target '{target}' exists",
                    "Use graceful=false for unresponsive agents",
                    "Verify you have permission to kill the agent",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"agent kill {target}")
    except ExecutionError as e:
        return format_error_response(str(e), f"agent kill {target}")
    except Exception as e:
        logger.error(f"Unexpected error in agent_kill: {e}")
        return format_error_response(f"Unexpected error: {e}", f"agent kill {target}")


async def agent_attach(target: str, read_only: bool = False) -> Dict[str, Any]:
    """
    Attach to an agent's terminal session.

    Implements API Designer's agent_attach specification with read-only mode.

    Args:
        target: Agent target in 'session:window' format
        read_only: Attach in read-only mode

    Returns:
        Structured response with attachment status
    """
    try:
        # Validate target format
        validate_session_format(target)

        # Build command
        cmd = ["tmux-orc", "session", "attach", target]

        # Add read-only flag if requested
        if read_only:
            cmd.append("--read-only")

        # Execute command (attach is typically non-blocking in MCP context)
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "target": target,
                "read_only": read_only,
                "attach_status": data if isinstance(data, dict) else {"attached": True},
                "attach_mode": "read-only" if read_only else "read-write",
            }

            return format_success_response(
                response_data,
                result["command"],
                f"Attached to {target} in {'read-only' if read_only else 'interactive'} mode",
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to attach to {target}"),
                result["command"],
                [
                    f"Check that target '{target}' exists",
                    "Verify tmux session is active",
                    "Ensure you have attach permissions",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"agent attach {target}")
    except ExecutionError as e:
        return format_error_response(str(e), f"agent attach {target}")
    except Exception as e:
        logger.error(f"Unexpected error in agent_attach: {e}")
        return format_error_response(f"Unexpected error: {e}", f"agent attach {target}")
