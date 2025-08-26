"""
Communication Tools

Implements native MCP tools for messaging and team communication with exact parameter
signatures from API Designer's specifications.
"""

import logging
from typing import Any, Dict, List, Optional

from .shared_logic import (
    CommandExecutor,
    ExecutionError,
    ValidationError,
    format_error_response,
    format_success_response,
    validate_session_format,
)

logger = logging.getLogger(__name__)


async def send_message(
    target: str, message: str, priority: str = "normal", expect_response: bool = False
) -> Dict[str, Any]:
    """
    Send message to a specific agent.

    Note: This is an alias for agent_send_message for backward compatibility.
    The primary implementation is in agent_tools.py.

    Args:
        target: Agent target in 'session:window' format
        message: Message content to send to the agent
        priority: Message priority level ("low", "normal", "high", "urgent")
        expect_response: Whether to wait for agent response

    Returns:
        Structured response with message delivery status
    """
    # Import here to avoid circular imports
    from .agent_tools import agent_send_message

    return await agent_send_message(target=target, message=message, priority=priority, expect_response=expect_response)


async def team_broadcast(
    team_name: str, message: str, priority: str = "normal", exclude_roles: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Send message to all team members.

    Implements API Designer's team_broadcast specification with role exclusion.

    Args:
        team_name: Target team name
        message: Message to broadcast
        priority: Message priority level ("low", "normal", "high", "urgent")
        exclude_roles: Agent roles to exclude from broadcast

    Returns:
        Structured response with broadcast results
    """
    try:
        # Validate team name
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", team_name):
            return format_error_response(
                f"Invalid team name '{team_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"team broadcast {team_name}",
            )

        # Validate message content
        if not message or not message.strip():
            return format_error_response(
                "Message cannot be empty", f"team broadcast {team_name}", ["Provide a non-empty message"]
            )

        # Validate priority
        valid_priorities = {"low", "normal", "high", "urgent"}
        if priority not in valid_priorities:
            return format_error_response(
                f"Invalid priority '{priority}'. Valid priorities: {', '.join(valid_priorities)}",
                f"team broadcast {team_name}",
                [f"Use one of: {', '.join(valid_priorities)}"],
            )

        # Build command
        cmd = ["tmux-orc", "team", "broadcast", team_name, message]

        # Add priority if not normal
        if priority != "normal":
            cmd.extend(["--priority", priority])

        # Add role exclusions if provided
        if exclude_roles:
            cmd.extend(["--exclude-roles"] + exclude_roles)

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "team_name": team_name,
                "message": message,
                "priority": priority,
                "exclude_roles": exclude_roles or [],
                "broadcast_status": data if isinstance(data, dict) else {"broadcasted": True},
                "recipients": data.get("recipients", []) if isinstance(data, dict) else [],
                "successful_sends": data.get("successful", 0) if isinstance(data, dict) else 0,
                "failed_sends": data.get("failed", 0) if isinstance(data, dict) else 0,
            }

            return format_success_response(
                response_data, result["command"], f"Broadcast sent to team {team_name} with {priority} priority"
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to broadcast to team {team_name}"),
                result["command"],
                [
                    f"Check that team '{team_name}' exists",
                    "Verify team has active agents",
                    "Ensure agents are responsive",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), f"team broadcast {team_name}")
    except Exception as e:
        logger.error(f"Unexpected error in team_broadcast: {e}")
        return format_error_response(f"Unexpected error: {e}", f"team broadcast {team_name}")


async def broadcast_message(
    session: str, message: str, exclude: Optional[List[str]] = None, priority: str = "normal"
) -> Dict[str, Any]:
    """
    Broadcast message to all agents in a session.

    Alternative interface for session-based broadcasting.

    Args:
        session: Session name to broadcast to
        message: Message to broadcast
        exclude: Window names/numbers to exclude from broadcast
        priority: Message priority level

    Returns:
        Structured response with broadcast results
    """
    try:
        # Validate session name
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", session):
            return format_error_response(
                f"Invalid session name '{session}'. Use alphanumeric characters, hyphens, and underscores only",
                f"broadcast message {session}",
            )

        # Validate message content
        if not message or not message.strip():
            return format_error_response(
                "Message cannot be empty", f"broadcast message {session}", ["Provide a non-empty message"]
            )

        # Validate priority
        valid_priorities = {"low", "normal", "high", "urgent"}
        if priority not in valid_priorities:
            return format_error_response(
                f"Invalid priority '{priority}'. Valid priorities: {', '.join(valid_priorities)}",
                f"broadcast message {session}",
                [f"Use one of: {', '.join(valid_priorities)}"],
            )

        # Build command (using session-based broadcast)
        cmd = ["tmux-orc", "session", "broadcast", session, message]

        # Add priority if not normal
        if priority != "normal":
            cmd.extend(["--priority", priority])

        # Add exclusions if provided
        if exclude:
            cmd.extend(["--exclude"] + [str(x) for x in exclude])

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "session": session,
                "message": message,
                "priority": priority,
                "exclude": exclude or [],
                "broadcast_status": data if isinstance(data, dict) else {"broadcasted": True},
                "targets": data.get("targets", []) if isinstance(data, dict) else [],
                "successful_sends": data.get("successful", 0) if isinstance(data, dict) else 0,
                "failed_sends": data.get("failed", 0) if isinstance(data, dict) else 0,
            }

            return format_success_response(response_data, result["command"], f"Broadcast sent to session {session}")
        else:
            return format_error_response(
                result.get("stderr", f"Failed to broadcast to session {session}"),
                result["command"],
                [
                    f"Check that session '{session}' exists",
                    "Verify session has active windows/agents",
                    "Ensure agents are responsive",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), f"broadcast message {session}")
    except Exception as e:
        logger.error(f"Unexpected error in broadcast_message: {e}")
        return format_error_response(f"Unexpected error: {e}", f"broadcast message {session}")


async def send_urgent_message(target: str, message: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Send urgent message with timeout.

    Convenience function for high-priority messaging with response expectation.

    Args:
        target: Agent target in 'session:window' format
        message: Urgent message content
        timeout: Response timeout in seconds

    Returns:
        Structured response with delivery and response status
    """
    try:
        # Validate target format
        validate_session_format(target)

        # Validate message content
        if not message or not message.strip():
            return format_error_response("Urgent message cannot be empty", f"send urgent message to {target}")

        # Validate timeout
        if not (5 <= timeout <= 300):
            return format_error_response(
                f"Invalid timeout {timeout}. Must be between 5 and 300 seconds",
                f"send urgent message to {target}",
                ["Use timeout between 5-300 seconds"],
            )

        # Build command with urgent priority and response expectation
        cmd = ["tmux-orc", "agent", "message", target, message]
        cmd.extend(["--priority", "urgent"])
        cmd.extend(["--timeout", str(timeout)])
        cmd.append("--expect-response")

        # Execute command
        executor = CommandExecutor(timeout=timeout + 5)  # Add buffer to executor timeout
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "target": target,
                "message": message,
                "priority": "urgent",
                "timeout": timeout,
                "delivery_status": data if isinstance(data, dict) else {"delivered": True},
                "response_received": data.get("response_received", False) if isinstance(data, dict) else False,
                "agent_response": data.get("response", None) if isinstance(data, dict) else None,
            }

            return format_success_response(response_data, result["command"], f"Urgent message sent to {target}")
        else:
            return format_error_response(
                result.get("stderr", f"Failed to send urgent message to {target}"),
                result["command"],
                [
                    f"Check that target '{target}' exists and is responsive",
                    "Verify agent is not in error or compaction state",
                    "Consider increasing timeout for busy agents",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"send urgent message to {target}")
    except ExecutionError as e:
        return format_error_response(str(e), f"send urgent message to {target}")
    except Exception as e:
        logger.error(f"Unexpected error in send_urgent_message: {e}")
        return format_error_response(f"Unexpected error: {e}", f"send urgent message to {target}")


async def team_notification(
    team_name: str, notification_type: str, content: str, include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Send formatted notification to team.

    Specialized function for system notifications with structured formatting.

    Args:
        team_name: Target team name
        notification_type: Type of notification ("info", "warning", "error", "success")
        content: Notification content
        include_metadata: Include timestamp and sender metadata

    Returns:
        Structured response with notification delivery status
    """
    try:
        # Validate team name
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", team_name):
            return format_error_response(
                f"Invalid team name '{team_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"team notification {team_name}",
            )

        # Validate notification type
        valid_types = {"info", "warning", "error", "success"}
        if notification_type not in valid_types:
            return format_error_response(
                f"Invalid notification type '{notification_type}'. Valid types: {', '.join(valid_types)}",
                f"team notification {team_name}",
                [f"Use one of: {', '.join(valid_types)}"],
            )

        # Validate content
        if not content or not content.strip():
            return format_error_response("Notification content cannot be empty", f"team notification {team_name}")

        # Format notification message
        type_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}

        formatted_message = f"{type_emoji.get(notification_type, '📢')} {notification_type.upper()}: {content}"

        if include_metadata:
            import datetime

            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            formatted_message += f" [{timestamp}]"

        # Use team broadcast with appropriate priority
        priority_map = {"info": "normal", "warning": "high", "error": "urgent", "success": "normal"}

        priority = priority_map.get(notification_type, "normal")

        # Call team broadcast
        broadcast_result = await team_broadcast(team_name=team_name, message=formatted_message, priority=priority)

        # Enhance response with notification metadata
        if broadcast_result.get("success"):
            data = broadcast_result.get("data", {})
            data.update(
                {
                    "notification_type": notification_type,
                    "original_content": content,
                    "formatted_message": formatted_message,
                    "include_metadata": include_metadata,
                }
            )

        return broadcast_result

    except Exception as e:
        logger.error(f"Unexpected error in team_notification: {e}")
        return format_error_response(f"Unexpected error: {e}", f"team notification {team_name}")
