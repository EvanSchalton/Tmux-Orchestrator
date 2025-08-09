"""Pydantic models for team coordination and deployment operations."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TeamMember(BaseModel):
    """Model for team member definition."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "developer",
                "briefing": "Senior React developer specializing in component architecture",
                "skills": ["React", "TypeScript", "CSS-in-JS", "Testing"],
            }
        }
    )

    role: str = Field(
        ...,
        description="Agent role/specialization",
        pattern="^(pm|developer|qa|devops|reviewer|researcher|docs)$",
        examples=["developer", "pm", "qa"],
    )
    briefing: Optional[str] = Field(None, description="Custom briefing for this team member", max_length=1000)
    skills: list[str] = Field(
        default_factory=list,
        description="Required skills/technologies",
        examples=[["React", "TypeScript"], ["Python", "FastAPI", "PostgreSQL"]],
    )


class TeamDeploymentRequest(BaseModel):
    """Request model for deploying agent teams."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_name": "ecommerce-app",
                "project_path": "/Users/dev/ecommerce-app",
                "team_members": [
                    {
                        "role": "pm",
                        "briefing": "Lead the frontend development team",
                        "skills": ["Project Management", "Agile"],
                    },
                    {
                        "role": "developer",
                        "briefing": "Focus on React components and state management",
                        "skills": ["React", "Redux", "TypeScript"],
                    },
                ],
                "coordination_strategy": "hub_and_spoke",
            }
        }
    )

    project_name: str = Field(
        ...,
        description="Name of the project/team",
        min_length=1,
        max_length=100,
        pattern="^[a-zA-Z0-9_-]+$",
    )
    project_path: str = Field(
        ...,
        description="Working directory for the project",
        examples=["/Users/dev/my-project", "/workspace/app"],
    )
    team_members: list[TeamMember] = Field(
        ..., description="List of team members to deploy", min_length=1, max_length=20
    )
    coordination_strategy: str = Field(
        "hub_and_spoke",
        description="Team coordination pattern",
        pattern="^(hub_and_spoke|peer_to_peer|hierarchical)$",
    )


class TeamDeploymentResponse(BaseModel):
    """Response model for team deployment operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "deployment_id": "dep_1704723000_001",
                "session_name": "ecommerce-app",
                "deployed_agents": [
                    {
                        "role": "pm",
                        "session": "ecommerce-app",
                        "window": "Claude-pm",
                        "target": "ecommerce-app:Claude-pm",
                        "status": "active",
                    }
                ],
                "coordination_setup": {
                    "strategy": "hub_and_spoke",
                    "hub": "ecommerce-app:Claude-pm",
                    "spokes": ["ecommerce-app:Claude-developer"],
                },
                "deployed_at": "2025-01-08T15:30:00Z",
            }
        }
    )

    success: bool = Field(..., description="Deployment success status")
    deployment_id: str = Field(..., description="Unique deployment identifier")
    session_name: str = Field(..., description="Session where team was deployed")
    deployed_agents: list[dict[str, str]] = Field(..., description="List of successfully deployed agents")
    coordination_setup: dict[str, Any] = Field(..., description="Coordination pattern configuration")
    deployed_at: str = Field(..., description="ISO timestamp of deployment")
    error_message: Optional[str] = Field(None, description="Error details if failed")


class StandupRequest(BaseModel):
    """Request model for team standup coordination."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_names": ["frontend-team", "backend-team"],
                "include_idle_agents": True,
                "timeout_seconds": 30,
                "standup_type": "daily",
            }
        }
    )

    session_names: list[str] = Field(..., description="List of team sessions to include in standup", min_length=1)
    include_idle_agents: bool = Field(True, description="Include idle agents in standup")
    timeout_seconds: int = Field(30, description="Timeout for agent responses", ge=10, le=300)
    standup_type: str = Field(
        "daily",
        description="Type of standup meeting",
        pattern="^(daily|weekly|urgent|retrospective)$",
    )


class StandupResponse(BaseModel):
    """Response model for standup coordination operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "standup_id": "standup_1704723000_001",
                "standup_initiated": True,
                "results": [
                    {
                        "session": "frontend-team",
                        "status": "completed",
                        "agents_contacted": 3,
                        "responses_received": 3,
                    }
                ],
                "total_agents_contacted": 5,
                "initiated_at": "2025-01-08T15:30:00Z",
            }
        }
    )

    success: bool = Field(..., description="Overall standup success")
    standup_id: str = Field(..., description="Unique standup identifier")
    standup_initiated: bool = Field(..., description="Whether standup was started")
    results: list[dict[str, Any]] = Field(..., description="Results per session")
    total_agents_contacted: int = Field(..., description="Total number of agents contacted")
    initiated_at: str = Field(..., description="ISO timestamp when standup started")


