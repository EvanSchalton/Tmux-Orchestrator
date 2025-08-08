"""Pydantic models for agent management operations."""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class AgentSpawnRequest(BaseModel):
    """Request model for spawning a new Claude agent."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "session_name": "my-project",
            "agent_type": "developer",
            "project_path": "/Users/dev/my-project",
            "briefing_message": "You are a senior Python developer..."
        }
    })
    
    session_name: str = Field(
        ..., 
        description="Target tmux session name",
        min_length=1,
        examples=["my-project", "frontend-team"]
    )
    agent_type: str = Field(
        ..., 
        description="Agent specialization type",
        pattern="^(developer|pm|qa|devops|reviewer|researcher|docs)$",
        examples=["developer", "pm", "qa"]
    )
    project_path: Optional[str] = Field(
        None, 
        description="Working directory for the agent",
        examples=["/Users/dev/my-project", "/workspace/app"]
    )
    briefing_message: Optional[str] = Field(
        None, 
        description="Initial briefing message for the agent",
        examples=["You are a senior developer working on React components"]
    )


class AgentSpawnResponse(BaseModel):
    """Response model for agent spawn operations."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "session": "my-project",
            "window": "Claude-developer",
            "target": "my-project:Claude-developer",
            "agent_type": "developer",
            "created_at": "2025-01-08T15:30:00Z"
        }
    })
    
    success: bool = Field(..., description="Operation success status")
    session: str = Field(..., description="Session where agent was created")
    window: str = Field(..., description="Window name for the agent")
    target: str = Field(..., description="Full tmux target (session:window)")
    agent_type: str = Field(..., description="Type of agent spawned")
    created_at: str = Field(..., description="ISO timestamp of creation")
    error_message: Optional[str] = Field(None, description="Error details if failed")


class AgentStatusRequest(BaseModel):
    """Request model for agent status checks."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "target": "my-project:Claude-developer",
            "include_activity": True,
            "activity_lines": 50
        }
    })
    
    target: str = Field(
        ..., 
        description="Agent target (session:window)",
        pattern=r"^[^:]+:[^:]+$",
        examples=["my-project:Claude-developer", "frontend:Claude-pm"]
    )
    include_activity: bool = Field(
        True, 
        description="Include recent activity in response"
    )
    activity_lines: int = Field(
        50, 
        description="Number of activity lines to capture",
        ge=1,
        le=200
    )


class AgentStatusResponse(BaseModel):
    """Response model for agent status operations."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "target": "my-project:Claude-developer",
            "status": "active",
            "responsive": True,
            "last_activity": "2025-01-08T15:35:00Z",
            "uptime_minutes": 45,
            "activity_summary": ["Working on authentication module", "Running tests"],
            "health_score": 95
        }
    })
    
    target: str = Field(..., description="Agent target identifier")
    status: str = Field(..., description="Current agent status")
    responsive: bool = Field(..., description="Agent responsiveness")
    last_activity: str = Field(..., description="ISO timestamp of last activity")
    uptime_minutes: int = Field(..., description="Minutes since agent started")
    activity_summary: List[str] = Field(..., description="Recent activity lines")
    health_score: int = Field(..., description="Health score (0-100)")
    error_details: Optional[str] = Field(None, description="Error information")


class AgentRestartRequest(BaseModel):
    """Request model for restarting agents."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "target": "my-project:Claude-developer",
            "preserve_context": True,
            "briefing_message": "Continue working on the authentication system"
        }
    })
    
    target: str = Field(
        ..., 
        description="Agent target to restart",
        pattern=r"^[^:]+:[^:]+$"
    )
    preserve_context: bool = Field(
        True, 
        description="Attempt to preserve work context"
    )
    briefing_message: Optional[str] = Field(
        None, 
        description="Custom briefing for restarted agent"
    )


class AgentRestartResponse(BaseModel):
    """Response model for agent restart operations."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "target": "my-project:Claude-developer",
            "old_pid": 12345,
            "new_pid": 12678,
            "restart_time": "2025-01-08T15:40:00Z",
            "context_preserved": True
        }
    })
    
    success: bool = Field(..., description="Restart operation success")
    target: str = Field(..., description="Agent target that was restarted")
    old_pid: Optional[int] = Field(None, description="Previous process ID")
    new_pid: Optional[int] = Field(None, description="New process ID")
    restart_time: str = Field(..., description="ISO timestamp of restart")
    context_preserved: bool = Field(..., description="Whether context was preserved")
    error_message: Optional[str] = Field(None, description="Error details if failed")


class AgentKillRequest(BaseModel):
    """Request model for terminating agents."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "target": "my-project:Claude-developer",
            "force": False,
            "save_state": True
        }
    })
    
    target: str = Field(
        ..., 
        description="Agent target to terminate",
        pattern=r"^[^:]+:[^:]+$"
    )
    force: bool = Field(
        False, 
        description="Force termination without graceful shutdown"
    )
    save_state: bool = Field(
        True, 
        description="Save agent state before termination"
    )


class AgentKillResponse(BaseModel):
    """Response model for agent termination operations."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "target": "my-project:Claude-developer",
            "termination_method": "graceful",
            "final_state_saved": True,
            "terminated_at": "2025-01-08T15:45:00Z"
        }
    })
    
    success: bool = Field(..., description="Termination operation success")
    target: str = Field(..., description="Agent target that was terminated")
    termination_method: str = Field(..., description="Method used (graceful/force)")
    final_state_saved: bool = Field(..., description="Whether final state was saved")
    terminated_at: str = Field(..., description="ISO timestamp of termination")
    error_message: Optional[str] = Field(None, description="Error details if failed")


class AgentListResponse(BaseModel):
    """Response model for listing all agents."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "agents": [
                {
                    "session": "my-project",
                    "window": "Claude-developer",
                    "target": "my-project:Claude-developer",
                    "type": "developer",
                    "status": "active",
                    "created_at": "2025-01-08T15:30:00Z"
                }
            ],
            "total_count": 1,
            "active_count": 1,
            "idle_count": 0,
            "error_count": 0
        }
    })
    
    agents: List[Dict[str, Union[str, int]]] = Field(
        ..., 
        description="List of all agents with their details"
    )
    total_count: int = Field(..., description="Total number of agents")
    active_count: int = Field(..., description="Number of active agents")
    idle_count: int = Field(..., description="Number of idle agents")
    error_count: int = Field(..., description="Number of agents with errors")
    query_timestamp: str = Field(..., description="When the query was executed")