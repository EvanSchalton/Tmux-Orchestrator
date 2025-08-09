"""Inter-agent communication routes for MCP server."""

from typing import Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from tmux_orchestrator.server.tools.broadcast_message import (
    BroadcastMessageRequest as ToolBroadcastMessageRequest,
)
from tmux_orchestrator.server.tools.broadcast_message import (
    broadcast_message,
)
from tmux_orchestrator.server.tools.get_messages import (
    GetMessagesRequest as ToolGetMessagesRequest,
)
from tmux_orchestrator.server.tools.get_messages import (
    get_messages,
)
from tmux_orchestrator.server.tools.send_message import (
    SendMessageRequest as ToolSendMessageRequest,
)
from tmux_orchestrator.server.tools.send_message import (
    send_message,
)
from tmux_orchestrator.utils.tmux import TMUXManager

router = APIRouter()
tmux = TMUXManager()


class MessageRequest(BaseModel):
    """MCP tool request for sending messages."""

    target: str  # session:window or session:window.pane
    message: str
    urgent: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target": "my-project:Claude-developer",
                "message": "Please implement the login functionality",
                "urgent": False,
            }
        }
    )


class MessageResponse(BaseModel):
    """MCP tool response for message sending."""

    success: bool
    target: str
    message_sent: str
    timestamp: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "target": "my-project:Claude-developer",
                "message_sent": "Please implement the login functionality",
                "timestamp": "2025-01-08T10:30:00Z",
            }
        }
    )


class BroadcastRequest(BaseModel):
    """MCP tool request for broadcasting to multiple agents."""

    session: str  # Session name to broadcast to
    message: str
    agent_types: Optional[list[str]] = None  # Filter by agent types
    exclude_targets: Optional[list[str]] = None  # Targets to exclude
    urgent: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session": "tmux-orc-dev",
                "message": "Please prepare status updates for the standup meeting",
                "agent_types": ["developer", "pm"],
                "exclude_targets": ["tmux-orc-dev:0"],
                "urgent": False,
            }
        }
    )


class BroadcastResponse(BaseModel):
    """MCP tool response for broadcast operations."""

    success: bool
    total_sent: int
    total_failed: int
    results: list[dict[str, Union[str, bool]]]
    errors: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "total_sent": 3,
                "total_failed": 0,
                "results": [
                    {"target": "frontend:Claude-developer", "success": True},
                    {"target": "backend:Claude-developer", "success": True},
                ],
                "errors": [],
            }
        }
    )


class InterruptRequest(BaseModel):
    """MCP tool request for interrupting agents."""

    session: str
    window: str
    force: bool = False  # Whether to send multiple interrupt signals

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session": "my-project",
                "window": "Claude-developer",
                "force": False,
            }
        }
    )


class ConversationHistoryRequest(BaseModel):
    """MCP tool request for retrieving conversation history."""

    session: str
    window: str
    lines: int = 100
    include_timestamps: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session": "my-project",
                "window": "Claude-developer",
                "lines": 100,
                "include_timestamps": False,
            }
        }
    )


@router.post("/send", response_model=MessageResponse)
async def send_message_tool(request: MessageRequest) -> MessageResponse:
    """MCP Tool: Send a message to a Claude agent.

    This is the primary communication tool for sending messages between
    agents or from external systems to agents in the orchestration system.
    """
    # Convert API request to business logic request
    tool_request = ToolSendMessageRequest(target=request.target, message=request.message, urgent=request.urgent)

    # Execute business logic
    result = send_message(tmux, tool_request)

    if not result.success:
        # Determine appropriate HTTP status code
        error_msg = result.error_message or "Unknown error"
        status_code = 404 if "not found" in error_msg.lower() else 500
        raise HTTPException(status_code=status_code, detail=result.error_message)

    return MessageResponse(success=result.success, target=result.target, message_sent=result.message_sent)