class TeamRecoveryRequest(BaseModel):
    """Request model for team recovery operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_name": "frontend-team",
                "recovery_strategy": "restart_failed",
                "preserve_context": True,
                "max_parallel_recoveries": 3,
            }
        }
    )

    session_name: str = Field(..., description="Team session to recover", min_length=1)
    recovery_strategy: str = Field(
        "restart_failed",
        description="Recovery strategy to use",
        pattern="^(restart_failed|restart_all|selective_recovery)$",
    )
    preserve_context: bool = Field(True, description="Attempt to preserve agent work context")
    max_parallel_recoveries: int = Field(3, description="Maximum agents to recover simultaneously", ge=1, le=10)


class TeamRecoveryResponse(BaseModel):
    """Response model for team recovery operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "recovery_id": "rec_1704723000_001",
                "session_name": "frontend-team",
                "recovery_summary": {
                    "total_agents": 4,
                    "failed_agents": 2,
                    "recovered_agents": 2,
                    "recovery_failures": 0,
                },
                "recovered_agents": ["Claude-developer", "Claude-qa"],
                "recovery_failures": [],
                "completed_at": "2025-01-08T15:35:00Z",
            }
        }
    )

    success: bool = Field(..., description="Overall recovery success")
    recovery_id: str = Field(..., description="Unique recovery operation identifier")
    session_name: str = Field(..., description="Session that was recovered")
    recovery_summary: dict[str, int] = Field(..., description="Summary statistics of recovery operation")
    recovered_agents: list[str] = Field(..., description="List of successfully recovered agents")
    recovery_failures: list[str] = Field(..., description="List of agents that failed to recover")
    completed_at: str = Field(..., description="ISO timestamp of completion")


class TeamStatusRequest(BaseModel):
    """Request model for team status operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_name": "frontend-team",
                "include_activity": True,
                "include_metrics": True,
                "activity_window_minutes": 60,
            }
        }
    )

    session_name: str = Field(..., description="Team session to check status for", min_length=1)
    include_activity: bool = Field(True, description="Include recent activity information")
    include_metrics: bool = Field(True, description="Include performance metrics")
    activity_window_minutes: int = Field(60, description="Minutes of activity history to include", ge=5, le=1440)


class TeamStatusResponse(BaseModel):
    """Response model for team status operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "session_name": "frontend-team",
                "session_info": {
                    "name": "frontend-team",
                    "created": "2025-01-08T14:00:00Z",
                    "attached": "1",
                    "windows": 4,
                },
                "agents": [
                    {
                        "window": "Claude-pm",
                        "type": "pm",
                        "status": "active",
                        "last_activity": "2025-01-08T15:30:00Z",
                        "health_score": 95,
                    }
                ],
                "team_metrics": {
                    "total_agents": 4,
                    "active_agents": 3,
                    "idle_agents": 1,
                    "avg_health_score": 92,
                    "productivity_index": 85,
                },
                "coordination_status": {
                    "pattern": "hub_and_spoke",
                    "hub_responsive": True,
                    "communication_health": "good",
                },
            }
        }
    )

    success: bool = Field(..., description="Status query success")
    session_name: str = Field(..., description="Team session name")
    session_info: dict[str, Any] = Field(..., description="Basic session information")
    agents: list[dict[str, Any]] = Field(..., description="Individual agent status information")
    team_metrics: dict[str, Any] = Field(..., description="Team-level performance metrics")
    coordination_status: dict[str, Any] = Field(..., description="Team coordination health information")
    queried_at: str = Field(..., description="When status was queried")
