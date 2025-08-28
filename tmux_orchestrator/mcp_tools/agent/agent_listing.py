"""Agent listing MCP tools."""

import logging
import re
from typing import Any, Dict, Optional

from ..shared_logic import (
    CommandExecutor,
    ExecutionError,
    format_error_response,
    format_success_response,
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
            # Basic session name validation
            # (no colon, alphanumeric + hyphens/underscores)
            if not re.match(r"^[a-zA-Z0-9_-]+$", filter_session):
                return format_error_response(
                    f"Invalid session name '{filter_session}'. "
                    f"Use alphanumeric characters, hyphens, and underscores only",
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
                "total_count": (len(data.get("agents", [])) if isinstance(data, dict) else 0),
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
                [
                    "Check if tmux-orc service is running",
                    "Verify session access permissions",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), "agent list")
    except Exception as e:
        logger.error(f"Unexpected error in agent_list: {e}")
        return format_error_response(f"Unexpected error: {e}", "agent list")