@router.post("/broadcast", response_model=BroadcastResponse)
async def broadcast_message_tool(request: BroadcastRequest) -> BroadcastResponse:
    """MCP Tool: Broadcast a message to multiple agents.

    This tool enables coordinated communication by sending the same message
    to multiple agents within a session.
    """
    # Convert API request to business logic request
    tool_request = ToolBroadcastMessageRequest(
        session=request.session,
        message=request.message,
        agent_types=request.agent_types,
        exclude_targets=request.exclude_targets,
        urgent=request.urgent,
    )

    # Execute business logic
    result = broadcast_message(tmux, tool_request)

    if not result.success and result.error_message:
        # Determine appropriate HTTP status code
        error_msg = result.error_message
        status_code = 404 if "not found" in error_msg.lower() else 500
        raise HTTPException(status_code=status_code, detail=result.error_message)

    # Convert results to API response format
    results = [{"target": target, "success": True} for target in result.targets_sent]
    results.extend([{"target": target, "success": False} for target in result.targets_failed])

    return BroadcastResponse(
        success=result.success,
        total_sent=len(result.targets_sent),
        total_failed=len(result.targets_failed),
        results=results,
        errors=[result.error_message] if result.error_message else [],
    )


@router.get("/history")
async def get_conversation_history_tool(
    request: ConversationHistoryRequest,
) -> dict[str, Union[str, list[dict[str, str]], int]]:
    """MCP Tool: Get conversation history for an agent.

    This tool retrieves the recent conversation history from an agent's
    tmux session for monitoring and debugging purposes.
    """
    # Convert to target format
    target = f"{request.session}:{request.window}"

    # Use the get_messages tool
    tool_request = ToolGetMessagesRequest(
        target=target,
        lines=request.lines,
        include_timestamps=request.include_timestamps,
    )

    result = get_messages(tmux, tool_request)

    if not result.success and result.error_message:
        error_msg = result.error_message
        status_code = 404 if "not found" in error_msg.lower() else 500
        raise HTTPException(status_code=status_code, detail=result.error_message)

    # Convert messages to dict format for API response
    messages = [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
        }
        for msg in result.messages
    ]

    return {
        "session": request.session,
        "window": request.window,
        "target": target,
        "messages": messages,
        "lines_captured": result.total_lines_captured,
        "total_lines_requested": request.lines,
    }


@router.post("/interrupt")
async def interrupt_agent_tool(
    request: InterruptRequest,
) -> dict[str, Union[str, bool]]:
    """MCP Tool: Send interrupt signal to an agent.

    This tool sends a Ctrl+C signal to interrupt a running agent,
    useful for stopping long-running operations or unresponsive agents.
    """
    try:
        target = f"{request.session}:{request.window}"

        if not tmux.has_session(request.session):
            raise HTTPException(status_code=404, detail="Session not found")

        # Send Ctrl+C to interrupt
        success = tmux.send_keys(target, "C-c")

        # Send additional interrupt if force is enabled
        if request.force and success:
            import asyncio

            await asyncio.sleep(0.5)
            tmux.send_keys(target, "C-c")

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send interrupt signal")

        return {
            "success": True,
            "target": target,
            "action": "interrupt_sent",
            "force_used": request.force,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{session}")
async def get_session_agents(
    session: str,
) -> dict[str, Union[str, list[dict[str, str]], int]]:
    """MCP Tool: Get all agents in a specific session.

    This tool lists all Claude agents running within a specific tmux session
    for targeted communication and management.
    """
    try:
        if not tmux.has_session(session):
            raise HTTPException(status_code=404, detail="Session not found")

        # Get all agents and filter by session
        all_agents = tmux.list_agents()
        session_agents = [agent for agent in all_agents if agent["session"] == session]

        return {
            "session": session,
            "agents": session_agents,
            "count": len(session_agents),
            "active": len([a for a in session_agents if a["status"] == "Active"]),
            "idle": len([a for a in session_agents if a["status"] == "Idle"]),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
