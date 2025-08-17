"""Business logic for sending messages to Claude agents."""

from dataclasses import dataclass
from typing import Optional

from tmux_orchestrator.core.communication.send_message import send_message as core_send_message
from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class SendMessageRequest:
    """Request parameters for sending a message."""

    target: str
    message: str
    urgent: bool = False


@dataclass
class SendMessageResult:
    """Result of sending a message operation."""

    success: bool
    target: str
    message_sent: str
    error_message: Optional[str] = None


def send_message(tmux: TMUXManager, request: SendMessageRequest) -> SendMessageResult:
    """
    Send a message to a Claude agent via tmux.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: SendMessageRequest with target and message

    Returns:
        SendMessageResult indicating success/failure

    Raises:
        ValueError: If target format is invalid or message is empty
    """
    try:
        # Delegate to core business logic
        success, result_message = core_send_message(
            tmux=tmux, target=request.target, message=request.message, timeout=30.0 if request.urgent else None
        )

        return SendMessageResult(
            success=success,
            target=request.target,
            message_sent=request.message,
            error_message=result_message if not success else None,
        )

    except Exception as e:
        return SendMessageResult(
            success=False,
            target=request.target,
            message_sent=request.message,
            error_message=f"Unexpected error sending message: {str(e)}",
        )
