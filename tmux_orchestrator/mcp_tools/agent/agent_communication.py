"""Agent communication MCP tools."""

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
                f"Invalid priority '{priority}'. " f"Valid priorities: {', '.join(valid_priorities)}",
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
                "delivery_status": (data if isinstance(data, dict) else {"delivered": True}),
                "message_id": (data.get("message_id") if isinstance(data, dict) else None),
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
