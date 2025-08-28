"""Agent status MCP tools."""

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
