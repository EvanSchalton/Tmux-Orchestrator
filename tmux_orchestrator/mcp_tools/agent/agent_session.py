"""Agent session management MCP tools."""

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
                f"Attached to {target} in " f"{'read-only' if read_only else 'interactive'} mode",
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
