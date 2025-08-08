"""Inter-agent communication routes for MCP server."""

from typing import Optional, Union, List, Dict, Any

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
    """MCP tool request for sending messages."""
    target: str  # session:window or session:window.pane
    message: str
    urgent: bool = False

    class Config:
        """Pydantic config for request validation."""
        json_schema_extra = {
            "example": {
                "target": "my-project:Claude-developer",
                "message": "Please implement the login functionality",
                "urgent": False
            }
        }


class MessageResponse(BaseModel):
    """MCP tool response for message sending."""
    success: bool
    target: str
    message_sent: str
    timestamp: Optional[str] = None

    class Config:
        """Pydantic config for response validation."""
        json_schema_extra = {
            "example": {
                "success": True,
                "target": "my-project:Claude-developer",
                "message_sent": "Please implement the login functionality",
                "timestamp": "2025-01-08T10:30:00Z"
            }
        }


class BroadcastRequest(BaseModel):
    """MCP tool request for broadcasting to multiple agents."""
    sessions: List[str]  # List of session names
    message: str
    exclude_windows: List[str] = []  # Windows to exclude
    agent_types_only: List[str] = []  # Only broadcast to specific agent types

    class Config:
        """Pydantic config for request validation."""
        json_schema_extra = {
            "example": {
                "sessions": ["frontend-project", "backend-project"],
                "message": "Please prepare status updates for the standup meeting",
                "exclude_windows": ["Project-Shell"],
                "agent_types_only": ["developer", "pm"]
            }
        }


class BroadcastResponse(BaseModel):
    """MCP tool response for broadcast operations."""
    success: bool
    total_sent: int
    total_failed: int
    results: list[dict[str, str | bool]]
    errors: list[str]

    class Config:
        """Pydantic config for response validation."""
        json_schema_extra = {
            "example": {
                "success": True,
                "total_sent": 3,
                "total_failed": 0,
                "results": [
                    {"target": "frontend:Claude-developer", "success": True},
                    {"target": "backend:Claude-developer", "success": True}
                ],
                "errors": []
            }
        }


class InterruptRequest(BaseModel):
    """MCP tool request for interrupting agents."""
    session: str
    window: str
    force: bool = False  # Whether to send multiple interrupt signals

    class Config:
        """Pydantic config for request validation."""
        json_schema_extra = {
            "example": {
                "session": "my-project",
                "window": "Claude-developer",
                "force": False
            }
        }


class ConversationHistoryRequest(BaseModel):
    """MCP tool request for retrieving conversation history."""
    session: str
    window: str
    lines: int = 100
    include_timestamps: bool = False

    class Config:
        """Pydantic config for request validation."""
        json_schema_extra = {
            "example": {
                "session": "my-project",
                "window": "Claude-developer",
                "lines": 100,
                "include_timestamps": False
            }
        }


@router.post("/send", response_model=MessageResponse)
async def send_message_tool(request: MessageRequest) -> MessageResponse:
    """MCP Tool: Send a message to a Claude agent.
    
    This is the primary communication tool for sending messages between
    agents or from external systems to agents in the orchestration system.
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


@router.post("/broadcast", response_model=BroadcastResponse)
async def broadcast_message_tool(request: BroadcastRequest) -> BroadcastResponse:
    """MCP Tool: Broadcast a message to multiple agents.
    
    This tool enables coordinated communication by sending the same message
    to multiple agents across different sessions simultaneously.
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
                
                # Filter by agent types if specified
                if request.agent_types_only:
                    agent_type_match = False
                    for agent_type in request.agent_types_only:
                        if agent_type.lower() in window_name.lower():
                            agent_type_match = True
                            break
                    if not agent_type_match:
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
        
        total_sent = len([r for r in results if r['success']])
        total_failed = len([r for r in results if not r['success']]) + len(errors)
        
        return BroadcastResponse(
            success=total_sent > 0,
            total_sent=total_sent,
            total_failed=total_failed,
            results=results,
            errors=errors
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_conversation_history_tool(
    request: ConversationHistoryRequest
) -> dict[str, str | list[str] | int]:
    """MCP Tool: Get conversation history for an agent.
    
    This tool retrieves the recent conversation history from an agent's
    tmux session for monitoring and debugging purposes.
    """
    try:
        target = f"{request.session}:{request.window}"
        
        if not tmux.has_session(request.session):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Capture pane content
        output = tmux.capture_pane(target, lines=request.lines)
        history_lines = output.split('\n') if output else []
        
        return {
            "session": request.session,
            "window": request.window,
            "target": target,
            "history": history_lines,
            "lines_captured": len(history_lines),
            "total_lines_requested": request.lines
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interrupt")
async def interrupt_agent_tool(request: InterruptRequest) -> dict[str, str | bool]:
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
            "force_used": request.force
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{session}")
async def get_session_agents(session: str) -> dict[str, list[dict[str, str]] | int]:
    """MCP Tool: Get all agents in a specific session.
    
    This tool lists all Claude agents running within a specific tmux session
    for targeted communication and management.
    """
    try:
        if not tmux.has_session(session):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get all agents and filter by session
        all_agents = tmux.list_agents()
        session_agents = [
            agent for agent in all_agents 
            if agent['session'] == session
        ]
        
        return {
            "session": session,
            "agents": session_agents,
            "count": len(session_agents),
            "active": len([a for a in session_agents if a['status'] == 'Active']),
            "idle": len([a for a in session_agents if a['status'] == 'Idle'])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))