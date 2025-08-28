"""Agent lifecycle MCP tools."""

import logging
from typing import Any, Dict

from ..shared_logic import (
    CommandExecutor,
    ExecutionError,
    ValidationError,
    format_error_response,
    format_success_response,
    validate_session_format,
)

logger = logging.getLogger(__name__)


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
                "restart_status": (data if isinstance(data, dict) else {"restarted": True}),
                "restart_time": (data.get("restart_time") if isinstance(data, dict) else None),
            }

            return format_success_response(
                response_data,
                result["command"],
                f"Agent {target} restarted successfully",
            )
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
                f"Agent {target} terminated " f"{'gracefully' if graceful else 'forcefully'}",
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
