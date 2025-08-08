"""Inter-agent messaging routes for MCP server."""

from typing import Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tmux_orchestrator.server.tools.send_message import (
    SendMessageRequest as ToolSendMessageRequest,
)
from tmux_orchestrator.server.tools.send_message import send_message
from tmux_orchestrator.utils.tmux import TMUXManager

router = APIRouter()
tmux = TMUXManager()


class MessageRequest(BaseModel):
    """API request model for sending messages."""
    target: str  # session:window or session:window.pane
    message: str
    urgent: bool = False


class MessageResponse(BaseModel):
    """API response model for message sending."""
    success: bool
    target: str
    message_sent: str
    timestamp: Optional[str] = None


class BroadcastRequest(BaseModel):
    """API request model for broadcasting to multiple agents."""
    sessions: List[str]  # List of session names
    message: str
    exclude_windows: List[str] = []  # Windows to exclude


@router.post("/send", response_model=MessageResponse)
async def tmux_send_message(request: MessageRequest) -> MessageResponse:
    """Send a message to a Claude agent.

    Primary MCP tool for inter-agent communication.
    """
    # Convert API request to business logic request
    tool_request = ToolSendMessageRequest(
        target=request.target,
        message=request.message,
        urgent=request.urgent
    )

    # Execute business logic
    result = send_message(tmux, tool_request)

    if not result.success:
        # Determine appropriate HTTP status code
        status_code = 404 if "not found" in result.error_message.lower() else 500
        raise HTTPException(status_code=status_code, detail=result.error_message)

    return MessageResponse(
        success=result.success,
        target=result.target,
        message_sent=result.message_sent
    )


@router.post("/broadcast")
async def broadcast_message(request: BroadcastRequest) -> Dict[str, Union[List[Dict[str, Union[str, bool]]], List[str], int]]:
    """Broadcast a message to multiple agents.

    MCP tool for coordinated communication.
    """
    try:
        results = []
        errors = []

        for session_name in request.sessions:
            if not tmux.has_session(session_name):
                errors.append(f"Session '{session_name}' not found")
                continue

            # Get all windows in the session
            windows = tmux.list_windows(session_name)

            for window in windows:
                window_name = window['name']

                # Skip excluded windows
                if window_name in request.exclude_windows:
                    continue

                # Only send to Claude agent windows
                if any(keyword in window_name.lower() for keyword in ['claude', 'pm', 'developer', 'qa']):
                    target = f"{session_name}:{window['index']}"
                    success = tmux.send_message(target, request.message)

                    results.append({
                        "target": target,
                        "window_name": window_name,
                        "success": success
                    })

        return {
            "broadcast_results": results,
            "errors": errors,
            "total_sent": len([r for r in results if r['success']]),
            "total_failed": len([r for r in results if not r['success']]) + len(errors)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session}/{window}")
async def get_message_history(session: str, window: str, lines: int = 100) -> Dict[str, Union[str, List[str], int]]:
    """Get recent message history for an agent.

    MCP tool for conversation monitoring.
    """
    try:
        target = f"{session}:{window}"

        if not tmux.has_session(session):
            raise HTTPException(status_code=404, detail="Session not found")

        # Capture pane content
        output = tmux.capture_pane(target, lines=lines)

        return {
            "session": session,
            "window": window,
            "history": output.split('\n') if output else [],
            "lines_captured": len(output.split('\n')) if output else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interrupt/{session}/{window}")
async def interrupt_agent(session: str, window: str) -> Dict[str, Union[str, bool]]:
    """Send interrupt signal to an agent.

    MCP tool for stopping runaway agents.
    """
    try:
        target = f"{session}:{window}"

        if not tmux.has_session(session):
            raise HTTPException(status_code=404, detail="Session not found")

        # Send Ctrl+C to interrupt
        success = tmux.send_keys(target, "C-c")

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send interrupt signal")

        return {
            "success": True,
            "target": target,
            "action": "interrupt_sent"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
