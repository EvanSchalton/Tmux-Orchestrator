"""Pydantic models for inter-agent communication operations."""

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class MessageRequest(BaseModel):
    """Request model for sending messages to agents."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target": "my-project:Claude-developer",
                "message": "Please focus on the authentication system",
                "urgent": False,
                "sender_id": "orchestrator",
            }
        }
    )

    target: str = Field(
        ...,
        description="Target agent (session:window or session:window.pane)",
        pattern=r"^[^:]+:[^:]+(\.\d+)?$",
        examples=["my-project:Claude-developer", "frontend:Claude-pm.1"],
    )
    message: str = Field(
        ...,
        description="Message content to send",
        min_length=1,
        max_length=2000,
        examples=["Update status on React components", "Start working on API tests"],
    )
    urgent: bool = Field(False, description="Mark message as urgent")
    sender_id: Optional[str] = Field(
        None,
        description="Identifier of the message sender",
        examples=["orchestrator", "pm-agent", "user"],
    )


class MessageResponse(BaseModel):
    """Response model for message sending operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "target": "my-project:Claude-developer",
                "message_id": "msg_1704723000_001",
                "delivered_at": "2025-01-08T15:30:00Z",
                "estimated_read_time": "2025-01-08T15:30:05Z",
            }
        }
    )

    success: bool = Field(..., description="Message delivery success")
    target: str = Field(..., description="Target where message was sent")
    message_id: str = Field(..., description="Unique message identifier")
    delivered_at: str = Field(..., description="ISO timestamp of delivery")
    estimated_read_time: str = Field(..., description="Estimated when agent will read")
    error_message: Optional[str] = Field(None, description="Error details if failed")


class BroadcastRequest(BaseModel):
    """Request model for broadcasting messages to multiple agents."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sessions": ["frontend-team", "backend-team"],
                "message": "Sprint planning meeting in 30 minutes",
                "exclude_windows": ["Claude-pm"],
                "agent_types_only": ["developer", "qa"],
                "urgent": True,
            }
        }
    )

    sessions: list[str] = Field(
        ...,
        description="List of session names to broadcast to",
        min_length=1,
        examples=[["frontend-team"], ["project-a", "project-b"]],
    )
    message: str = Field(..., description="Message to broadcast", min_length=1, max_length=2000)
    exclude_windows: list[str] = Field(default_factory=list, description="Window names to exclude from broadcast")
    agent_types_only: list[str] = Field(
        default_factory=list,
        description="Only send to specific agent types",
        examples=[["developer", "qa"], ["pm"]],
    )
    urgent: bool = Field(False, description="Mark broadcast as urgent")
    sender_id: Optional[str] = Field(None, description="Broadcast sender identifier")


class BroadcastResponse(BaseModel):
    """Response model for broadcast operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "broadcast_id": "bc_1704723000_001",
                "total_sent": 5,
                "total_failed": 1,
                "results": [
                    {
                        "target": "frontend:Claude-developer",
                        "success": True,
                        "delivered_at": "2025-01-08T15:30:00Z",
                    }
                ],
                "errors": ["Session 'invalid' not found"],
            }
        }
    )

    success: bool = Field(..., description="Overall broadcast success")
    broadcast_id: str = Field(..., description="Unique broadcast identifier")
    total_sent: int = Field(..., description="Number of successful deliveries")
    total_failed: int = Field(..., description="Number of failed deliveries")
    results: list[dict[str, Union[str, bool]]] = Field(..., description="Detailed delivery results per target")
    errors: list[str] = Field(..., description="List of error messages")
    broadcast_at: str = Field(..., description="ISO timestamp of broadcast")


class InterruptRequest(BaseModel):
    """Request model for interrupting agent operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target": "my-project:Claude-developer",
                "interrupt_type": "soft",
                "reason": "Urgent priority change",
                "new_instruction": "Stop current work and focus on bug fix",
            }
        }
    )

    target: str = Field(..., description="Target agent to interrupt", pattern=r"^[^:]+:[^:]+(\.\d+)?$")
    interrupt_type: str = Field("soft", description="Type of interrupt", pattern="^(soft|hard|emergency)$")
    reason: Optional[str] = Field(None, description="Reason for the interrupt", max_length=500)
    new_instruction: Optional[str] = Field(None, description="New instruction after interrupt", max_length=1000)


class InterruptResponse(BaseModel):
    """Response model for interrupt operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "target": "my-project:Claude-developer",
                "interrupt_id": "int_1704723000_001",
                "interrupted_at": "2025-01-08T15:35:00Z",
                "agent_acknowledged": True,
                "previous_state_saved": True,
            }
        }
    )

    success: bool = Field(..., description="Interrupt operation success")
    target: str = Field(..., description="Target that was interrupted")
    interrupt_id: str = Field(..., description="Unique interrupt identifier")
    interrupted_at: str = Field(..., description="ISO timestamp of interrupt")
    agent_acknowledged: bool = Field(..., description="Whether agent acknowledged interrupt")
    previous_state_saved: bool = Field(..., description="Whether previous work state was saved")
    error_message: Optional[str] = Field(None, description="Error details if failed")


class ConversationHistoryRequest(BaseModel):
    """Request model for retrieving conversation history."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target": "my-project:Claude-developer",
                "lines": 100,
                "include_timestamps": True,
                "filter_type": "messages_only",
            }
        }
    )

    target: str = Field(
        ...,
        description="Target agent conversation to retrieve",
        pattern=r"^[^:]+:[^:]+(\.\d+)?$",
    )
    lines: int = Field(50, description="Number of conversation lines to retrieve", ge=1, le=1000)
    include_timestamps: bool = Field(True, description="Include timestamps in history")
    filter_type: str = Field(
        "all",
        description="Filter conversation content",
        pattern="^(all|messages_only|responses_only|errors_only)$",
    )


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target": "my-project:Claude-developer",
                "conversation": [
                    {
                        "timestamp": "2025-01-08T15:30:00Z",
                        "type": "user_message",
                        "content": "Work on authentication system",
                        "message_id": "msg_001",
                    },
                    {
                        "timestamp": "2025-01-08T15:30:05Z",
                        "type": "agent_response",
                        "content": "I'll start working on the authentication system...",
                        "response_to": "msg_001",
                    },
                ],
                "total_entries": 2,
                "history_range": {
                    "oldest": "2025-01-08T15:00:00Z",
                    "newest": "2025-01-08T15:30:05Z",
                },
            }
        }
    )

    target: str = Field(..., description="Target agent for this conversation")
    conversation: list[dict[str, Union[str, Optional[str]]]] = Field(
        ..., description="Chronological conversation entries"
    )
    total_entries: int = Field(..., description="Number of conversation entries")
    history_range: dict[str, str] = Field(..., description="Timestamp range of conversation history")
    retrieved_at: str = Field(..., description="When this history was retrieved")
    error_message: Optional[str] = Field(None, description="Error details if failed")
