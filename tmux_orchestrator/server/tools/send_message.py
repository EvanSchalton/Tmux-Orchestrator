"""Business logic for sending messages to Claude agents."""

from dataclasses import dataclass
from typing import Optional

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
    # Validate target format
    if ':' not in request.target:
        return SendMessageResult(
            success=False,
            target=request.target,
            message_sent=request.message,
            error_message="Target must be in format 'session:window' or 'session:window.pane'"
        )

    # Validate message content
    if not request.message.strip():
        return SendMessageResult(
            success=False,
            target=request.target,
            message_sent=request.message,
            error_message="Message cannot be empty"
        )

    # Extract session name and validate it exists
    session_name = request.target.split(':')[0]
    if not tmux.has_session(session_name):
        return SendMessageResult(
            success=False,
            target=request.target,
            message_sent=request.message,
            error_message=f"Session '{session_name}' not found"
        )

    try:
        # Use TMUXManager's optimized send_message method
        success = tmux.send_message(request.target, request.message)

        if not success:
            return SendMessageResult(
                success=False,
                target=request.target,
                message_sent=request.message,
                error_message="Failed to send message via tmux"
            )

        return SendMessageResult(
            success=True,
            target=request.target,
            message_sent=request.message
        )

    except Exception as e:
        return SendMessageResult(
            success=False,
            target=request.target,
            message_sent=request.message,
            error_message=f"Unexpected error sending message: {str(e)}"
        )
